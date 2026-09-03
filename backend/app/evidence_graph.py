"""
EVIDENCE GRAPH — built with NetworkX (no LLM calls)

Every insight in BoardMind must be traceable to the data that supports it.
We model this literally as a directed graph: data sources -> the KPI they
feed -> the material events they help explain. The graph is the actual
data structure the API returns to the frontend (rendered with React Flow),
not a decorative diagram.
"""
import random
import networkx as nx
from .data_gen import get_data

SOURCE_META = {
    "sales":      {"name": "Sales Ledger",       "cadence_mins": 1440},
    "inventory":  {"name": "Inventory Feed",      "cadence_mins": 60},
    "marketing":  {"name": "Marketing Campaigns", "cadence_mins": 10080},
    "reviews":    {"name": "Customer Reviews",    "cadence_mins": 180},
    "competitor": {"name": "Competitor Pricing",  "cadence_mins": 1440},
    "weather":    {"name": "Weather Feed",        "cadence_mins": 1440},
    "news":       {"name": "News & Events",       "cadence_mins": 720},
}


def build_source_freshness() -> list[dict]:
    data = get_data()
    rng = random.Random(7)
    out = []
    for sid, meta in SOURCE_META.items():
        freshness = rng.randint(2, max(3, int(meta["cadence_mins"] * 0.6)))
        label = f"{freshness}m ago" if freshness < 60 else f"{freshness // 60}h ago" if freshness < 1440 else f"{freshness // 1440}d ago"
        out.append({
            "id": sid, "name": meta["name"], "cadenceMins": meta["cadence_mins"],
            "count": int(len(data[sid])), "freshnessMins": freshness, "freshnessLabel": label,
            "lineage": f"{sid}_v{rng.randint(3,9)} -> harmonizer -> semantic_kpi_layer",
        })
    return out


def build_graph(events: list[dict]) -> nx.DiGraph:
    """Constructs the literal traceability graph: source -> kpi -> event."""
    g = nx.DiGraph()
    for sid, meta in SOURCE_META.items():
        g.add_node(f"source:{sid}", kind="source", label=meta["name"])
    kpi_ids = {"revenue", "marketing", "inventory", "new_product"}
    for k in kpi_ids:
        g.add_node(f"kpi:{k}", kind="kpi", label=k.replace("_", " ").title())
    for e in events:
        g.add_node(f"event:{e['id']}", kind="event", label=e["title"], severity=e["severity"])
        g.add_edge(f"kpi:{e['kpi']}", f"event:{e['id']}", relation="explains")
        for s in e["sources"]:
            g.add_edge(f"source:{s}", f"kpi:{e['kpi']}", relation="feeds")
    return g


def graph_to_reactflow(g: nx.DiGraph) -> dict:
    """Serializes the NetworkX graph into React Flow's {nodes, edges} shape,
    with a simple layered layout computed from graph topology (topological
    generations), not a hand-placed layout."""
    nodes, edges = [], []
    try:
        generations = list(nx.topological_generations(g))
    except nx.NetworkXUnfeasible:
        generations = [list(g.nodes())]

    for col, gen in enumerate(generations):
        for row, node_id in enumerate(gen):
            attrs = g.nodes[node_id]
            nodes.append({
                "id": node_id, "position": {"x": col * 260, "y": row * 110},
                "data": {"label": attrs.get("label", node_id), "kind": attrs.get("kind"), "severity": attrs.get("severity")},
            })
    for u, v, attrs in g.edges(data=True):
        edges.append({"id": f"{u}->{v}", "source": u, "target": v, "label": attrs.get("relation", "")})
    return {"nodes": nodes, "edges": edges}
