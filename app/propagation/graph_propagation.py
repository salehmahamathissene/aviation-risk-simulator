import random


def propagate_delay(G, start_node, initial_delay):

    delays = {node: 0 for node in G.nodes}
    delays[start_node] = initial_delay

    queue = [start_node]

    while queue:
        current = queue.pop(0)

        for neighbor in G.successors(current):
            spread = delays[current] * random.uniform(0.3, 0.7)

            if spread > delays[neighbor]:
                delays[neighbor] = spread
                queue.append(neighbor)

    return delays
