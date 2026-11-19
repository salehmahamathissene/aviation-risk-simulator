import pytest
import math

from app.data.loader import load_schedule
from app.models.flight import Flight
from app.rotation.aircraft_rotation import AircraftRotation


def make_flight(
    flight_id,
    aircraft_id="A1",
    departure=0,
    duration=60,
    turnaround=45,
    origin="CDG",
    destination="JFK",
):
    return Flight(
        flight_id=flight_id,
        origin=origin,
        destination=destination,
        scheduled_departure=departure,
        duration=duration,
        aircraft_id=aircraft_id,
        minimum_turnaround_minutes=turnaround,
    )


def make_continuous_pair(
    first_id="F1",
    second_id="F2",
    first_departure=0,
    first_duration=100,
    second_departure=120,
    second_duration=60,
    turnaround=45,
    aircraft_id="A1",
):
    return [
        make_flight(
            first_id,
            aircraft_id=aircraft_id,
            departure=first_departure,
            duration=first_duration,
            turnaround=turnaround,
            origin="CDG",
            destination="JFK",
        ),
        make_flight(
            second_id,
            aircraft_id=aircraft_id,
            departure=second_departure,
            duration=second_duration,
            turnaround=turnaround,
            origin="JFK",
            destination="LHR",
        ),
    ]


def test_normal_rotation_has_no_propagated_delay():
    flights = make_continuous_pair(
        first_duration=60,
        second_departure=120,
        turnaround=30,
    )
    results = AircraftRotation(flights).propagate_delay()

    assert [row["flight"].flight_id for row in results] == ["F1", "F2"]
    assert results[0]["propagated_delay"] == 0
    assert results[1]["propagated_delay"] == 0
    assert results[1]["flight"].actual_departure == 120


def test_insufficient_turnaround_propagates_delay():
    flights = make_continuous_pair(
        first_duration=100,
        second_departure=120,
        turnaround=45,
    )
    results = AircraftRotation(flights).propagate_delay(
        {"F1": 20}
    )

    second = results[1]
    assert second["propagated_delay"] == 45
    assert second["flight"].actual_departure == 165
    assert "F1" in second["delay_sources"]


def test_delay_source_is_not_double_counted():
    flights = make_continuous_pair(
        first_duration=100,
        second_departure=150,
        turnaround=45,
    )
    results = AircraftRotation(flights).propagate_delay(
        {"F1": 20}
    )

    assert results[0]["direct_delay"] == 20
    assert results[0]["propagated_delay"] == 0
    assert results[1]["direct_delay"] == 0
    assert results[1]["propagated_delay"] == 15
    assert results[1]["flight"].delay_minutes == 15


def test_undelayed_next_leg_retains_previous_source():
    flights = make_continuous_pair(
        first_duration=100,
        second_departure=120,
        turnaround=45,
    )
    flights.append(
        make_flight(
            "F3",
            departure=180,
            duration=60,
            turnaround=45,
            origin="LHR",
            destination="FRA",
        )
    )
    results = AircraftRotation(flights).propagate_delay({"F1": 20})

    assert results[1]["propagated_delay"] == 45
    assert results[2]["propagated_delay"] == 90
    assert "F1" in results[1]["delay_sources"]
    assert "F1" in results[2]["delay_sources"]


def test_overlapping_schedule_is_moved_after_turnaround():
    flights = make_continuous_pair(
        first_duration=120,
        second_departure=90,
        turnaround=30,
    )
    results = AircraftRotation(flights).propagate_delay()

    assert results[1]["flight"].actual_departure == 150
    assert results[1]["propagated_delay"] == 60
    assert "F1" in results[1]["delay_sources"]


def test_multiple_aircraft_are_calculated_independently():
    flights = [
        make_flight("F1", aircraft_id="A1", departure=0, duration=60),
        make_flight("F2", aircraft_id="A1", departure=80, duration=60, origin="JFK", destination="LHR"),
        make_flight("F3", aircraft_id="A2", departure=10, duration=30, origin="CDG", destination="JFK"),
    ]
    results = AircraftRotation(flights).propagate_delay()

    by_aircraft = {
        row["aircraft_id"]: row["flight"].actual_departure
        for row in results
    }
    assert by_aircraft["A1"] == 105
    assert by_aircraft["A2"] == 10


def test_duplicate_flight_ids_are_rejected():
    flights = [
        make_flight("F1"),
        make_flight("F1"),
    ]

    with pytest.raises(ValueError, match="Duplicate flight identifier"):
        AircraftRotation(flights).build()


