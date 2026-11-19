from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.montecarlo.simulator import GlobalMonteCarlo
from app.network.network_simulator import run_network_simulation

app = FastAPI()


@app.get("/")
def root():
    return {
        "system": "Airline Network Disruption Simulation Engine",
        "version": "1.0.0",
        "capabilities": [
            "aircraft rotation modeling",
            "delay propagation analysis",
            "stochastic disruption simulation",
            "monte carlo risk evaluation",
            "network resilience analysis"
        ],
        "status": "operational"
    }


# 🔥 GLOBAL SIMULATION (clean, working)
@app.get("/simulate/global")
def simulate_global():
    sim = GlobalMonteCarlo(runs=2000)
    return sim.run()


# 🔥 REAL SIMULATION (same engine for now)
@app.get("/simulate/real")
def simulate_real():
    sim = GlobalMonteCarlo(runs=2000)
    return sim.run()


class NetworkSimulationRequest(BaseModel):
    runs: int = 500
    start_airport: str | None = None
    initial_delay: float | None = None
    seed: int | None = None


@app.post("/simulate/network")
def simulate_network(request: NetworkSimulationRequest):
    try:
        return run_network_simulation(
            runs=request.runs,
            start_airport=request.start_airport,
            initial_delay=request.initial_delay,
            seed=request.seed,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
