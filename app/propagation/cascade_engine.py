import random

def propagate_delay(G, start_node, initial_delay):

    delays = {node: 0 for node in G.nodes}
    delays[start_node] = initial_delay

    queue = [start_node]

    while queue:
        node = queue.pop(0)

        for neighbor in G.successors(node):

            # propagation factor
            factor = random.uniform(0.3, 0.7)

            propagated = delays[node] * factor

            # only propagate if meaningful
            if propagated > 5:
                delays[neighbor] += propagated
                queue.append(neighbor)

    return delays
