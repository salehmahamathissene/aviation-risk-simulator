import pandas as pd

from app.models.flight import (
    LEGACY_TURNAROUND_MINUTES,
    Flight,
)


def load_flights(path="data/flights_sample.csv"):

    df = pd.read_csv(path)

    return df.to_dict(orient="records")


def load_schedule(
    path="data/flights_sample.csv",
    known_airports=None,
    known_aircraft_ids=None,
    minimum_turnaround_minutes=None,
    strict=False,
):
    if strict:
        if known_airports is None:
            raise ValueError(
                "strict mode requires a known-airport set"
            )
        if known_aircraft_ids is None:
            raise ValueError(
                "strict mode requires a known-aircraft set"
            )
        if minimum_turnaround_minutes is None:
            raise ValueError(
                "strict mode requires an explicit minimum_turnaround_minutes"
            )
    elif minimum_turnaround_minutes is None:
        minimum_turnaround_minutes = LEGACY_TURNAROUND_MINUTES

    df = pd.read_csv(path)
    required = {
        "flight_id",
        "origin",
        "destination",
        "departure_time",
        "duration",
        "aircraft_id",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(
            "Missing schedule columns: " + ", ".join(sorted(missing))
        )
    if df.empty:
        raise ValueError("Flight schedule is empty")

    flights = []
    flight_ids = set()
    for _, row in df.iterrows():
        flight_id = str(row["flight_id"]).strip()
        origin = str(row["origin"]).strip()
        destination = str(row["destination"]).strip()
        aircraft_id = str(row["aircraft_id"]).strip()

        if flight_id in flight_ids:
            raise ValueError(f"Duplicate flight identifier: {flight_id}")
        flight_ids.add(flight_id)

        if known_airports is not None:
            unknown = [
                airport
                for airport in (origin, destination)
                if airport not in known_airports
            ]
            if unknown:
                raise ValueError(
                    "Unknown airport reference: "
                    + ", ".join(sorted(set(unknown)))
                )

        if known_aircraft_ids is not None:
            if aircraft_id not in known_aircraft_ids:
                raise ValueError(
                    f"Unknown aircraft identifier: {aircraft_id}"
                )
            if aircraft_id == "UNKNOWN":
                raise ValueError(
                    "UNKNOWN is not a valid aircraft identifier"
                )

        flight = Flight(
            flight_id=flight_id,
            origin=origin,
            destination=destination,
            scheduled_departure=float(row["departure_time"]),
            duration=float(row["duration"]),
            aircraft_id=aircraft_id,
            minimum_turnaround_minutes=minimum_turnaround_minutes,
            schedule_mode="strict" if strict else "legacy",
        )
        flights.append(flight)

    return flights
