import plotly.graph_objects as go
import networkx as nx

class NetworkDashboard:

    def create_dashboard(self, graph):

        pos = nx.spring_layout(graph)

        edge_x = []
        edge_y = []

        for edge in graph.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]

            edge_x.append(x0)
            edge_x.append(x1)
            edge_x.append(None)

            edge_y.append(y0)
            edge_y.append(y1)
            edge_y.append(None)

        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            line=dict(width=1),
            hoverinfo='none',
            mode='lines'
        )

        node_x = []
        node_y = []
        text = []

        for node in graph.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            text.append(node)

        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode='markers+text',
            text=text,
            textposition="top center",
            hoverinfo='text',
            marker=dict(size=12)
        )

        fig = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                title="Global Airline Network",
                showlegend=False
            )
        )

        fig.show()