def test_unknown_aircraft_reference_is_rejected():
    flights = [make_flight("F1", aircraft_id="A99")]

    with pytest.raises(ValueError, match="Unknown aircraft identifier"):
        AircraftRotation(flights, aircraft_ids={"A1"}).build()


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"scheduled_departure": -1}, "scheduled_departure"),
        ({"duration": -1}, "duration"),
        ({"duration": 0}, "duration"),
        ({"minimum_turnaround_minutes": -1}, "minimum_turnaround"),
        ({"origin": "JFK", "destination": "JFK"}, "different"),
    ],
)
def test_invalid_flight_values_are_rejected(changes, message):
    values = {
        "flight_id": "F1",
        "origin": "CDG",
        "destination": "JFK",
        "scheduled_departure": 0,
        "duration": 60,
        "aircraft_id": "A1",
        "minimum_turnaround_minutes": 45,
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        Flight(**values)


def test_invalid_scheduled_arrival_order_is_rejected():
    with pytest.raises(ValueError, match="scheduled_arrival"):
        Flight(
            flight_id="F1",
            origin="CDG",
            destination="JFK",
            scheduled_departure=100,
            scheduled_arrival=90,
            aircraft_id="A1",
        )


def test_repository_schedule_loads_as_canonical_model():
    flights = load_schedule(
        known_airports={
            "CDG",
            "JFK",
            "LHR",
            "FRA",
            "DXB",
            "HND",
            "AMS",
            "LAX",
        },
        known_aircraft_ids={"A1", "A2", "A3"},
    )

    assert len(flights) == 5
    assert all(isinstance(flight, Flight) for flight in flights)
    assert flights[0].scheduled_arrival == 420


def test_repository_loader_rejects_unknown_destination():
    with pytest.raises(ValueError, match="Unknown airport reference"):
        load_schedule(
            known_airports={"CDG", "JFK", "LHR", "FRA"},
            known_aircraft_ids={"A1", "A2", "A3"},
        )


def test_rotation_results_are_deterministic():
    flights = make_continuous_pair(
        first_id="F1",
        second_id="F2",
        first_departure=0,
        first_duration=100,
        second_departure=120,
        second_duration=60,
    )
    flights.reverse()
    first = AircraftRotation(flights).propagate_delay({"F1": 20})
    second = AircraftRotation(flights).propagate_delay({"F1": 20})

    def serialize(results):
        return [
            (
                row["flight"].flight_id,
                row["flight"].actual_departure,
                row["flight"].actual_arrival,
                row["direct_delay"],
                row["propagated_delay"],
                row["delay_sources"],
            )
            for row in results
        ]

    assert serialize(first) == serialize(second)


def test_valid_airport_continuity():
    flights = [
        make_flight("F1", departure=0, duration=60, origin="CDG", destination="JFK"),
        make_flight("F2", departure=120, duration=60, origin="JFK", destination="LHR"),
    ]
    rotation = AircraftRotation(flights)
    assert len(rotation.build()["A1"]) == 2
    assert len(rotation.propagate_delay()) == 2


def test_invalid_airport_continuity_is_rejected():
    flights = [
        make_flight("F1", departure=0, duration=60, origin="CDG", destination="JFK"),
        make_flight("F2", departure=120, duration=60, origin="LHR", destination="FRA"),
    ]
    with pytest.raises(ValueError, match="continuity error"):
        AircraftRotation(flights).build()


def test_disconnected_flight_after_long_gap_is_still_rejected():
    flights = [
        make_flight("F1", departure=0, duration=60, origin="CDG", destination="JFK"),
        make_flight("F2", departure=1000, duration=60, origin="LHR", destination="FRA"),
    ]
    with pytest.raises(ValueError, match="continuity error"):
        AircraftRotation(flights).propagate_delay()


def test_multiple_aircraft_require_independent_continuity():
    flights = [
        make_flight("F1", aircraft_id="A1", departure=0, duration=60, origin="CDG", destination="JFK"),
        make_flight("F2", aircraft_id="A1", departure=120, duration=60, origin="JFK", destination="LHR"),
        make_flight("F3", aircraft_id="A2", departure=0, duration=60, origin="FRA", destination="AMS"),
        make_flight("F4", aircraft_id="A2", departure=120, duration=60, origin="AMS", destination="DXB"),
    ]
    assert len(AircraftRotation(flights).propagate_delay()) == 4


def test_repeated_build_is_idempotent():
    flights = make_continuous_pair(
        first_duration=60,
        second_departure=120,
    )
    rotation = AircraftRotation(flights)

    first = rotation.build()
    second = rotation.build()

    assert len(first["A1"]) == 2
    assert len(second["A1"]) == 2
    assert rotation.propagate_delay()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("scheduled_departure", float("nan")),
        ("scheduled_departure", float("inf")),
        ("scheduled_departure", float("-inf")),
        ("scheduled_arrival", float("nan")),
        ("scheduled_arrival", float("inf")),
        ("duration", float("nan")),
        ("duration", float("inf")),
        ("minimum_turnaround_minutes", float("nan")),
        ("minimum_turnaround_minutes", float("inf")),
        ("delay_minutes", float("nan")),
    ],
)
def test_nonfinite_schedule_values_are_rejected(field, value):
    values = {
        "flight_id": "F1",
        "origin": "CDG",
        "destination": "JFK",
        "scheduled_departure": 0,
        "scheduled_arrival": 60,
        "duration": 60,
        "aircraft_id": "A1",
        "minimum_turnaround_minutes": 45,
    }
    values[field] = value
    with pytest.raises(ValueError, match="finite"):
        Flight(**values)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_direct_delay_is_rejected(value):
    flight = make_flight("F1")
    with pytest.raises(ValueError, match="finite"):
        AircraftRotation([flight]).propagate_delay({"F1": value})


