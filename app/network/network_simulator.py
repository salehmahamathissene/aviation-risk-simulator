import numpy as np
import random
from app.network.global_network import build_network
from app.propagation.cascade_engine import propagate_delay
from app.analytics.economics import compute_costs
from app.ai.recovery import suggest_recovery

def run_network_simulation(runs=500):

    G = build_network()

    all_total_delays = []
    cancellations = 0

    nodes = list(G.nodes)

    for _ in range(runs):
        start = random.choice(nodes)
        initial_delay = random.uniform(30, 120)

        delays = propagate_delay(G, start, initial_delay)

        total_delay = sum(delays.values())
        all_total_delays.append(total_delay)

        if total_delay > 5000:
            cancellations += 1

    mean_delay = np.mean(all_total_delays)
    p95 = np.percentile(all_total_delays, 95)

    economics = compute_costs(all_total_delays, cancellations)

    recommendation = suggest_recovery(mean_delay, random.random())

    return {
        "mean_delay": float(mean_delay),
        "p95_delay": float(p95),
        "cancelled_flights": cancellations,
        "runs": runs,
        "economics": economics,
        "recommendation": recommendation
    }
