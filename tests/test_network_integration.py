import csv

import networkx as nx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.network.global_network import build_network
from app.network.network_simulator import run_network_simulation
from app.propagation.cascade_engine import propagate_delay


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_repository_route_dataset_builds_directed_network():
    graph = build_network()

    assert graph.is_directed()
    assert graph.nodes["CDG"]["lat"] == pytest.approx(49.0097)
    assert graph.nodes["CDG"]["cancel_prob"] == pytest.approx(0.04)
    assert graph.has_edge("CDG", "JFK")
    assert graph.has_edge("LHR", "CDG")
    assert graph.has_edge("FRA", "JFK")
    assert not graph.has_edge("JFK", "LAX")
    edge = graph.edges["CDG", "JFK"]
    assert "AF101" in edge["flight_ids"]


def test_duplicate_routes_preserve_all_edge_attributes(tmp_path):
    airports = tmp_path / "airports.csv"
    routes = tmp_path / "routes.csv"
    write_csv(
        airports,
        ["iata", "lat", "lon"],
        [
            {"iata": "A", "lat": 1, "lon": 2},
            {"iata": "B", "lat": 3, "lon": 4},
        ],
    )
    write_csv(
        routes,
        ["flight_id", "origin", "destination", "departure_time", "duration", "aircraft_id"],
        [
            {"flight_id": "F1", "origin": "A", "destination": "B", "departure_time": 0, "duration": 60, "aircraft_id": "A1"},
            {"flight_id": "F2", "origin": "A", "destination": "B", "departure_time": 30, "duration": 90, "aircraft_id": "A1"},
        ],
    )

    network = build_network(str(airports), str(routes))
    edge = network.edges["A", "B"]

    assert edge["flight_ids"] == ["F1", "F2"]
    assert edge["departure_times"] == [0, 30]
    assert edge["durations"] == [60, 90]
    assert edge["aircraft_ids"] == ["A1", "A1"]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("duration", "-1", "duration values must be non-negative"),
        ("duration", "0", "duration values must be greater than zero"),
        ("departure_time", "-1", "departure_time values must be non-negative"),
        ("destination", "", "destination contains missing values"),
    ],
)
def test_invalid_route_values_are_rejected(tmp_path, field, value, message):
    airports = tmp_path / "airports.csv"
    routes = tmp_path / "routes.csv"
    write_csv(
        airports,
        ["iata", "lat", "lon"],
        [
            {"iata": "A", "lat": 1, "lon": 2},
            {"iata": "B", "lat": 3, "lon": 4},
        ],
    )
    row = {
        "flight_id": "F1",
        "origin": "A",
        "destination": "B",
        "departure_time": "0",
        "duration": "60",
        "aircraft_id": "A1",
    }
    row[field] = value
    write_csv(
        routes,
        ["flight_id", "origin", "destination", "departure_time", "duration", "aircraft_id"],
        [row],
    )

    from app.network.global_network import GlobalAirNetwork

    network = GlobalAirNetwork()
    for _, row in __import__("pandas").read_csv(airports).iterrows():
        network.graph.add_node(row["iata"], lat=row["lat"], lon=row["lon"])

    with pytest.raises(ValueError, match=message):
        network.load_routes(str(routes), strict_unknown=True)


def test_unknown_airports_raise_in_strict_loader(tmp_path):
    from app.network.global_network import GlobalAirNetwork

    airports = tmp_path / "airports.csv"
    routes = tmp_path / "routes.csv"
    write_csv(
        airports,
        ["iata", "lat", "lon"],
        [{"iata": "A", "lat": 1, "lon": 2}],
    )
    write_csv(
        routes,
        ["flight_id", "origin", "destination", "departure_time", "duration", "aircraft_id"],
        [{"flight_id": "F1", "origin": "A", "destination": "Z", "departure_time": 0, "duration": 60, "aircraft_id": "A1"}],
    )

    network = GlobalAirNetwork()
    for _, row in __import__("pandas").read_csv(airports).iterrows():
        network.graph.add_node(row["iata"], lat=row["lat"], lon=row["lon"])

    with pytest.raises(ValueError, match="Unknown airports"):
        network.load_routes(str(routes), strict_unknown=True)


def test_empty_route_dataset_is_rejected(tmp_path):
    from app.network.global_network import GlobalAirNetwork

    routes = tmp_path / "routes.csv"
    write_csv(
        routes,
        ["flight_id", "origin", "destination", "departure_time", "duration", "aircraft_id"],
        [],
    )
    network = GlobalAirNetwork()

    with pytest.raises(ValueError, match="Route dataset is empty"):
        network.load_routes(str(routes))


def test_disruption_affects_downstream_airports():
    graph = nx.DiGraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_node("D")

    result = propagate_delay(graph, "A", 100)

    assert result["A"] == 100
    assert result["B"] > 0
    assert result["C"] > 0
    assert result["D"] == 0


def test_cycle_is_bounded():
    graph = nx.DiGraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "A")

    result = propagate_delay(graph, "A", 100)

    assert result["A"] == 100
    assert result["B"] > 0


def test_network_simulation_response_shape_and_reproducibility():
    first = run_network_simulation(
        runs=10,
        start_airport="CDG",
        initial_delay=60,
        seed=123,
    )
    second = run_network_simulation(
        runs=10,
        start_airport="CDG",
        initial_delay=60,
        seed=123,
    )

    assert first == second
    assert set(first) == {
        "mean_network_delay",
        "p95_network_delay",
        "max_delay",
        "affected_airports",
        "runs",
    }
    assert first["runs"] == 10
    assert first["max_delay"] >= 60
    assert "CDG" in first["affected_airports"]
    assert "JFK" in first["affected_airports"]


def test_network_post_endpoint_returns_required_shape():
    client = TestClient(app)
    response = client.post(
        "/simulate/network",
        json={
            "runs": 5,
            "start_airport": "CDG",
            "initial_delay": 60,
            "seed": 123,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "mean_network_delay",
        "p95_network_delay",
        "max_delay",
        "affected_airports",
        "runs",
    }
    assert body["runs"] == 5


def test_network_post_endpoint_rejects_unknown_airport():
    client = TestClient(app)
    response = client.post(
        "/simulate/network",
        json={"runs": 5, "start_airport": "XXX", "initial_delay": 60},
    )

    assert response.status_code == 422
