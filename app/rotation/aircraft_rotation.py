from collections import defaultdict
import math
from typing import Iterable, Mapping, Optional
from datetime import datetime, timezone

from app.models.flight import Flight
from app.models.rotation_validation import (
    AircraftChainResult,
    AircraftPositionState,
    InitialAircraftPosition,
    ScheduleValidationResult,
    TurnaroundConfig,
    ValidationIssue,
)


class AircraftRotation:
    """
    Deterministic flight-leg rotation simulator.

    The missing source turnaround is an explicit illustration value supplied
    by the caller. It does not represent an operational airline value.

    build() is a legacy compatibility grouping method. In particular, it
    bypasses strict ferry/positioning origin validation and does not perform
    structured outcome validation. Use validate_rotation(strict=True) for
    ferry integrity, position, cancellation, and turnaround validation.
    """

    def __init__(
        self,
        flights: Iterable[Flight],
        aircraft_ids: Optional[Iterable[str]] = None,
        strict: bool = False,
    ):
        self.flights = list(flights)
        if strict and aircraft_ids is None:
            raise ValueError(
                "strict rotation requires an authoritative known-aircraft set"
            )
        self.aircraft_ids = (
            set(aircraft_ids) if aircraft_ids is not None else None
        )
        self.strict = strict
        self.rotation = defaultdict(list)

    def build(self):
        """Group flights using legacy continuity rules.

        This method does not perform strict ferry-movement validation;
        validate_rotation() validates ferry origins and movement instead.
        """
        self.rotation = defaultdict(list)
        flight_ids = set()

        for flight in self.flights:
            if flight.flight_id in flight_ids:
                raise ValueError(
                    f"Duplicate flight identifier: {flight.flight_id}"
                )
            flight_ids.add(flight.flight_id)

            if self.aircraft_ids is not None:
                if flight.aircraft_id not in self.aircraft_ids:
                    raise ValueError(
                        f"Unknown aircraft identifier: {flight.aircraft_id}"
                    )
            if self.strict and flight.aircraft_id == "UNKNOWN":
                raise ValueError(
                    "Aircraft identifier UNKNOWN is not valid"
                )

            self.rotation[flight.aircraft_id].append(flight)

        for aircraft_id, legs in self.rotation.items():
            legs.sort(
                key=lambda flight: (
                    flight.scheduled_departure,
                    flight.flight_id,
                )
            )

            for index in range(1, len(legs)):
                previous = legs[index - 1]
                current = legs[index]
                is_movement_leg = current.leg_type in ("ferry", "positioning")
                if not is_movement_leg and current.origin != previous.destination:
                    raise ValueError(
                        "Aircraft rotation continuity error for "
                        f"{aircraft_id}: {previous.flight_id} ends at "
                        f"{previous.destination}, but {current.flight_id} "
                        f"starts at {current.origin}"
                    )

            if self.strict:
                for leg in legs:
                    if leg.schedule_mode != "strict":
                        raise ValueError(
                            f"Strict rotation rejected legacy flight: {leg.flight_id}"
                        )
                    if leg.minimum_turnaround_minutes is None:
                        raise ValueError(
                            f"Strict rotation requires turnaround for: {leg.flight_id}"
                        )
                    if leg.aircraft_id == "UNKNOWN":
                        raise ValueError(
                            f"Strict rotation rejected unknown aircraft: {leg.flight_id}"
                        )

        return dict(self.rotation)

    def propagate_delay(
        self,
        delay_map: Optional[Mapping[str, float]] = None,
    ):
        direct_delays = delay_map or {}
        known_flight_ids = {
            flight.flight_id
            for flight in self.flights
        }
        unknown_delay_ids = set(direct_delays).difference(known_flight_ids)
        if unknown_delay_ids:
            raise ValueError(
                "Unknown delay-map flight identifier(s): "
                + ", ".join(sorted(str(item) for item in unknown_delay_ids))
            )
        rotations = self.build()
        results = []

        for aircraft_id in sorted(rotations):
            legs = rotations[aircraft_id]
            previous_arrival = None
            previous_sources = set()

            for index, original in enumerate(legs):
                flight = original.model_copy(deep=True)
                if flight.cancelled or flight.status == "cancelled":
                    flight.actual_departure = None
                    flight.actual_arrival = None
                    flight.delay_minutes = 0.0
                    flight.status = "cancelled"
                    flight.cancelled = True
                    previous_arrival = None
                    previous_sources = set()
                    results.append(
                        {
                            "flight": flight,
                            "direct_delay": 0.0,
                            "propagated_delay": 0.0,
                            "contributions": [],
                            "delay_sources": [],
                            "aircraft_id": aircraft_id,
                            "cancelled": True,
                            "rotation_chain": "incomplete",
                        }
                    )
                    continue

                direct_delay = float(direct_delays.get(flight.flight_id, 0.0))
                if not math.isfinite(direct_delay) or direct_delay < 0:
                    raise ValueError(
                        f"Delay for {flight.flight_id} must be finite and non-negative"
                    )

                sources = set()
                if direct_delay > 0:
                    sources.add(flight.flight_id)

                actual_departure = flight.scheduled_departure + direct_delay
                propagated_delay = 0.0
                contributions = []
                if direct_delay > 0:
                    contributions.append(
                        {
                            "source_flight_id": flight.flight_id,
                            "cause": "direct",
                            "minutes": direct_delay,
                        }
                    )

                if index > 0:
                    earliest_departure = (
                        previous_arrival
                        + flight.minimum_turnaround_minutes
                        if previous_arrival is not None
                        else None
                    )
                    if (
                        earliest_departure is not None
                        and actual_departure < earliest_departure
                    ):
                        propagated = earliest_departure - actual_departure
                        if not math.isfinite(propagated):
                            raise ValueError(
                                "Propagated delay must be a finite number"
                            )
                        actual_departure = earliest_departure
                        propagated_delay = propagated
                        sources.update(previous_sources)
                        contributions.append(
                            {
                                "source_flight_ids": sorted(previous_sources),
                                "cause": "turnaround",
                                "minutes": propagated_delay,
                            }
                        )

                duration = (
                    flight.duration
                    if flight.duration is not None
                    else (
                        flight.scheduled_arrival - flight.scheduled_departure
                    )
                )
                if not math.isfinite(duration) or duration <= 0:
                    raise ValueError(
                        f"Duration for {flight.flight_id} must be finite and positive"
                    )
                actual_arrival = actual_departure + duration
                if (
                    not math.isfinite(actual_departure)
                    or not math.isfinite(actual_arrival)
                    or actual_arrival < actual_departure
                ):
                    raise ValueError(
                        f"Computed timestamps for {flight.flight_id} are invalid"
                    )

                flight.actual_departure = actual_departure
                flight.actual_arrival = actual_arrival
                total_delay = max(
                    0.0,
                    actual_departure - flight.scheduled_departure,
                )
                if not math.isfinite(total_delay):
                    raise ValueError(
                        f"Total delay for {flight.flight_id} must be finite"
                    )
                if abs(total_delay - (direct_delay + propagated_delay)) > 1e-9:
                    raise ValueError(
                        "Direct and propagated delays do not reconcile "
                        "with total delay"
                    )
                flight.delay_minutes = total_delay
                if total_delay > 0:
                    flight.status = "delayed"

                results.append(
                    {
                        "flight": flight,
                        "direct_delay": direct_delay,
                        "propagated_delay": propagated_delay,
                        "contributions": contributions,
                        "delay_sources": sorted(sources),
                        "aircraft_id": aircraft_id,
                    }
                )

                previous_arrival = actual_arrival
                if index == 0 and not sources:
                    previous_sources = {flight.flight_id}
                elif sources:
                    previous_sources = sources

        return results

    def validate_rotation(
        self,
        known_aircraft_ids: Optional[Iterable[str]] = None,
        aircraft_types: Optional[Mapping[str, str]] = None,
        initial_positions: Optional[Mapping[str, InitialAircraftPosition]] = None,
        turnaround_config: Optional[TurnaroundConfig] = None,
        strict: bool = False,
    ) -> ScheduleValidationResult:
        overall_issues = []
        chain_results = []
        known_aircraft = (
            set(known_aircraft_ids)
            if known_aircraft_ids is not None
            else None
        )
        aircraft_types = dict(aircraft_types or {})
        initial_positions = dict(initial_positions or {})

        if strict:
            if known_aircraft is None:
                overall_issues.append(
                    ValidationIssue(
                        code="MISSING_AIRCRAFT_CATALOGUE",
                        outcome="INCOMPLETE_ROTATION",
                        message="Strict validation requires a known-aircraft catalogue",
                        source="validation_configuration",
                    )
                )
            if turnaround_config is None:
                overall_issues.append(
                    ValidationIssue(
                        code="MISSING_TURNAROUND_CONFIG",
                        outcome="INCOMPLETE_ROTATION",
                        message="Strict validation requires explicit turnaround configuration",
                        source="validation_configuration",
                    )
                )
        else:
            if turnaround_config is None:
                turnaround_config = TurnaroundConfig(
                    default_minimum_turnaround_minutes=45.0,
                    source="legacy_illustrative",
                )

        flight_ids = set()
        duplicate_ids = set()
        for flight in self.flights:
            if flight.flight_id in flight_ids:
                duplicate_ids.add(flight.flight_id)
            flight_ids.add(flight.flight_id)

            authoritative_assignments = [
                assignment
                for assignment in getattr(flight, "aircraft_assignments", [])
                if assignment.authoritative
            ]
            assignment_ids = {
                assignment.aircraft_id
                for assignment in authoritative_assignments
            }
            if len(assignment_ids) > 1:
                overall_issues.append(
                    ValidationIssue(
                        code="MULTIPLE_AUTHORITATIVE_ASSIGNMENTS",
                        outcome="INVALID_SCHEDULE",
                        message="Flight has multiple contradictory authoritative aircraft assignments",
                        flight_ids=[flight.flight_id],
                        aircraft_id=",".join(sorted(assignment_ids)),
                    )
                )

            if flight.aircraft_id == "UNKNOWN" or not flight.aircraft_id.strip():
                overall_issues.append(
                    ValidationIssue(
                        code="MISSING_AIRCRAFT_ASSIGNMENT",
                        outcome="INCOMPLETE_ROTATION",
                        message="Flight has no authoritative aircraft assignment",
                        flight_ids=[flight.flight_id],
                        aircraft_id=None,
                    )
                )
            elif known_aircraft is not None and flight.aircraft_assignment_authoritative:
                if flight.aircraft_id not in known_aircraft:
                    overall_issues.append(
                        ValidationIssue(
                            code="UNKNOWN_AUTHORITATIVE_AIRCRAFT",
                            outcome="INVALID_SCHEDULE",
                            message="Authoritative aircraft assignment is absent from the known catalogue",
                            flight_ids=[flight.flight_id],
                            aircraft_id=flight.aircraft_id,
                        )
                    )

            if flight.aircraft_assignment_authoritative is False:
                overall_issues.append(
                    ValidationIssue(
                        code="NON_AUTHORITATIVE_AIRCRAFT_ASSIGNMENT",
                        outcome="INCOMPLETE_ROTATION",
                        message="Aircraft assignment is not authoritative",
                        flight_ids=[flight.flight_id],
                        aircraft_id=flight.aircraft_id,
                        severity="warning",
                    )
                )

            aircraft_record_type = aircraft_types.get(flight.aircraft_id)
            authoritative_types = []
            if aircraft_record_type is not None:
                authoritative_types.append(aircraft_record_type)
            authoritative_types.extend(
                assignment.aircraft_type
                for assignment in authoritative_assignments
                if assignment.aircraft_type is not None
            )
            has_type_contradiction = (
                len(set(authoritative_types)) > 1
                or (
                    flight.aircraft_type is not None
                    and any(
                        authoritative_type != flight.aircraft_type
                        for authoritative_type in authoritative_types
                    )
                )
            )
            if has_type_contradiction:
                configured_type = next(
                    (
                        authoritative_type
                        for authoritative_type in authoritative_types
                        if authoritative_type != flight.aircraft_type
                    ),
                    authoritative_types[0],
                )
                overall_issues.append(
                    ValidationIssue(
                        code="AIRCRAFT_TYPE_CONTRADICTION",
                        outcome="INVALID_SCHEDULE",
                        message="Flight and authoritative aircraft records contain conflicting aircraft types",
                        flight_ids=[flight.flight_id],
                        aircraft_id=flight.aircraft_id,
                        observed_value=flight.aircraft_type,
                        configured_value=configured_type,
                    )
                )

            if strict:
                if flight.scheduled_departure_utc is None or flight.scheduled_arrival_utc is None:
                    overall_issues.append(
                        ValidationIssue(
                            code="MISSING_UTC_TIMESTAMPS",
                            outcome="INCOMPLETE_ROTATION",
                            message="Strict validation requires timezone-aware UTC departure and arrival",
                            flight_ids=[flight.flight_id],
                            aircraft_id=flight.aircraft_id,
                        )
                    )

                if flight.aircraft_type is None:
                    overall_issues.append(
                        ValidationIssue(
                            code="MISSING_AIRCRAFT_TYPE",
                            outcome="INCOMPLETE_ROTATION",
                            message="Strict validation requires aircraft type evidence",
                            flight_ids=[flight.flight_id],
                            aircraft_id=flight.aircraft_id,
                        )
                    )
                elif flight.aircraft_id in aircraft_types:
                    catalogue_type = aircraft_types.get(flight.aircraft_id)
                    if catalogue_type is None:
                        overall_issues.append(
                            ValidationIssue(
                                code="MISSING_CATALOGUE_AIRCRAFT_TYPE",
                                outcome="INCOMPLETE_ROTATION",
                                message="Catalogue aircraft type evidence is missing",
                                flight_ids=[flight.flight_id],
                                aircraft_id=flight.aircraft_id,
                            )
                        )
                elif (
                    flight.scheduled_departure_utc is not None
                    and flight.scheduled_arrival_utc is not None
                    and (
                        flight.scheduled_departure_utc.tzinfo is None
                        or flight.scheduled_arrival_utc.tzinfo is None
                    )
                ):
                    overall_issues.append(
                        ValidationIssue(
                            code="NAIVE_UTC_TIMESTAMPS",
                            outcome="INCOMPLETE_ROTATION",
                            message="UTC timestamps must be timezone-aware",
                            flight_ids=[flight.flight_id],
                            aircraft_id=flight.aircraft_id,
                        )
                    )
                elif (
                    flight.scheduled_departure_utc is not None
                    and flight.scheduled_arrival_utc is not None
                    and flight.scheduled_departure_utc.tzinfo is not None
                    and flight.scheduled_arrival_utc.tzinfo is not None
                    and flight.scheduled_arrival_utc < flight.scheduled_departure_utc
                ):
                    overall_issues.append(
                        ValidationIssue(
                            code="INVALID_UTC_CHRONOLOGY",
                            outcome="INVALID_SCHEDULE",
                            message="UTC arrival precedes UTC departure",
                            flight_ids=[flight.flight_id],
                            aircraft_id=flight.aircraft_id,
                        )
                    )

        for flight_id in sorted(duplicate_ids):
            overall_issues.append(
                ValidationIssue(
                    code="DUPLICATE_FLIGHT_ID",
                    outcome="INVALID_SCHEDULE",
                    message=f"Duplicate flight identifier: {flight_id}",
                    flight_ids=[flight_id],
                )
            )

        rotations = defaultdict(list)
        for flight in self.flights:
            if flight.aircraft_id:
                rotations[flight.aircraft_id].append(flight)
        for aircraft_id, legs in rotations.items():
            legs.sort(
                key=lambda flight: (
                    (
                        flight.scheduled_departure_utc.timestamp()
                        if strict
                        and flight.scheduled_departure_utc is not None
                        and flight.scheduled_departure_utc.tzinfo is not None
                        else flight.scheduled_departure
                    ),
                    flight.flight_id,
                )
            )

        for aircraft_id in sorted(rotations):
            legs = rotations[aircraft_id]
            chain_issues = []
            initial_state = None
            if aircraft_id in initial_positions:
                initial = initial_positions[aircraft_id]
                initial_state = AircraftPositionState(
                    aircraft_id=aircraft_id,
                    airport=initial.airport,
                    availability_time_utc=initial.availability_time_utc,
                    position_known=True,
                    position_status="at_airport",
                    source=initial.source,
                )
            elif strict:
                initial_state = AircraftPositionState(
                    aircraft_id=aircraft_id,
                    position_known=False,
                    position_status="unknown",
                    source="missing_initial_position",
                )
                chain_issues.append(
                    ValidationIssue(
                        code="MISSING_INITIAL_POSITION",
                        outcome="INCOMPLETE_ROTATION",
                        message="Strict chain has no authoritative initial position",
                        aircraft_id=aircraft_id,
                        flight_ids=[leg.flight_id for leg in legs],
                    )
                )

            state = initial_state
            previous_actual_arrival = None
            previous_leg = None

            for leg_index in range(1, len(legs)):
                previous = legs[leg_index - 1]
                current = legs[leg_index]
                if previous.cancelled or current.cancelled:
                    continue
                if strict:
                    if (
                        previous.scheduled_arrival_utc is None
                        or current.scheduled_departure_utc is None
                    ):
                        continue
                    previous_end = previous.scheduled_arrival_utc
                    current_start = current.scheduled_departure_utc
                else:
                    previous_end = (
                        previous.scheduled_arrival
                        if previous.scheduled_arrival is not None
                        else previous.scheduled_departure + (previous.duration or 0)
                    )
                    current_start = current.scheduled_departure
                if current_start < previous_end:
                    chain_issues.append(
                        ValidationIssue(
                            code="OVERLAPPING_AIRCRAFT_ASSIGNMENT",
                            outcome="INFEASIBLE_ROTATION",
                            message="Aircraft is assigned to overlapping flights",
                            flight_ids=[previous.flight_id, current.flight_id],
                            aircraft_id=aircraft_id,
                        )
                    )

            for leg_index, leg in enumerate(legs):
                if leg_index > 0:
                    previous = legs[leg_index - 1]
                    if previous.cancelled or previous.status == "cancelled":
                        pass
                    else:
                        if leg.leg_type == "passenger" or leg.leg_type == "cargo":
                            if previous.destination != leg.origin:
                                chain_issues.append(
                                    ValidationIssue(
                                        code="AIRPORT_CONTINUITY_MISMATCH",
                                        outcome="INFEASIBLE_ROTATION",
                                        message="Next flight origin does not match previous flight destination",
                                        flight_ids=[previous.flight_id, leg.flight_id],
                                        aircraft_id=aircraft_id,
                                    )
                                )
                    if leg.leg_type in ("ferry", "positioning"):
                        if state is not None and state.position_known:
                            if leg.origin != state.airport:
                                chain_issues.append(
                                    ValidationIssue(
                                        code="FERRY_ORIGIN_MISMATCH",
                                        outcome="INFEASIBLE_ROTATION",
                                        message="Ferry/positioning origin differs from known aircraft position",
                                        flight_ids=[leg.flight_id],
                                        aircraft_id=aircraft_id,
                                    )
                                )
                        else:
                            chain_issues.append(
                                ValidationIssue(
                                    code="FERRY_POSITION_UNKNOWN",
                                    outcome="INCOMPLETE_ROTATION",
                                    message="Ferry/positioning origin cannot be established",
                                    flight_ids=[leg.flight_id],
                                    aircraft_id=aircraft_id,
                                )
                            )

                if leg.leg_type in ("ferry", "positioning") and strict:
                    if (
                        leg.scheduled_departure_utc is None
                        or leg.scheduled_arrival_utc is None
                    ):
                        chain_issues.append(
                            ValidationIssue(
                            code="FERRY_TIMESTAMPS_MISSING",
                            outcome="INCOMPLETE_ROTATION",
                            message="Ferry/positioning leg requires explicit UTC timestamps",
                            flight_ids=[leg.flight_id],
                            aircraft_id=aircraft_id,
                            )
                        )
                    elif (
                        leg.scheduled_departure_utc is not None
                        and leg.scheduled_arrival_utc is not None
                        and (
                            leg.scheduled_departure_utc.tzinfo is None
                            or leg.scheduled_arrival_utc.tzinfo is None
                        )
                    ):
                        chain_issues.append(
                            ValidationIssue(
                                code="NAIVE_FERRY_UTC_TIMESTAMPS",
                                outcome="INCOMPLETE_ROTATION",
                                message="Ferry/positioning UTC timestamps must be timezone-aware",
                                flight_ids=[leg.flight_id],
                                aircraft_id=aircraft_id,
                            )
                        )
                    elif (
                        leg.scheduled_departure_utc.tzinfo is not None
                        and leg.scheduled_arrival_utc.tzinfo is not None
                        and leg.scheduled_arrival_utc < leg.scheduled_departure_utc
                    ):
                        chain_issues.append(
                            ValidationIssue(
                            code="INVALID_FERRY_TIMESTAMPS",
                            outcome="INVALID_SCHEDULE",
                            message="Ferry/positioning arrival precedes departure",
                            flight_ids=[leg.flight_id],
                            aircraft_id=aircraft_id,
                            )
                        )

                if leg.leg_type in ("ferry", "positioning"):
                    if state is not None and state.position_known:
                        if leg.origin != state.airport:
                            already_reported = any(
                                issue.code == "FERRY_ORIGIN_MISMATCH"
                                and leg.flight_id in issue.flight_ids
                                for issue in chain_issues
                            )
                            if not already_reported:
                                chain_issues.append(
                                    ValidationIssue(
                                        code="FERRY_ORIGIN_MISMATCH",
                                        outcome="INFEASIBLE_ROTATION",
                                        message="Ferry/positioning origin differs from known aircraft position",
                                        flight_ids=[leg.flight_id],
                                        aircraft_id=aircraft_id,
                                    )
                                )
                    elif leg_index == 0:
                        chain_issues.append(
                            ValidationIssue(
                                code="FERRY_POSITION_UNKNOWN",
                                outcome="INCOMPLETE_ROTATION",
                                message="Ferry/positioning initial position is unknown",
                                flight_ids=[leg.flight_id],
                                aircraft_id=aircraft_id,
                            )
                        )

                if leg.cancelled or leg.status == "cancelled":
                    stage = leg.cancellation_stage
                    if stage == "before_departure":
                        if state is not None and state.position_known:
                            if (
                                leg.cancellation_position_status == "at_airport"
                                and leg.cancellation_position_airport
                                and leg.cancellation_position_airport != state.airport
                            ):
                                chain_issues.append(
                                    ValidationIssue(
                                        code="CANCELLATION_POSITION_MISMATCH",
                                        outcome="INFEASIBLE_ROTATION",
                                        message="Before-departure cancellation is inconsistent with known aircraft position",
                                        flight_ids=[leg.flight_id],
                                        aircraft_id=aircraft_id,
                                    )
                                )
                        else:
                            chain_issues.append(
                                ValidationIssue(
                                    code="CANCELLATION_POSITION_UNKNOWN",
                                    outcome="INCOMPLETE_ROTATION",
                                    message="Before-departure cancellation position is unknown",
                                    flight_ids=[leg.flight_id],
                                    aircraft_id=aircraft_id,
                                )
                            )
                        continue

                    if stage == "after_departure":
                        if (
                            leg.cancellation_position_status == "at_airport"
                            and leg.cancellation_position_airport
                            and leg.cancellation_time_utc is not None
                        ):
                            state = AircraftPositionState(
                                aircraft_id=aircraft_id,
                                airport=leg.cancellation_position_airport,
                                availability_time_utc=leg.cancellation_time_utc,
                                position_known=True,
                                position_status="at_airport",
                                source="cancellation_record",
                            )
                        else:
                            state = AircraftPositionState(
                                aircraft_id=aircraft_id,
                                position_known=False,
                                position_status="unknown",
                                source="cancellation_position_unknown",
                            )
                            chain_issues.append(
                                ValidationIssue(
                                    code="CANCELLATION_POSITION_UNKNOWN",
                                    outcome="INCOMPLETE_ROTATION",
                                    message="After-departure cancellation position is unknown",
                                    flight_ids=[leg.flight_id],
                                    aircraft_id=aircraft_id,
                                )
                            )
                        continue

                    state = AircraftPositionState(
                        aircraft_id=aircraft_id,
                        position_known=False,
                        position_status="unknown",
                        source="cancellation_stage_unknown",
                    )
                    chain_issues.append(
                        ValidationIssue(
                            code="CANCELLATION_STAGE_UNKNOWN",
                            outcome="INCOMPLETE_ROTATION",
                            message="Cancellation stage is unknown",
                            flight_ids=[leg.flight_id],
                            aircraft_id=aircraft_id,
                        )
                    )
                    continue

                if strict:
                    if (
                        leg.scheduled_departure_utc is None
                        or leg.scheduled_arrival_utc is None
                    ):
                        chain_issues.append(
                            ValidationIssue(
                                code="MISSING_UTC_TIMESTAMPS",
                                outcome="INCOMPLETE_ROTATION",
                                message="Strict leg requires UTC timestamps",
                                flight_ids=[leg.flight_id],
                                aircraft_id=aircraft_id,
                            )
                        )
                        continue
                    if (
                        leg.scheduled_departure_utc.tzinfo is None
                        or leg.scheduled_arrival_utc.tzinfo is None
                    ):
                        chain_issues.append(
                            ValidationIssue(
                                code="NAIVE_UTC_TIMESTAMPS",
                                outcome="INCOMPLETE_ROTATION",
                                message="UTC timestamps must be timezone-aware",
                                flight_ids=[leg.flight_id],
                                aircraft_id=aircraft_id,
                            )
                        )
                        continue
                    departure = leg.scheduled_departure_utc
                    arrival = leg.scheduled_arrival_utc
                else:
                    departure = leg.scheduled_departure
                    arrival = (
                        leg.scheduled_arrival
                        if leg.scheduled_arrival is not None
                        else leg.scheduled_departure + (leg.duration or 0)
                    )

                if state is not None and state.position_known:
                    if leg.origin != state.airport:
                        chain_issues.append(
                            ValidationIssue(
                                code="AIRCRAFT_POSITION_MISMATCH",
                                outcome="INFEASIBLE_ROTATION",
                                message="Flight origin differs from known aircraft position",
                                flight_ids=[leg.flight_id],
                                aircraft_id=aircraft_id,
                            )
                        )

                    if state.availability_time_utc is not None:
                        if strict:
                            if turnaround_config is not None:
                                minimum = turnaround_config.minimum_for(
                                    leg.aircraft_type,
                                    leg.origin,
                                )
                                from datetime import timedelta
                                earliest = state.availability_time_utc + timedelta(
                                    minutes=minimum
                                )
                                if departure < earliest:
                                    chain_issues.append(
                                        ValidationIssue(
                                            code="TURNAROUND_BELOW_MINIMUM",
                                            outcome="INFEASIBLE_ROTATION",
                                            message="Configured turnaround is not available",
                                            flight_ids=[leg.flight_id],
                                            aircraft_id=aircraft_id,
                                            observed_value=str(
                                                (departure - state.availability_time_utc).total_seconds() / 60
                                            ),
                                            configured_value=str(minimum),
                                            unit="minutes",
                                            source=turnaround_config.source,
                                        )
                                    )

                previous_actual_arrival = arrival
                state = AircraftPositionState(
                    aircraft_id=aircraft_id,
                    airport=leg.destination,
                    availability_time_utc=arrival,
                    position_known=True,
                    position_status="at_airport",
                    source="leg_destination",
                )
                previous_leg = leg

            chain_outcome = "VALID"
            if any(issue.outcome == "INVALID_SCHEDULE" for issue in chain_issues):
                chain_outcome = "INVALID_SCHEDULE"
            elif any(issue.outcome == "INFEASIBLE_ROTATION" for issue in chain_issues):
                chain_outcome = "INFEASIBLE_ROTATION"
            elif any(issue.outcome == "INCOMPLETE_ROTATION" for issue in chain_issues):
                chain_outcome = "INCOMPLETE_ROTATION"

            chain_results.append(
                AircraftChainResult(
                    aircraft_id=aircraft_id,
                    outcome=chain_outcome,
                    flight_ids=[leg.flight_id for leg in legs],
                    issues=chain_issues,
                    warnings=[issue for issue in chain_issues if issue.severity == "warning"],
                    initial_state=initial_state,
                    final_state=state,
                )
            )

        all_issues = list(overall_issues)
        for chain in chain_results:
            all_issues.extend(chain.issues)

        outcome = "VALID"
        if any(issue.outcome == "INVALID_SCHEDULE" for issue in all_issues):
            outcome = "INVALID_SCHEDULE"
        elif any(issue.outcome == "INFEASIBLE_ROTATION" for issue in all_issues):
            outcome = "INFEASIBLE_ROTATION"
        elif any(issue.outcome == "INCOMPLETE_ROTATION" for issue in all_issues):
            outcome = "INCOMPLETE_ROTATION"

        configuration = {
            "strict": strict,
            "timezone_basis": "UTC" if strict else "legacy_relative",
            "turnaround_configured": turnaround_config is not None,
        }
        if turnaround_config is not None:
            configuration["turnaround_source"] = turnaround_config.source
            configuration["default_minimum_turnaround_minutes"] = (
                turnaround_config.default_minimum_turnaround_minutes
            )

        return ScheduleValidationResult(
            outcome=outcome,
            valid=(outcome == "VALID"),
            aircraft_chains=chain_results,
            issues=all_issues,
            warnings=[issue for issue in all_issues if issue.severity == "warning"],
            configuration=configuration,
        )
