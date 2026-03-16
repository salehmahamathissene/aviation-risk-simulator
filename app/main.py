from fastapi import FastAPI
from app.montecarlo.simulator import run_simulation

app = FastAPI(
    title="Aviation Risk Simulator",
    description="Simulation platform for airline disruption modeling",
    version="1.0"
)


@app.get("/")
def root():
    return {"message": "Aviation Risk Simulator Running"}


@app.get("/simulate")
def simulate():

    result = run_simulation(1000)

    return result
