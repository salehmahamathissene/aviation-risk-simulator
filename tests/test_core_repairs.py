import networkx as nx
import pytest

from app.models.flight import Flight
from app.montecarlo.simulator import GlobalMonteCarlo
from app.network.flight_network import FlightNetwork
from app.network.global_network import GlobalAirNetwork, build_network
from app.propagation.cascade_engine import propagate_delay


def test_cascade_propagation_does_not_loop_on_cycle():
    graph = nx.DiGraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "A")

    result = propagate_delay(graph, "A", 100)

    assert set(result) == {"A", "B"}
    assert result["A"] == 100
    assert result["B"] > 0


def test_cascade_propagation_rejects_unknown_node():
    graph = nx.DiGraph()
    graph.add_node("A")

    with pytest.raises(ValueError, match="Unknown start node"):
        propagate_delay(graph, "Z", 100)


def test_cascade_propagation_rejects_negative_initial_delay():
    graph = nx.DiGraph()
    graph.add_node("A")

    with pytest.raises(ValueError, match="non-negative"):
        propagate_delay(graph, "A", -1)


def test_global_air_network_loads_repository_csv_schemas():
    network = GlobalAirNetwork()
    network.load_data()
    graph = network.get_graph()

    assert graph.is_directed()
    assert graph.number_of_nodes() == 7
    assert graph.nodes["CDG"]["lat"] == pytest.approx(49.0097)
    assert graph.nodes["CDG"]["lon"] == pytest.approx(2.5479)
    assert graph.nodes["CDG"]["avg_delay"] == pytest.approx(45)
    assert graph.nodes["CDG"]["cancel_prob"] == pytest.approx(0.04)


def test_global_network_builder_returns_loaded_graph():
    graph = build_network()

    assert graph.number_of_nodes() == 7
    assert "JFK" in graph


def test_missing_airport_columns_are_reported(tmp_path, monkeypatch):
    bad_airports = tmp_path / "airports.csv"
    bad_flights = tmp_path / "flights.csv"
    bad_airports.write_text("iata,name\nCDG,Paris\n", encoding="utf-8")
    bad_flights.write_text(
        "airport,avg_delay,cancel_prob\nCDG,45,0.04\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "global").mkdir()
    bad_airports.replace(tmp_path / "data" / "global" / "airports.csv")
    bad_flights.replace(tmp_path / "data" / "flights.csv")

    network = GlobalAirNetwork()
    with pytest.raises(ValueError, match="Missing airport columns"):
        network.load_data()


def test_flight_model_import_and_network_creation():
    flight = Flight(
        flight_id="FL1",
        origin="CDG",
        destination="JFK",
        departure_time=100,
    )
    assert flight.origin == "CDG"

    network = FlightNetwork()
    flights = network.generate_network(["CDG", "JFK", "LHR"])
    assert isinstance(flights, list)
    assert all(isinstance(item, Flight) for item in flights)


def test_monte_carlo_empty_dataset_is_rejected(tmp_path):
    csv_path = tmp_path / "flights.csv"
    csv_path.write_text(
        "airport,avg_delay,cancel_prob\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="dataset is empty"):
        GlobalMonteCarlo(runs=10, data_path=str(csv_path))


def test_monte_carlo_malformed_numeric_data_is_rejected(tmp_path):
    csv_path = tmp_path / "flights.csv"
    csv_path.write_text(
        "airport,avg_delay,cancel_prob\n"
        "X,bad,0.1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid numeric"):
        GlobalMonteCarlo(runs=10, data_path=str(csv_path))


def test_monte_carlo_negative_average_is_rejected(tmp_path):
    csv_path = tmp_path / "flights.csv"
    csv_path.write_text(
        "airport,avg_delay,cancel_prob\n"
        "X,-5,0.1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="avg_delay"):
        GlobalMonteCarlo(runs=10, data_path=str(csv_path))


@pytest.mark.parametrize("runs", [0, -1, 1.5, True])
def test_monte_carlo_invalid_run_counts_are_rejected(runs):
    with pytest.raises(ValueError, match="positive integer"):
        GlobalMonteCarlo(runs=runs)


def test_monte_carlo_seed_is_reproducible():
    first = GlobalMonteCarlo(runs=25, seed=123).run()
    second = GlobalMonteCarlo(runs=25, seed=123).run()

    assert first == second
    assert first["runs"] == 25
    assert first["mean_delay"] >= 0
    assert first["p95_delay"] >= 0
    assert first["cancelled_flights"] >= 0
