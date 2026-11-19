from datetime import datetime
from typing import Literal, Optional

import math

from pydantic import BaseModel, ConfigDict, model_validator


RotationOutcome = Literal[
    "VALID",
    "INVALID_SCHEDULE",
    "INFEASIBLE_ROTATION",
    "INCOMPLETE_ROTATION",
]


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: Literal["error", "warning"] = "error"
    outcome: RotationOutcome
    message: str
    flight_ids: list[str] = []
    aircraft_id: Optional[str] = None
    source: str = "schedule_validation"
    observed_value: Optional[str] = None
    configured_value: Optional[str] = None
    unit: Optional[str] = None


class AircraftPositionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aircraft_id: str
    airport: Optional[str] = None
    availability_time_utc: Optional[datetime] = None
    position_known: bool
    position_status: Literal[
        "at_airport",
        "in_flight",
        "unknown",
        "not_applicable",
    ]
    source: str


class InitialAircraftPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aircraft_id: str
    airport: str
    availability_time_utc: datetime
    source: str


class AircraftCatalogueEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aircraft_id: str
    aircraft_type: Optional[str] = None
    assignment_authoritative: bool = True
    source: str


class TurnaroundConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_minimum_turnaround_minutes: float
    source: str
    aircraft_type_overrides: dict[str, float] = {}
    airport_overrides: dict[str, float] = {}

    @model_validator(mode="after")
    def validate_turnaround_values(self):
        values = [self.default_minimum_turnaround_minutes]
        values.extend(self.aircraft_type_overrides.values())
        values.extend(self.airport_overrides.values())
        if any(
            not math.isfinite(float(value)) or float(value) < 0
            for value in values
        ):
            raise ValueError(
                "Turnaround values must be finite and non-negative"
            )
        return self

    def minimum_for(
        self,
        aircraft_type: Optional[str],
        airport: Optional[str],
    ) -> float:
        if airport is not None and airport in self.airport_overrides:
            return self.airport_overrides[airport]
        if aircraft_type is not None and aircraft_type in self.aircraft_type_overrides:
            return self.aircraft_type_overrides[aircraft_type]
        return self.default_minimum_turnaround_minutes


class AircraftChainResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aircraft_id: str
    outcome: RotationOutcome
    flight_ids: list[str] = []
    issues: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    initial_state: Optional[AircraftPositionState] = None
    final_state: Optional[AircraftPositionState] = None


class ScheduleValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: RotationOutcome
    valid: bool
    aircraft_chains: list[AircraftChainResult] = []
    issues: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    configuration: dict = {}
