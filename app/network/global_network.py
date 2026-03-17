import networkx as nx


class GlobalAirNetwork:

    def __init__(self):

        self.graph = nx.DiGraph()

    def add_route(self, origin, destination):

        self.graph.add_edge(origin, destination)

    def airports(self):

        return list(self.graph.nodes)

    def routes(self):

        return list(self.graph.edges)

    def hub_centrality(self):

        return nx.betweenness_centrality(self.graph)
