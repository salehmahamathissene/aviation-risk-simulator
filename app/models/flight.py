from pydantic import BaseModel

class Flight(BaseModel):

    flight_number: str
    origin: str
    destination: str
    delay_minutes: int = 0
