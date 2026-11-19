from collections import defaultdict
import math
from typing import Iterable, Mapping, Optional

from app.models.flight import Flight


class AircraftRotation:
    """
    Deterministic flight-leg rotation simulator.

    The missing source turnaround is an explicit illustration value supplied
    by the caller. It does not represent an operational airline value.
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
                if current.origin != previous.destination:
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
