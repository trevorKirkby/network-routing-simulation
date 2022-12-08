from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

color_vals = plt.get_cmap('rainbow')
color_vals = {i:color_vals(i/7) for i in range(0,7)}

inverted_color_vals = {v:k for k,v in color_vals.items()}

# Make a graph representation of a simulated network.
def make_graph(media):
    G = nx.Graph()
    ids = {}
    for medium in media.values():
        if medium.logic == False and len(medium.connections) == 2:
            G.add_edge(medium.connections[0].id+1, medium.connections[1].id+1, id=medium.id)
            #print(medium.connections[0].id, medium.connections[1].id)
        else:
            G.add_node(medium.id+1, id=medium.id)
            ids[medium.id+1] = medium.id
            #print(medium.id)
    return G, ids

# Get the correct coloring for each aspect of the graph at a given moment.
def make_colors(media):
    node_colors = []
    edge_colors = {}
    for key in media:
        medium = media[key]
        density = len(medium.in_transit)
        if medium.logic == True:
            density += medium.count_buffers()
        color = color_vals[min(density, 5)]
        if medium.logic == False and len(medium.connections) == 2:
            edge_colors[medium.id] = color
        else:
            node_colors.append(color)
    return node_colors, edge_colors

# Create an animated visualization of what the network is doing
# Visualization makes the most sense for using on smallish networks, obviously, but gives a solid intuition about what's actually going on
# A bit of help from https://stackoverflow.com/questions/50376066/what-tool-to-draw-an-animated-network-graph
def animate_network(media, node_colors_animated, edge_colors_animated, show_labels=False):
    G, ids = make_graph(media)
    pos = nx.spring_layout(G)

    # draw graph
    #nodes = nx.draw_networkx_nodes(G, pos)
    #edges = nx.draw_networkx_edges(G, pos, width=2)
    #labels = nx.draw_networkx_labels(G, pos, labels=ids)
    #plt.axis('off')

    #fig = plt.gcf()
    fig = plt.figure(facecolor='#212121')

    def update(ii):
        fig.clear()
        nodes = nx.draw_networkx_nodes(G, pos, node_color=node_colors_animated[ii])
        edges = nx.draw_networkx_edges(G, pos, width=2, edge_color=[edge_colors_animated[ii][G[u][v]['id']] for u,v in G.edges()])
        if show_labels:
            labels = nx.draw_networkx_labels(G, pos, labels=ids)
            edge_lables = nx.draw_networkx_edge_labels(G, pos, edge_labels={(u,v):G[u][v]['id'] for u,v in G.edges()})
        #labels = nx.draw_networkx_labels(G, pos, labels={i+1:inverted_color_vals[node_colors_animated[ii][i]] for i in range(len(G.nodes))})
        plt.axis('off')
        # nodes are just markers returned by plt.scatter;
        # node color can hence be changed in the same way like marker colors
        #nodes.set_array(node_colors_animated[ii])
        #edges.set_array(edge_colors_animated[ii])
        #return nodes, edges

    animation = FuncAnimation(fig, update, interval=50, frames=len(node_colors_animated)) #, blit=True)
    plt.show()