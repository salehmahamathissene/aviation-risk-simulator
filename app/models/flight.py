import math
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator


FlightStatus = Literal["scheduled", "delayed", "cancelled"]
LEGACY_DURATION_MINUTES = 60.0
LEGACY_TURNAROUND_MINUTES = 45.0
SCHEDULE_TOLERANCE_MINUTES = 1e-9
STRICT_FLIGHT_FIELDS = {
    "flight_id",
    "origin",
    "destination",
    "scheduled_departure",
    "scheduled_arrival",
    "duration",
    "aircraft_id",
    "aircraft_type",
    "minimum_turnaround_minutes",
    "delay_minutes",
    "status",
    "schedule_mode",
    "passengers",
    "arrived",
    "cancelled",
    "scheduled_departure_utc",
    "scheduled_arrival_utc",
    "departure_timezone",
    "arrival_timezone",
    "leg_type",
    "cancellation_stage",
    "cancellation_time_utc",
    "cancellation_position_airport",
    "cancellation_position_status",
    "aircraft_assignment_authoritative",
    "aircraft_id_source",
    "aircraft_assignments",
}


class AircraftAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aircraft_id: str
    aircraft_type: Optional[str] = None
    authoritative: bool = True
    source: str = "schedule"


def require_finite_number(value: float, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a finite number")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite number") from exc
    if not math.isfinite(numeric):
        raise ValueError(f"{field_name} must be a finite number")
    return numeric


