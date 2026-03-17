from fastapi import FastAPI

from app.montecarlo.simulator import MonteCarloSimulator

app = FastAPI(title="Aviation Risk Simulator")

@app.get("/")
def root():
    return {"message": "Aviation Risk Simulator API"}

@app.get("/simulate")
def simulate():

    airports = [
        "KGL","NBO","ADD","JNB","CAI","LOS","CMN","DSS","ACC","ABJ",
        "CDG","LHR","FRA","AMS","MAD","BCN","FCO","IST","ZRH","VIE",
        "DXB","DOH","AUH","DEL","BOM","SIN","HKG","BKK","ICN","NRT",
        "JFK","LAX","ORD","ATL","DFW","MIA","SEA","DEN","SFO","YYZ"
    ]

    simulator = MonteCarloSimulator()

    result = simulator.run(airports, runs=1000)

    return result
