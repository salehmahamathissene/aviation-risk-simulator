from pydantic import BaseModel
from typing import List
from app.models.flight import Flight


class SimulationRequest(BaseModel):
    flights: List[Flight]
    runs: int = 1000
