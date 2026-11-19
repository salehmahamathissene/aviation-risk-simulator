import random

import pytest

from app.analytics.risk_engine import RiskEngine
from app.data.loader import load_schedule
from app.disruptions.disruption_engine import DisruptionEngine
from app.models.flight import (
    LEGACY_DURATION_MINUTES,
    LEGACY_TURNAROUND_MINUTES,
    Flight,
)
from app.network.airline_network import AirlineNetwork
from app.network.flight_network import FlightNetwork
from app.propagation.delay_propagation import DelayPropagation
from app.rotation.aircraft_rotation import AircraftRotation
from app.simulation.event_engine import EventEngine
from app.simulation.event_simulator import AirlineSimulation
from app.simulation.events import FlightArrivalEvent, FlightDepartureEvent


def legacy_flight(
    flight_id="F1",
    origin="CDG",
    destination="JFK",
    departure=100,
):
    return Flight(
        flight_id=flight_id,
        origin=origin,
        destination=destination,
        departure_time=departure,
        aircraft_id="A1",
        passengers=150,
    )


def test_legacy_attributes_remain_mapped_to_canonical_fields():
    flight = Flight(
        flight_id="F1",
        origin="CDG",
        destination="JFK",
        departure_time=100,
        arrival_time=180,
        aircraft="A1",
        delay=25,
        passengers=120,
        arrived=False,
        cancelled=False,
    )

    assert flight.departure_time == 100
    assert flight.arrival_time == 180
    assert flight.aircraft == "A1"
    assert flight.delay == 25
    assert flight.delay_minutes == 25
    assert flight.passengers == 120
    assert flight.arrived is False
    assert flight.cancelled is False

    flight.departure_time = 110
    flight.arrival_time = 190
    flight.aircraft = "A2"
    flight.delay = 30
    assert flight.scheduled_departure == 110
    assert flight.scheduled_arrival == 190
    assert flight.aircraft_id == "A2"
    assert flight.delay_minutes == 30


def test_passenger_preservation_and_risk_cost():
    flight = legacy_flight()
    flight.delay = 20

    cost = RiskEngine().compute_cost([flight])

    assert flight.passengers == 150
    assert cost == 20 * 150 * 5


def test_legacy_delay_and_delay_minutes_must_not_conflict():
    with pytest.raises(ValueError, match="delay and delay_minutes"):
        Flight(
            flight_id="F1",
            origin="CDG",
            destination="JFK",
            departure_time=100,
            aircraft="A1",
            delay=10,
            delay_minutes=20,
        )


def test_cancel_and_uncancel_methods_keep_simulation_state_consistent():
    flight = legacy_flight()
    flight.delay = 15

    flight.cancel()
    assert flight.cancelled is True
    assert flight.status == "cancelled"
    assert flight.arrived is False

    flight.uncancel()
    assert flight.cancelled is False
    assert flight.status == "delayed"
    assert flight.arrived is False


def test_delay_reset_returns_flight_to_scheduled_status():
    flight = legacy_flight()
    flight.delay = 15
    assert flight.status == "delayed"

    flight.delay = 0

    assert flight.delay_minutes == 0
    assert flight.status == "scheduled"


@pytest.mark.parametrize(
    ("status", "cancelled"),
    [
        ("cancelled", False),
        ("scheduled", True),
        ("delayed", True),
    ],
)
def test_contradictory_status_and_cancellation_are_rejected(status, cancelled):
    with pytest.raises(ValueError, match="contradict"):
        Flight(
            flight_id="F1",
            origin="CDG",
            destination="JFK",
            scheduled_departure=100,
            duration=60,
            aircraft_id="A1",
            status=status,
            cancelled=cancelled,
        )


def test_boolean_passenger_count_is_rejected():
    with pytest.raises(ValueError, match="passengers"):
        Flight(
            flight_id="F1",
            origin="CDG",
            destination="JFK",
            scheduled_departure=100,
            duration=60,
            aircraft_id="A1",
            passengers=True,
        )


