from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models.flight import AircraftAssignment, Flight
from app.models.rotation_validation import (
    InitialAircraftPosition,
    TurnaroundConfig,
)
from app.rotation.aircraft_rotation import AircraftRotation


UTC = timezone.utc


def utc_flight(
    flight_id,
    origin,
    destination,
    departure,
    duration_minutes=60,
    aircraft_id="A1",
    aircraft_type="A320",
    leg_type="passenger",
    cancelled=False,
    cancellation_stage=None,
    cancellation_time_utc=None,
    cancellation_position_airport=None,
    cancellation_position_status="unknown",
    aircraft_assignment_authoritative=True,
):
    departure_utc = departure
    arrival_utc = departure + timedelta(minutes=duration_minutes)
    return Flight(
        flight_id=flight_id,
        origin=origin,
        destination=destination,
        scheduled_departure=0,
        scheduled_arrival=duration_minutes,
        duration=duration_minutes,
        aircraft_id=aircraft_id,
        aircraft_type=aircraft_type,
        minimum_turnaround_minutes=45,
        scheduled_departure_utc=departure_utc,
        scheduled_arrival_utc=arrival_utc,
        departure_timezone="UTC",
        arrival_timezone="UTC",
        leg_type=leg_type,
        cancelled=cancelled,
        status="cancelled" if cancelled else "scheduled",
        cancellation_stage=cancellation_stage,
        cancellation_time_utc=cancellation_time_utc,
        cancellation_position_airport=cancellation_position_airport,
        cancellation_position_status=cancellation_position_status,
        aircraft_assignment_authoritative=aircraft_assignment_authoritative,
        aircraft_id_source="authoritative" if aircraft_assignment_authoritative else "synthetic_demo",
        schedule_mode="strict",
    )


def strict_config(turnaround=45):
    return TurnaroundConfig(
        default_minimum_turnaround_minutes=turnaround,
        source="test_configuration",
    )


def initial_position(
    aircraft_id="A1",
    airport="CDG",
    at=None,
):
    return InitialAircraftPosition(
        aircraft_id=aircraft_id,
        airport=airport,
        availability_time_utc=at or datetime(2026, 1, 1, 8, 0, tzinfo=UTC),
        source="authoritative_test_fixture",
    )


def validate(
    flights,
    turnaround=45,
    known_aircraft=None,
    aircraft_types=None,
    initial_positions=None,
):
    return AircraftRotation(flights).validate_rotation(
        known_aircraft_ids=known_aircraft or {"A1"},
        aircraft_types=aircraft_types,
        initial_positions=initial_positions,
        turnaround_config=strict_config(turnaround),
        strict=True,
    )


def test_duplicate_flight_id_is_invalid_schedule():
    flights = [
        utc_flight("F1", "CDG", "JFK", datetime(2026, 1, 1, 9, 0, tzinfo=UTC)),
        utc_flight("F1", "JFK", "LHR", datetime(2026, 1, 1, 11, 0, tzinfo=UTC)),
    ]
    result = validate(
        flights,
        initial_positions={"A1": initial_position()},
    )
    assert result.outcome == "INVALID_SCHEDULE"
    assert any(issue.code == "DUPLICATE_FLIGHT_ID" for issue in result.issues)


def test_missing_authoritative_assignment_is_incomplete():
    flight = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        aircraft_id="UNKNOWN",
    )
    result = validate(
        [flight],
        initial_positions={"UNKNOWN": initial_position("UNKNOWN", "CDG")},
    )
    assert result.outcome == "INCOMPLETE_ROTATION"
    assert result.valid is False
    assert any(issue.code == "MISSING_AIRCRAFT_ASSIGNMENT" for issue in result.issues)


def test_explicit_unknown_authoritative_aircraft_is_invalid():
    flight = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        aircraft_id="A99",
    )
    result = validate(
        [flight],
        initial_positions={"A99": initial_position("A99", "CDG")},
    )
    assert result.outcome == "INVALID_SCHEDULE"
    assert result.valid is False
    assert any(issue.code == "UNKNOWN_AUTHORITATIVE_AIRCRAFT" for issue in result.issues)


