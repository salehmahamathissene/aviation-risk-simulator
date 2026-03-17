import networkx as nx
import matplotlib.pyplot as plt

class NetworkVisualizer:

    def plot_network(self, graph):

        plt.figure(figsize=(10,8))

        pos = nx.spring_layout(graph)

        nx.draw(
            graph,
            pos,
            with_labels=True,
            node_size=2000,
            node_color="skyblue",
            font_size=10,
            arrows=True
        )

        plt.title("Airline Network Simulation")

        plt.show()