def test_legacy_departure_setter_preserves_arrival_chronology():
    flight = legacy_flight(departure=100)
    flight.arrival_time = 180

    flight.departure_time = 200

    assert flight.scheduled_departure == 200
    assert flight.scheduled_arrival == 280
    assert flight.duration == 80


def test_strict_schedule_rejects_unknown_fields():
    with pytest.raises(ValueError, match="unknown fields"):
        Flight(
            flight_id="F1",
            origin="CDG",
            destination="JFK",
            scheduled_departure=100,
            duration=60,
            aircraft_id="A1",
            minimum_turnaround_minutes=45,
            schedule_mode="strict",
            unexpected="typo",
        )


def test_simpy_simulation_sets_arrival_state():
    flight = legacy_flight(departure=10)
    flight.delay = 5
    simulation = AirlineSimulation()
    simulation.add_flight(flight)

    simulation.run()

    assert flight.arrived is True


def test_cancelled_flight_is_not_processed_by_simpy():
    flight = legacy_flight(departure=10)
    flight.cancel()
    simulation = AirlineSimulation()
    simulation.add_flight(flight)

    simulation.run()

    assert flight.arrived is False
    assert flight.status == "cancelled"


def test_event_departure_and_arrival_state():
    flight = legacy_flight(departure=10)
    engine = EventEngine()

    FlightDepartureEvent(flight).process(engine)
    engine.run()

    assert flight.arrived is True


def test_positive_delay_event_terminates_and_schedules_once():
    flight = legacy_flight(departure=10)
    flight.delay = 5
    engine = EventEngine()

    FlightDepartureEvent(flight).process(engine)
    engine.run()

    assert flight.arrived is True
    assert engine.time == 75


def test_zero_delay_event_terminates_and_schedules_arrival():
    flight = legacy_flight(departure=10)
    flight.delay = 0
    engine = EventEngine()

    FlightDepartureEvent(flight).process(engine)
    engine.run()

    assert flight.arrived is True
    assert engine.time == 70


def test_cancelled_event_is_not_scheduled_as_normal_flight():
    flight = legacy_flight(departure=10)
    flight.cancel()
    engine = EventEngine()

    FlightDepartureEvent(flight).process(engine)

    assert engine.events == []


def test_disruption_applies_canonical_delay_update():
    flight = legacy_flight()
    flight.delay = 10
    random.seed(1)

    DisruptionEngine().apply(flight)

    assert flight.delay_minutes >= 10
    assert flight.delay == flight.delay_minutes


def test_cancelled_flight_is_not_disrupted():
    flight = legacy_flight()
    flight.cancel()

    DisruptionEngine().apply(flight)

    assert flight.delay_minutes == 0
    assert flight.status == "cancelled"


def test_delay_propagation_preserves_cancelled_flights():
    active = legacy_flight(flight_id="F1", origin="CDG", destination="JFK")
    canceled = legacy_flight(flight_id="F2", origin="CDG", destination="FRA")
    canceled.cancel()
    random.seed(2)

    disrupted = DelayPropagation().propagate_delays([active, canceled])

    assert [flight.flight_id for flight in disrupted] == ["F1", "F2"]
    assert canceled.cancelled is True
    assert canceled.delay_minutes == 0


def test_delay_propagation_uses_canonical_status_and_delay():
    active = legacy_flight(flight_id="F1", origin="CDG", destination="JFK")
    random.seed(2)

    disrupted = DelayPropagation().propagate_delays([active])

    assert disrupted[0].delay_minutes == disrupted[0].delay
    assert disrupted[0].status == "delayed"


def test_flight_network_generates_unique_canonical_flights():
    random.seed(4)
    flights = FlightNetwork().generate_network(["CDG", "JFK", "LHR"])

    assert flights
    ids = [flight.flight_id for flight in flights]
    assert len(ids) == len(set(ids))
    assert all(flight.schedule_mode == "legacy" for flight in flights)
    assert all(flight.duration == LEGACY_DURATION_MINUTES for flight in flights)
    assert all(
        flight.minimum_turnaround_minutes == LEGACY_TURNAROUND_MINUTES
        for flight in flights
    )


