import random

def propagate_delay(G, start_node, initial_delay):

    if start_node not in G:
        raise ValueError(f"Unknown start node: {start_node}")
    if not isinstance(initial_delay, (int, float)):
        raise TypeError("initial_delay must be numeric")
    if initial_delay < 0:
        raise ValueError("initial_delay must be non-negative")

    delays = {node: 0 for node in G.nodes}
    delays[start_node] = initial_delay

    queue = [start_node]
    depth = {start_node: 0}

    while queue:
        node = queue.pop(0)

        for neighbor in G.successors(node):
            # propagation factor
            factor = random.uniform(0.3, 0.7)

            propagated = delays[node] * factor

            # only propagate if meaningful
            if propagated > 5 and propagated > delays[neighbor]:
                next_depth = depth[node] + 1
                if next_depth > len(G.nodes):
                    continue
                delays[neighbor] = propagated
                depth[neighbor] = next_depth
                queue.append(neighbor)

    return delays
