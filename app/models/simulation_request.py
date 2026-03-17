from pydantic import BaseModel
from typing import List


class Flight(BaseModel):
    flight_id: str
    origin: str
    destination: str
    departure_time: int
    duration: int
    aircraft_id: str


class SimulationRequest(BaseModel):
    flights: List[Flight]
    runs: int = 1000
