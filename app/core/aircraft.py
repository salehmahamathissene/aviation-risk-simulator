from pydantic import BaseModel

class Aircraft(BaseModel):
    tail_number: str
    aircraft_type: str
    capacity: int
    current_airport: str
