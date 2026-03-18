from fastapi import FastAPI
from app.montecarlo.simulator import GlobalMonteCarlo

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