class Flight(BaseModel):
    model_config = ConfigDict(extra="allow")

    flight_id: str
    origin: str
    destination: str
    scheduled_departure: float
    scheduled_arrival: Optional[float] = None
    duration: Optional[float] = None
    aircraft_id: str = "UNKNOWN"
    aircraft_type: Optional[str] = None
    minimum_turnaround_minutes: float = LEGACY_TURNAROUND_MINUTES
    actual_departure: Optional[float] = None
    actual_arrival: Optional[float] = None
    delay_minutes: float = 0.0
    status: FlightStatus = "scheduled"
    schedule_mode: Literal["legacy", "strict"] = "legacy"
    passengers: int = 0
    arrived: bool = False
    cancelled: bool = False
    aircraft_assignment_authoritative: bool = True
    aircraft_id_source: str = "authoritative"
    aircraft_assignments: list[AircraftAssignment] = []
    scheduled_departure_utc: Optional[datetime] = None
    scheduled_arrival_utc: Optional[datetime] = None
    departure_timezone: Optional[str] = None
    arrival_timezone: Optional[str] = None
    leg_type: Literal["passenger", "cargo", "ferry", "positioning"] = "passenger"
    cancellation_stage: Optional[Literal["before_departure", "after_departure", "unknown"]] = None
    cancellation_time_utc: Optional[datetime] = None
    cancellation_position_airport: Optional[str] = None
    cancellation_position_status: Literal["at_airport", "in_flight", "unknown"] = "unknown"

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_fields(cls, values):
        if not isinstance(values, dict):
            return values
        values = dict(values)

        if values.get("schedule_mode") == "strict":
            unexpected = set(values).difference(STRICT_FLIGHT_FIELDS)
            if unexpected:
                raise ValueError(
                    "Strict schedule contains unknown fields: "
                    + ", ".join(sorted(unexpected))
                )

        if "passengers" in values and isinstance(values["passengers"], bool):
            raise ValueError("passengers must be an integer")

        if "scheduled_departure" not in values and "departure_time" in values:
            values["scheduled_departure"] = values["departure_time"]

        if "scheduled_arrival" not in values and "arrival_time" in values:
            values["scheduled_arrival"] = values["arrival_time"]

        if (
            "duration" not in values
            and "scheduled_arrival" not in values
            and values.get("schedule_mode", "legacy") != "strict"
        ):
            values["duration"] = LEGACY_DURATION_MINUTES

        if "aircraft_id" not in values and "aircraft" in values:
            values["aircraft_id"] = values["aircraft"]

        if (
            "departure_time" in values
            or "arrival_time" in values
            or "aircraft" in values
        ):
            values["schedule_mode"] = "legacy"

        if "passengers" in values:
            values["passengers"] = values["passengers"]
        if "arrived" in values:
            values["arrived"] = values["arrived"]
        if "cancelled" in values:
            values["cancelled"] = values["cancelled"]
        if "status" in values:
            status = values["status"]
            cancelled = values.get("cancelled")
            if status == "cancelled" and cancelled is False:
                raise ValueError(
                    "status='cancelled' contradicts cancelled=False"
                )
            if status != "cancelled" and cancelled is True:
                raise ValueError(
                    f"status={status!r} contradicts cancelled=True"
                )
            if values.get("cancelled") is True:
                values["status"] = "cancelled"
        if "delay" in values:
            legacy_delay = values["delay"]
            if "delay_minutes" in values:
                if not math.isfinite(float(legacy_delay)) or not math.isfinite(float(values["delay_minutes"])) or float(legacy_delay) != float(values["delay_minutes"]):
                    raise ValueError("delay and delay_minutes must match")
            values["delay_minutes"] = legacy_delay

        return values

    @model_validator(mode="after")
    def validate_schedule(self):
        authoritative_assignment_ids = [
            assignment.aircraft_id
            for assignment in self.aircraft_assignments
            if assignment.authoritative
        ]
        if len(set(authoritative_assignment_ids)) > 1:
            raise ValueError(
                "Multiple contradictory authoritative aircraft assignments"
            )
        if authoritative_assignment_ids:
            if self.aircraft_id == "UNKNOWN":
                self.aircraft_id = authoritative_assignment_ids[0]
            elif self.aircraft_id not in authoritative_assignment_ids:
                raise ValueError(
                    "Flight aircraft_id conflicts with authoritative assignments"
                )

        if (
            (self.scheduled_departure_utc is None)
            != (self.scheduled_arrival_utc is None)
        ):
            raise ValueError(
                "scheduled_departure_utc and scheduled_arrival_utc must be supplied together"
            )
        if self.scheduled_departure_utc is not None:
            if self.scheduled_arrival_utc is not None:
                if self.scheduled_arrival_utc < self.scheduled_departure_utc:
                    raise ValueError(
                        "scheduled_arrival_utc must not precede scheduled_departure_utc"
                    )

        if self.cancelled:
            if self.cancellation_stage == "before_departure":
                if (
                    self.cancellation_position_status == "at_airport"
                    and not self.cancellation_position_airport
                ):
                    raise ValueError(
                        "Before-departure cancellation at an airport requires cancellation_position_airport"
                    )
            elif self.cancellation_stage == "after_departure":
                if self.cancellation_time_utc is None:
                    raise ValueError(
                        "after-departure cancellation requires cancellation_time_utc"
                    )
                if (
                    self.cancellation_position_status == "at_airport"
                    and not self.cancellation_position_airport
                ):
                    raise ValueError(
                        "After-departure airport position requires cancellation_position_airport"
                    )
            elif self.cancellation_stage == "unknown":
                if self.cancellation_position_status == "at_airport":
                    raise ValueError(
                        "Unknown cancellation stage cannot establish an airport position"
                    )

        numeric_fields = {
            "scheduled_departure": self.scheduled_departure,
            "minimum_turnaround_minutes": self.minimum_turnaround_minutes,
            "delay_minutes": self.delay_minutes,
        }
        if self.scheduled_arrival is not None:
            numeric_fields["scheduled_arrival"] = self.scheduled_arrival
        if self.duration is not None:
            numeric_fields["duration"] = self.duration
        if self.actual_departure is not None:
            numeric_fields["actual_departure"] = self.actual_departure
        if self.actual_arrival is not None:
            numeric_fields["actual_arrival"] = self.actual_arrival

        for field_name, value in numeric_fields.items():
            require_finite_number(value, field_name)

        if not self.flight_id.strip():
            raise ValueError("flight_id must not be empty")
        if not self.origin.strip():
            raise ValueError("origin must not be empty")
        if not self.destination.strip():
            raise ValueError("destination must not be empty")
        if self.origin == self.destination:
            raise ValueError("origin and destination must be different")
        if self.scheduled_departure < 0:
            raise ValueError("scheduled_departure must be non-negative")
        if self.minimum_turnaround_minutes < 0:
            raise ValueError("minimum_turnaround_minutes must be non-negative")
        if self.delay_minutes < 0:
            raise ValueError("delay_minutes must be non-negative")
        if self.passengers < 0:
            raise ValueError("passengers must be non-negative")
        if isinstance(self.passengers, bool):
            raise ValueError("passengers must be an integer")

        if self.duration is not None and self.duration <= 0:
            raise ValueError("duration must be greater than zero")

        if self.schedule_mode == "strict":
            if "minimum_turnaround_minutes" not in self.model_fields_set:
                raise ValueError(
                    "strict mode requires an explicit minimum_turnaround_minutes"
                )

        if self.scheduled_arrival is None:
            if self.duration is None:
                if self.schedule_mode == "strict":
                    raise ValueError(
                        "strict mode requires duration or scheduled_arrival"
                    )
                self.duration = LEGACY_DURATION_MINUTES
            self.scheduled_arrival = self.scheduled_departure + self.duration
        elif self.duration is None:
            self.duration = self.scheduled_arrival - self.scheduled_departure
        elif abs(
            self.scheduled_arrival
            - (self.scheduled_departure + self.duration)
        ) > SCHEDULE_TOLERANCE_MINUTES:
            raise ValueError(
                "scheduled_arrival must equal scheduled_departure + duration"
            )

        if self.scheduled_arrival < self.scheduled_departure:
            raise ValueError("scheduled_arrival must not precede scheduled_departure")
        if self.duration is not None and self.duration <= 0:
            raise ValueError("duration must be greater than zero")

        if (self.actual_departure is None) != (self.actual_arrival is None):
            raise ValueError(
                "actual_departure and actual_arrival must be supplied together"
            )
        if (
            self.actual_departure is not None
            and self.actual_arrival is not None
        ):
            raise ValueError(
                "actual timestamps are simulation outputs and must not be supplied"
            )

        if self.cancelled:
            self.status = "cancelled"
            self.arrived = False
        elif self.status == "cancelled":
            raise ValueError(
                "status='cancelled' contradicts cancelled=False"
            )

        return self

    @property
    def departure_time(self) -> float:
        return self.scheduled_departure

    @departure_time.setter
    def departure_time(self, value: float) -> None:
        numeric = require_finite_number(value, "departure_time")
        if numeric < 0:
            raise ValueError("departure_time must be non-negative")
        previous_departure = self.scheduled_departure
        previous_arrival = self.scheduled_arrival
        self.scheduled_departure = numeric
        if previous_arrival is not None:
            delta = numeric - previous_departure
            shifted_arrival = previous_arrival + delta
            if shifted_arrival < numeric:
                raise ValueError(
                    "departure_time mutation leaves invalid arrival chronology"
                )
            self.scheduled_arrival = shifted_arrival
            self.duration = shifted_arrival - numeric

    @property
    def arrival_time(self) -> Optional[float]:
        return self.scheduled_arrival

    @arrival_time.setter
    def arrival_time(self, value: float) -> None:
        numeric = require_finite_number(value, "arrival_time")
        if numeric < self.scheduled_departure:
            raise ValueError("arrival_time must not precede departure_time")
        self.scheduled_arrival = numeric
        self.duration = numeric - self.scheduled_departure

    @property
    def delay(self) -> float:
        return self.delay_minutes

    @delay.setter
    def delay(self, value: float) -> None:
        numeric = require_finite_number(value, "delay")
        if numeric < 0:
            raise ValueError("delay must be non-negative")
        self.delay_minutes = numeric
        if numeric > 0 and not self.cancelled:
            self.status = "delayed"
        elif numeric == 0 and not self.cancelled:
            self.status = "scheduled"

    @property
    def aircraft(self) -> str:
        return self.aircraft_id

    @aircraft.setter
    def aircraft(self, value: str) -> None:
        if not str(value).strip():
            raise ValueError("aircraft must not be empty")
        self.aircraft_id = str(value)

    def cancel(self) -> None:
        self.cancelled = True
        self.status = "cancelled"
        self.arrived = False

    def uncancel(self) -> None:
        self.cancelled = False
        if self.delay_minutes > 0:
            self.status = "delayed"
        else:
            self.status = "scheduled"
