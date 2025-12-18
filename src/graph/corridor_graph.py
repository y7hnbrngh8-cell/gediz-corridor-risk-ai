from __future__ import annotations
import networkx as nx

NODES = ["Camargue", "Kerkini", "Tuna", "Gediz", "Tuz", "EastMed"]

EDGES = [
    ("Camargue", "Kerkini", {"species": "Flamingo"}),
    ("Kerkini", "Gediz", {"species": "Flamingo"}),
    ("Gediz", "Tuz", {"species": "Flamingo"}),

    ("Tuna", "Kerkini", {"species": "Pelican"}),
    ("Kerkini", "Gediz", {"species": "Pelican"}),
    ("Gediz", "EastMed", {"species": "Pelican"}),
]

def build_corridor_graph() -> nx.DiGraph:
    G = nx.DiGraph()
    G.add_nodes_from(NODES)
    for u, v, attrs in EDGES:
        G.add_edge(u, v, **attrs)
    return G

def subgraph_for_species(G: nx.DiGraph, species: str) -> nx.DiGraph:
    H = nx.DiGraph()
    H.add_nodes_from(G.nodes(data=True))
    for u, v, d in G.edges(data=True):
        if d.get("species") == species:
            H.add_edge(u, v, **d)
    return H

def bottleneck_scores(G: nx.DiGraph) -> dict[str, float]:
    return nx.betweenness_centrality(G)