def test_conflicting_scheduled_timestamps_are_rejected():
    with pytest.raises(ValueError, match="scheduled_arrival"):
        Flight(
            flight_id="F1",
            origin="CDG",
            destination="JFK",
            scheduled_departure=100,
            scheduled_arrival=200,
            duration=60,
            aircraft_id="A1",
        )


def test_actual_timestamps_must_not_be_supplied_as_inputs():
    with pytest.raises(ValueError, match="simulation outputs"):
        Flight(
            flight_id="F1",
            origin="CDG",
            destination="JFK",
            scheduled_departure=100,
            duration=60,
            aircraft_id="A1",
            actual_departure=120,
            actual_arrival=180,
        )


def test_legacy_duration_and_turnaround_are_explicit():
    from app.models.flight import LEGACY_DURATION_MINUTES, LEGACY_TURNAROUND_MINUTES

    flight = Flight(
        flight_id="F1",
        origin="CDG",
        destination="JFK",
        departure_time=100,
        schedule_mode="legacy",
    )
    assert LEGACY_DURATION_MINUTES == 60.0
    assert LEGACY_TURNAROUND_MINUTES == 45.0
    assert flight.duration == LEGACY_DURATION_MINUTES
    assert flight.minimum_turnaround_minutes == LEGACY_TURNAROUND_MINUTES


def test_strict_loader_requires_reference_sets():
    with pytest.raises(ValueError, match="known-airport"):
        load_schedule(strict=True)


def test_strict_loader_rejects_unknown_aircraft():
    with pytest.raises(ValueError, match="known-aircraft"):
        load_schedule(
            known_airports={"CDG", "JFK", "LHR", "FRA", "DXB", "AMS", "HND", "LAX"},
            strict=True,
        )


def test_strict_model_rejects_unknown_aircraft():
    flight = make_flight("F1", aircraft_id="UNKNOWN")
    with pytest.raises(ValueError, match="UNKNOWN"):
        AircraftRotation(
            [flight],
            aircraft_ids={"OTHER"},
            strict=True,
        ).build()


def test_direct_delay_only_on_next_leg():
    flights = make_continuous_pair(
        first_duration=60,
        second_departure=200,
        turnaround=45,
    )
    results = AircraftRotation(flights).propagate_delay({"F2": 30})
    assert results[1]["direct_delay"] == 30
    assert results[1]["propagated_delay"] == 0
    assert results[1]["flight"].delay_minutes == 30


def test_only_propagated_delay():
    flights = make_continuous_pair(
        first_duration=100,
        second_departure=120,
        turnaround=45,
    )
    results = AircraftRotation(flights).propagate_delay()
    assert results[1]["direct_delay"] == 0
    assert results[1]["propagated_delay"] == 25


def test_direct_and_propagated_with_direct_dominating():
    flights = make_continuous_pair(
        first_duration=100,
        second_departure=120,
        turnaround=45,
    )
    results = AircraftRotation(flights).propagate_delay({"F1": 20, "F2": 100})
    assert results[1]["direct_delay"] == 100
    assert results[1]["propagated_delay"] == 0
    assert results[1]["flight"].delay_minutes == 100


def test_direct_and_propagated_with_propagated_dominating():
    flights = make_continuous_pair(
        first_duration=100,
        second_departure=120,
        turnaround=45,
    )
    results = AircraftRotation(flights).propagate_delay({"F1": 20, "F2": 10})
    assert results[1]["direct_delay"] == 10
    assert results[1]["propagated_delay"] == 35
    assert results[1]["flight"].delay_minutes == 45


def test_direct_and_propagated_equal_constraints():
    flights = make_continuous_pair(
        first_duration=100,
        second_departure=120,
        turnaround=45,
    )
    results = AircraftRotation(flights).propagate_delay({"F1": 20, "F2": 45})
    assert results[1]["direct_delay"] == 45
    assert results[1]["propagated_delay"] == 0
    assert results[1]["flight"].delay_minutes == 45


def test_later_new_direct_delay_after_earlier_delay():
    flights = make_continuous_pair(
        first_duration=100,
        second_departure=150,
        turnaround=45,
    )
    results = AircraftRotation(flights).propagate_delay({"F1": 20, "F2": 20})
    assert results[1]["direct_delay"] == 20
    assert results[1]["propagated_delay"] == 0
    assert results[1]["flight"].delay_minutes == 20
