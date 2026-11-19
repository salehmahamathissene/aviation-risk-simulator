from typing import Optional

from pydantic import BaseModel


class Flight(BaseModel):
    flight_id: str = ""
    origin: str
    destination: str
    departure_time: int = 0
    duration: int = 0
    aircraft_id: str = ""
    delay_minutes: int = 0