def test_non_authoritative_assignment_is_incomplete():
    flight = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        aircraft_assignment_authoritative=False,
    )
    result = validate(
        [flight],
        initial_positions={"A1": initial_position()},
    )
    assert result.outcome == "INCOMPLETE_ROTATION"
    assert any(issue.code == "NON_AUTHORITATIVE_AIRCRAFT_ASSIGNMENT" for issue in result.issues)


def test_aircraft_type_conflict_is_invalid_schedule():
    flight = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        aircraft_type="B737",
    )
    result = validate(
        [flight],
        aircraft_types={"A1": "A320"},
        initial_positions={"A1": initial_position()},
    )
    assert result.outcome == "INVALID_SCHEDULE"
    assert any(issue.code == "AIRCRAFT_TYPE_CONTRADICTION" for issue in result.issues)


def test_authoritative_assignment_type_conflicting_with_flight_and_catalogue_is_invalid():
    flight = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
    )
    flight.aircraft_assignments = [
        AircraftAssignment(
            aircraft_id="A1",
            aircraft_type="B737",
            authoritative=True,
        )
    ]
    result = validate(
        [flight],
        aircraft_types={"A1": "A320"},
        initial_positions={"A1": initial_position()},
    )
    assert result.outcome == "INVALID_SCHEDULE"
    assert result.valid is False
    assert any(issue.code == "AIRCRAFT_TYPE_CONTRADICTION" for issue in result.issues)


def test_overlapping_aircraft_assignments_are_infeasible():
    flights = [
        utc_flight("F1", "CDG", "JFK", datetime(2026, 1, 1, 9, 0, tzinfo=UTC), 120),
        utc_flight("F2", "JFK", "LHR", datetime(2026, 1, 1, 10, 30, tzinfo=UTC), 60),
    ]
    result = validate(
        flights,
        initial_positions={"A1": initial_position(at=datetime(2026, 1, 1, 8, 0, tzinfo=UTC))},
    )
    assert result.outcome == "INFEASIBLE_ROTATION"
    assert any(issue.code == "OVERLAPPING_AIRCRAFT_ASSIGNMENT" for issue in result.issues)


def test_missing_strict_turnaround_config_is_incomplete():
    flight = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
    )
    following = utc_flight(
        "F2",
        "JFK",
        "LHR",
        datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
    )
    result = AircraftRotation([flight, following]).validate_rotation(
        known_aircraft_ids={"A1"},
        initial_positions={"A1": initial_position()},
        turnaround_config=None,
        strict=True,
    )
    assert result.outcome == "INCOMPLETE_ROTATION"
    missing_config_issues = [
        issue for issue in result.issues
        if issue.code == "MISSING_TURNAROUND_CONFIG"
    ]
    assert len(missing_config_issues) == 1


def test_exact_turnaround_boundary_is_valid():
    flights = [
        utc_flight("F1", "CDG", "JFK", datetime(2026, 1, 1, 9, 0, tzinfo=UTC), 60),
        utc_flight("F2", "JFK", "LHR", datetime(2026, 1, 1, 10, 45, tzinfo=UTC), 60),
    ]
    result = validate(
        flights,
        turnaround=45,
        initial_positions={"A1": initial_position(at=datetime(2026, 1, 1, 8, 0, tzinfo=UTC))},
    )
    assert result.outcome == "VALID"
    assert result.valid is True


def test_insufficient_turnaround_is_infeasible():
    flights = [
        utc_flight("F1", "CDG", "JFK", datetime(2026, 1, 1, 9, 0, tzinfo=UTC), 60),
        utc_flight("F2", "JFK", "LHR", datetime(2026, 1, 1, 10, 30, tzinfo=UTC), 60),
    ]
    result = validate(
        flights,
        turnaround=45,
        initial_positions={"A1": initial_position(at=datetime(2026, 1, 1, 8, 0, tzinfo=UTC))},
    )
    assert result.outcome == "INFEASIBLE_ROTATION"
    assert any(issue.code == "TURNAROUND_BELOW_MINIMUM" for issue in result.issues)


