from pyvis.network import Network


def visualize_network(G):

    net = Network(height="600px", width="100%", directed=True)

    for node in G.nodes:
        net.add_node(node)

    for edge in G.edges:
        net.add_edge(edge[0], edge[1])

    net.save_graph("network.html")

    return "network.html"
