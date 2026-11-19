import networkx as nx
import pandas as pd


class GlobalAirNetwork:

    def __init__(self):
        self.graph = nx.DiGraph()

    def load_data(self):
        airports = pd.read_csv("data/global/airports.csv")
        flights = pd.read_csv("data/flights.csv")

        required_airport_columns = {"iata", "lat", "lon"}
        missing_airport_columns = required_airport_columns.difference(airports.columns)
        if missing_airport_columns:
            raise ValueError(
                "Missing airport columns: "
                + ", ".join(sorted(missing_airport_columns))
            )

        for _, row in airports.iterrows():
            self.graph.add_node(
                row["iata"],
                name=row["iata"],
                lat=row["lat"],
                lon=row["lon"]
            )

        required_flight_columns = {"airport", "avg_delay", "cancel_prob"}
        missing_flight_columns = required_flight_columns.difference(flights.columns)
        if missing_flight_columns:
            raise ValueError(
                "Missing flight simulation columns: "
                + ", ".join(sorted(missing_flight_columns))
            )

        for _, row in flights.iterrows():
            if row["airport"] in self.graph:
                nx.set_node_attributes(
                    self.graph,
                    {row["airport"]: {
                        "avg_delay": float(row["avg_delay"]),
                        "cancel_prob": float(row["cancel_prob"]),
                    }},
                )

    def get_graph(self):
        return self.graph

    def load_routes(self, path="data/flights_sample.csv", strict_unknown=True):
        flights = pd.read_csv(path)
        required = {
            "flight_id",
            "origin",
            "destination",
            "departure_time",
            "duration",
            "aircraft_id",
        }
        missing = required.difference(flights.columns)
        if missing:
            raise ValueError(
                "Missing route columns: " + ", ".join(sorted(missing))
            )
        if flights.empty:
            raise ValueError("Route dataset is empty")

        for column in ("departure_time", "duration"):
            numeric = pd.to_numeric(flights[column], errors="coerce")
            if numeric.isna().any():
                raise ValueError(f"{column} contains missing or invalid values")
            if (numeric < 0).any():
                raise ValueError(f"{column} values must be non-negative")
        if (pd.to_numeric(flights["duration"], errors="coerce") <= 0).any():
            raise ValueError("duration values must be greater than zero")

        for column in ("flight_id", "origin", "destination", "aircraft_id"):
            if flights[column].isna().any():
                raise ValueError(f"{column} contains missing values")

        for _, row in flights.iterrows():
            origin = str(row["origin"]).strip()
            destination = str(row["destination"]).strip()

            unknown = [
                code
                for code in (origin, destination)
                if code not in self.graph
            ]
            if unknown:
                message = "Unknown airports: " + ", ".join(sorted(set(unknown)))
                if strict_unknown:
                    raise ValueError(message)
                continue
            if origin == destination:
                raise ValueError(f"Invalid route: origin equals destination ({origin})")

            flight_id = str(row["flight_id"]).strip()
            departure_time = int(row["departure_time"])
            duration = int(row["duration"])
            aircraft_id = str(row["aircraft_id"]).strip()

            if self.graph.has_edge(origin, destination):
                edge = self.graph.edges[origin, destination]
                edge["flight_ids"].append(flight_id)
                edge["departure_times"].append(departure_time)
                edge["durations"].append(duration)
                edge["aircraft_ids"].append(aircraft_id)
            else:
                self.graph.add_edge(
                    origin,
                    destination,
                    flight_ids=[flight_id],
                    departure_times=[departure_time],
                    durations=[duration],
                    aircraft_ids=[aircraft_id],
                    duration=duration,
                )

        return self.graph


def build_network(
    airport_path="data/global/airports.csv",
    route_path="data/flights_sample.csv",
    simulation_path="data/flights.csv",
):
    network = GlobalAirNetwork()
    airports = pd.read_csv(airport_path)
    required = {"iata", "lat", "lon"}
    missing = required.difference(airports.columns)
    if missing:
        raise ValueError(
            "Missing airport columns: " + ", ".join(sorted(missing))
        )
    for _, row in airports.iterrows():
        network.graph.add_node(
            row["iata"],
            name=row["iata"],
            lat=row["lat"],
            lon=row["lon"],
        )

    simulation = pd.read_csv(simulation_path)
    required_simulation = {"airport", "avg_delay", "cancel_prob"}
    missing_simulation = required_simulation.difference(simulation.columns)
    if missing_simulation:
        raise ValueError(
            "Missing flight simulation columns: "
            + ", ".join(sorted(missing_simulation))
        )
    for _, row in simulation.iterrows():
        airport = str(row["airport"]).strip()
        if airport in network.graph:
            network.graph.nodes[airport]["avg_delay"] = float(row["avg_delay"])
            network.graph.nodes[airport]["cancel_prob"] = float(row["cancel_prob"])

    network.load_routes(path=route_path, strict_unknown=False)
    return network.get_graph()