def test_disconnected_airports_are_infeasible():
    flights = [
        utc_flight("F1", "CDG", "JFK", datetime(2026, 1, 1, 9, 0, tzinfo=UTC), 60),
        utc_flight("F2", "LHR", "FRA", datetime(2026, 1, 1, 11, 0, tzinfo=UTC), 60),
    ]
    result = validate(
        flights,
        initial_positions={"A1": initial_position(at=datetime(2026, 1, 1, 8, 0, tzinfo=UTC))},
    )
    assert result.outcome == "INFEASIBLE_ROTATION"
    assert any(issue.code in {"AIRPORT_CONTINUITY_MISMATCH", "AIRCRAFT_POSITION_MISMATCH"} for issue in result.issues)


def test_valid_ferry_movement():
    flights = [
        utc_flight("F1", "CDG", "JFK", datetime(2026, 1, 1, 9, 0, tzinfo=UTC), 60),
        utc_flight(
            "FM1",
            "JFK",
            "LHR",
            datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
            60,
            leg_type="ferry",
        ),
    ]
    result = validate(
        flights,
        initial_positions={"A1": initial_position(at=datetime(2026, 1, 1, 8, 0, tzinfo=UTC))},
    )
    assert result.outcome == "VALID"


def test_ferry_origin_mismatch_with_known_position_is_infeasible():
    flights = [
        utc_flight("F1", "CDG", "JFK", datetime(2026, 1, 1, 9, 0, tzinfo=UTC), 60),
        utc_flight(
            "FM1",
            "LHR",
            "FRA",
            datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
            60,
            leg_type="ferry",
        ),
    ]
    result = validate(
        flights,
        initial_positions={"A1": initial_position(at=datetime(2026, 1, 1, 8, 0, tzinfo=UTC))},
    )
    assert result.outcome == "INFEASIBLE_ROTATION"
    assert any(issue.code == "FERRY_ORIGIN_MISMATCH" for issue in result.issues)


def test_ferry_with_missing_utc_is_incomplete():
    ferry = utc_flight(
        "FM1",
        "CDG",
        "LHR",
        datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
        leg_type="ferry",
    )
    ferry.scheduled_departure_utc = None
    ferry.scheduled_arrival_utc = None
    result = validate(
        [ferry],
        initial_positions={"A1": initial_position(at=datetime(2026, 1, 1, 8, 0, tzinfo=UTC))},
    )
    assert result.outcome == "INCOMPLETE_ROTATION"
    assert any(issue.code in {"FERRY_TIMESTAMPS_MISSING", "MISSING_UTC_TIMESTAMPS"} for issue in result.issues)


def test_before_departure_cancellation_uses_known_initial_position():
    canceled = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        cancelled=True,
        cancellation_stage="before_departure",
        cancellation_position_airport="CDG",
        cancellation_position_status="at_airport",
    )
    following = utc_flight(
        "F2",
        "CDG",
        "LHR",
        datetime(2026, 1, 1, 9, 45, tzinfo=UTC),
    )
    result = validate(
        [canceled, following],
        initial_positions={"A1": initial_position(at=datetime(2026, 1, 1, 8, 0, tzinfo=UTC))},
    )
    assert result.outcome == "VALID"


def test_before_departure_cancellation_without_position_is_incomplete():
    canceled = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        cancelled=True,
        cancellation_stage="before_departure",
    )
    result = validate([canceled])
    assert result.outcome == "INCOMPLETE_ROTATION"


def test_after_departure_known_airport_position_can_establish_availability():
    canceled = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        cancelled=True,
        cancellation_stage="after_departure",
        cancellation_time_utc=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        cancellation_position_airport="JFK",
        cancellation_position_status="at_airport",
    )
    following = utc_flight(
        "F2",
        "JFK",
        "LHR",
        datetime(2026, 1, 1, 10, 45, tzinfo=UTC),
    )
    result = validate(
        [canceled, following],
        initial_positions={"A1": initial_position(at=datetime(2026, 1, 1, 8, 0, tzinfo=UTC))},
    )
    assert result.outcome == "VALID"