def test_airline_network_generates_unique_canonical_flights():
    random.seed(5)
    graph, flights = AirlineNetwork().generate_network(["CDG", "JFK", "LHR"])

    assert flights
    ids = [flight.flight_id for flight in flights]
    assert len(ids) == len(set(ids))
    assert graph.is_directed()
    assert all(flight.schedule_mode == "legacy" for flight in flights)
    assert all(flight.aircraft_id != "UNKNOWN" for flight in flights)


def test_repository_loader_still_loads_canonical_flights():
    flights = load_schedule(
        known_airports={
            "CDG", "JFK", "LHR", "FRA", "DXB", "AMS", "HND", "LAX"
        },
        known_aircraft_ids={"A1", "A2", "A3"},
    )
    assert len(flights) == 5
    assert all(isinstance(flight, Flight) for flight in flights)


def test_strict_rotation_requires_authoritative_aircraft_set():
    flight = Flight(
        flight_id="F1",
        origin="CDG",
        destination="JFK",
        scheduled_departure=0,
        duration=60,
        aircraft_id="A1",
        minimum_turnaround_minutes=45,
        schedule_mode="strict",
    )

    with pytest.raises(ValueError, match="authoritative known-aircraft"):
        AircraftRotation([flight], strict=True)


def test_strict_rotation_rejects_legacy_flight():
    flight = legacy_flight()

    with pytest.raises(ValueError, match="legacy flight"):
        AircraftRotation(
            [flight],
            aircraft_ids={"A1"},
            strict=True,
        ).build()


def test_strict_rotation_accepts_two_valid_legs():
    first = Flight(
        flight_id="F1",
        origin="CDG",
        destination="JFK",
        scheduled_departure=0,
        duration=60,
        aircraft_id="A1",
        minimum_turnaround_minutes=45,
        schedule_mode="strict",
    )
    second = Flight(
        flight_id="F2",
        origin="JFK",
        destination="LHR",
        scheduled_departure=120,
        duration=60,
        aircraft_id="A1",
        minimum_turnaround_minutes=45,
        schedule_mode="strict",
    )

    results = AircraftRotation(
        [first, second],
        aircraft_ids={"A1"},
        strict=True,
    ).propagate_delay()

    assert len(results) == 2


def test_unknown_delay_map_identifier_is_rejected():
    flight = legacy_flight()

    with pytest.raises(ValueError, match="Unknown delay-map"):
        AircraftRotation([flight]).propagate_delay({"NOT-A-FLIGHT": 10})


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_computed_timestamp_is_rejected(bad):
    flight = legacy_flight()
    with pytest.raises(ValueError, match="finite"):
        AircraftRotation([flight]).propagate_delay({"F1": bad})


def test_cancelled_rotation_skips_availability_processing():
    first = legacy_flight()
    second = legacy_flight(
        flight_id="F2",
        origin="JFK",
        destination="LHR",
        departure=120,
    )
    second.cancel()

    results = AircraftRotation([first, second]).propagate_delay()

    canceled = results[1]
    assert canceled["cancelled"] is True
    assert canceled["propagated_delay"] == 0
    assert canceled["flight"].actual_departure is None


def test_canceled_leg_breaks_rotation_delay_source_chain():
    first = legacy_flight()
    canceled = legacy_flight(
        flight_id="F2",
        origin="JFK",
        destination="LHR",
        departure=120,
    )
    canceled.cancel()
    later = legacy_flight(
        flight_id="F3",
        origin="LHR",
        destination="FRA",
        departure=180,
    )

    results = AircraftRotation([first, canceled, later]).propagate_delay(
        {"F1": 50, "F3": 20}
    )

    assert results[1]["cancelled"] is True
    assert results[2]["direct_delay"] == 20
    assert results[2]["propagated_delay"] == 0
    assert results[2]["delay_sources"] == ["F3"]
