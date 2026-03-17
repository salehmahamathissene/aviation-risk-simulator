from fastapi import FastAPI
from app.network.global_network import GlobalAirNetwork
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

@app.get("/simulate/global")
def simulate():

    network = GlobalAirNetwork()

    network.add_route("CDG", "JFK")
    network.add_route("JFK", "LAX")
    network.add_route("LAX", "HND")

    sim = GlobalMonteCarlo()

    result = sim.run(network, runs=2000)

    return result

@app.get("/simulate/real")   # 🔥 THIS LINE IS THE KEY
def simulate():
    sim = GlobalMonteCarlo(runs=2000)
    return sim.run()