def test_after_departure_known_position_without_applicable_turnaround_is_incomplete():
    config = strict_config(45)
    canceled = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        cancelled=True,
        cancellation_stage="after_departure",
        cancellation_time_utc=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        cancellation_position_airport="JFK",
        cancellation_position_status="at_airport",
    )
    canceled.cancellation_position_status = "in_flight"
    canceled.cancellation_position_airport = None
    following = utc_flight(
        "F2",
        "JFK",
        "LHR",
        datetime(2026, 1, 1, 10, 45, tzinfo=UTC),
    )
    result = AircraftRotation([canceled, following]).validate_rotation(
        known_aircraft_ids={"A1"},
        initial_positions={"A1": initial_position(at=datetime(2026, 1, 1, 8, 0, tzinfo=UTC))},
        turnaround_config=config,
        strict=True,
    )
    assert result.outcome == "INCOMPLETE_ROTATION"
    assert any(issue.code == "CANCELLATION_POSITION_UNKNOWN" for issue in result.issues)


def test_after_departure_unknown_position_is_incomplete():
    canceled = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        cancelled=True,
        cancellation_stage="after_departure",
        cancellation_time_utc=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        cancellation_position_status="unknown",
    )
    result = validate(
        [canceled],
        initial_positions={"A1": initial_position(at=datetime(2026, 1, 1, 8, 0, tzinfo=UTC))},
    )
    assert result.outcome == "INCOMPLETE_ROTATION"


def test_unknown_cancellation_stage_is_incomplete():
    canceled = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        cancelled=True,
        cancellation_stage="unknown",
    )
    result = validate(
        [canceled],
        initial_positions={"A1": initial_position(at=datetime(2026, 1, 1, 8, 0, tzinfo=UTC))},
    )
    assert result.outcome == "INCOMPLETE_ROTATION"


def test_missing_utc_timestamp_is_incomplete():
    flight = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
    )
    flight.scheduled_departure_utc = None
    flight.scheduled_arrival_utc = None
    result = validate(
        [flight],
        initial_positions={"A1": initial_position()},
    )
    assert result.outcome == "INCOMPLETE_ROTATION"


def test_naive_utc_timestamp_is_incomplete():
    flight = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0),
    )
    result = validate(
        [flight],
        initial_positions={"A1": initial_position()},
    )
    assert result.outcome == "INCOMPLETE_ROTATION"


def test_mixed_chain_outcomes_preserve_schedule_precedence():
    valid_flights = [
        utc_flight("F1", "CDG", "JFK", datetime(2026, 1, 1, 9, 0, tzinfo=UTC), 60, aircraft_id="A1"),
        utc_flight("F2", "JFK", "LHR", datetime(2026, 1, 1, 11, 0, tzinfo=UTC), 60, aircraft_id="A1"),
    ]
    incomplete_flight = utc_flight(
        "F3",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        aircraft_id="A2",
    )
    result = validate(
        valid_flights + [incomplete_flight],
        known_aircraft={"A1", "A2"},
        initial_positions={"A1": initial_position(at=datetime(2026, 1, 1, 8, 0, tzinfo=UTC))},
    )
    assert result.outcome == "INCOMPLETE_ROTATION"
    assert len(result.aircraft_chains) == 2


def test_strict_missing_turnaround_config_is_incomplete_without_crash():
    flight = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
    )
    result = AircraftRotation([flight]).validate_rotation(
        known_aircraft_ids={"A1"},
        initial_positions={"A1": initial_position()},
        turnaround_config=None,
        strict=True,
    )
    assert result.outcome == "INCOMPLETE_ROTATION"
    assert any(issue.code == "MISSING_TURNAROUND_CONFIG" for issue in result.issues)


def test_strict_missing_flight_aircraft_type_is_incomplete():
    flight = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        aircraft_type=None,
    )
    result = validate(
        [flight],
        aircraft_types={"A1": "A320"},
        initial_positions={"A1": initial_position()},
    )
    assert result.outcome == "INCOMPLETE_ROTATION"
    assert any(issue.code == "MISSING_AIRCRAFT_TYPE" for issue in result.issues)


