import numpy as np
import random
from app.network.global_network import build_network
from app.propagation.cascade_engine import propagate_delay


def run_network_simulation(
    runs=500,
    start_airport=None,
    initial_delay=None,
    seed=None,
):
    if isinstance(runs, bool) or not isinstance(runs, int) or runs <= 0:
        raise ValueError("runs must be a positive integer")
    if initial_delay is not None:
        if not isinstance(initial_delay, (int, float)):
            raise TypeError("initial_delay must be numeric")
        if initial_delay < 0:
            raise ValueError("initial_delay must be non-negative")

    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    graph = build_network()
    nodes = list(graph.nodes)
    if not graph.nodes:
        raise ValueError("Network dataset is empty")
    if start_airport is not None:
        if start_airport not in graph:
            raise ValueError(f"Unknown start airport: {start_airport}")

    all_max_delays = []
    affected_airports = set()
    for _ in range(runs):
        start = start_airport or random.choice(nodes)
        disruption = (
            float(initial_delay)
            if initial_delay is not None
            else random.uniform(30, 120)
        )
        delays = propagate_delay(graph, start, disruption)
        positive = {
            airport: delay
            for airport, delay in delays.items()
            if delay > 0
        }
        affected_airports.update(positive)
        all_max_delays.append(max(positive.values(), default=0.0))

    mean_network_delay = float(np.mean(all_max_delays))
    p95_network_delay = float(np.percentile(all_max_delays, 95))
    max_delay = float(max(all_max_delays, default=0.0))

    return {
        "mean_network_delay": mean_network_delay,
        "p95_network_delay": p95_network_delay,
        "max_delay": max_delay,
        "affected_airports": sorted(affected_airports),
        "runs": runs,
    }