def test_strict_missing_catalogue_aircraft_type_is_incomplete():
    flight = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        aircraft_type="A320",
    )
    result = validate(
        [flight],
        aircraft_types={"A1": None},
        initial_positions={"A1": initial_position()},
    )
    assert result.outcome == "INCOMPLETE_ROTATION"
    assert any(issue.code == "MISSING_CATALOGUE_AIRCRAFT_TYPE" for issue in result.issues)


def test_before_departure_cancellation_position_must_match_known_position():
    canceled = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        cancelled=True,
        cancellation_stage="before_departure",
        cancellation_position_airport="LHR",
        cancellation_position_status="at_airport",
    )
    result = validate(
        [canceled],
        initial_positions={"A1": initial_position(airport="CDG")},
    )
    assert result.outcome == "INFEASIBLE_ROTATION"
    assert any(issue.code == "CANCELLATION_POSITION_MISMATCH" for issue in result.issues)


def test_blank_aircraft_assignment_is_incomplete():
    flight = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
    )
    flight.aircraft_id = ""
    result = validate([flight], initial_positions={})
    assert result.outcome == "INCOMPLETE_ROTATION"
    assert result.valid is False
    assert any(issue.code == "MISSING_AIRCRAFT_ASSIGNMENT" for issue in result.issues)


def test_blank_assignment_does_not_skip_strict_schedule_validation():
    with pytest.raises(ValidationError, match="origin and destination must be different"):
        Flight(
            flight_id="F1",
            origin="CDG",
            destination="CDG",
            scheduled_departure=0,
            scheduled_arrival=60,
            duration=60,
            aircraft_id="",
            aircraft_type="A320",
            minimum_turnaround_minutes=45,
            schedule_mode="strict",
        )


def test_multiple_authoritative_assignment_records_are_invalid():
    flight = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
    )
    flight.aircraft_assignments = [
        AircraftAssignment(aircraft_id="A1", aircraft_type="A320", authoritative=True),
        AircraftAssignment(aircraft_id="A2", aircraft_type="A320", authoritative=True),
    ]
    result = validate(
        [flight],
        initial_positions={"A1": initial_position(), "A2": initial_position("A2", "CDG")},
    )
    assert result.outcome == "INVALID_SCHEDULE"
    assert any(issue.code == "MULTIPLE_AUTHORITATIVE_ASSIGNMENTS" for issue in result.issues)


def test_canceled_middle_leg_connected_following_flight_with_known_position():
    canceled = utc_flight(
        "F2",
        "JFK",
        "LHR",
        datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        cancelled=True,
        cancellation_stage="before_departure",
        cancellation_position_airport="JFK",
        cancellation_position_status="at_airport",
    )
    following = utc_flight(
        "F3",
        "JFK",
        "FRA",
        datetime(2026, 1, 1, 10, 45, tzinfo=UTC),
    )
    result = validate(
        [canceled, following],
        initial_positions={"A1": initial_position(airport="JFK")},
    )
    assert result.outcome == "VALID"


def test_canceled_leg_followed_by_disconnected_flight_is_infeasible():
    canceled = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        cancelled=True,
        cancellation_stage="before_departure",
        cancellation_position_airport="CDG",
        cancellation_position_status="at_airport",
    )
    following = utc_flight(
        "F2",
        "LHR",
        "FRA",
        datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
    )
    result = validate(
        [canceled, following],
        initial_positions={"A1": initial_position(airport="CDG")},
    )
    assert result.outcome == "INFEASIBLE_ROTATION"


def test_canceled_leg_followed_by_unknown_position_is_incomplete():
    canceled = utc_flight(
        "F1",
        "CDG",
        "JFK",
        datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        cancelled=True,
        cancellation_stage="after_departure",
        cancellation_time_utc=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        cancellation_position_status="unknown",
    )
    following = utc_flight(
        "F2",
        "JFK",
        "LHR",
        datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
    )
    result = validate([canceled, following])
    assert result.outcome == "INCOMPLETE_ROTATION"
