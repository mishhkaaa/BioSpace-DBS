# dashboard_integration/query_engine.py
"""
Microstep 16:
Unified Query Engine — routes user queries to:
    - SQL
    - Graph (NoSQL)
    - Hybrid (SQL + Graph)
"""

import re
import warnings
from functools import lru_cache
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pathlib import Path

from sql.models import Paper, Summary, Keyword, Cluster
from nosql import GraphClient  # Hot-swappable adapter

# -----------------------------------
# DB + Graph initialization
# -----------------------------------

DB_PATH = Path(__file__).resolve().parents[1] / "sql" / "space_bio.db"
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)

# Initialize graph client (adapter pattern - Neo4j or placeholder based on KG_ADAPTER env var)
try:
    graph = GraphClient()
except Exception as e:
    warnings.warn(f"Failed to initialize graph client: {e}. Graph features will be unavailable.", RuntimeWarning)
    graph = None

# Simple in-memory cache for graph queries (reduces Neo4j Aura calls)
@lru_cache(maxsize=100)
def _cached_get_related_papers(entity_id, limit=20):
    """Cached wrapper for get_related_papers to reduce Neo4j calls."""
    if graph:
        try:
            return tuple(graph.get_related_papers(entity_id, limit))  # tuple for hashability
        except Exception as e:
            warnings.warn(f"Graph query failed: {e}", RuntimeWarning)
            return tuple()
    return tuple()

@lru_cache(maxsize=50)
def _cached_get_entity_by_name(name):
    """Cached wrapper for get_entity_by_name."""
    if graph:
        try:
            return graph.get_entity_by_name(name)
        except Exception as e:
            warnings.warn(f"Graph query failed: {e}", RuntimeWarning)
            return None
    return None

# -----------------------------------
# Query Classification Rules
# -----------------------------------

SQL_KEYWORDS = [
    "year", "keyword", "cluster", "abstract", "title", "papers",
    "summary", "journal", "doi", "after", "before"
]

GRAPH_KEYWORDS = [
    "entity", "relation", "connected", "linked",
    "graph", "node", "edge"
]

HYBRID_HOOKS = [
    "related to", "connected to", "and in cluster",
    "and year", "and keyword"
]


def classify_query(q):
    q_low = q.lower()

    sql_hit = any(kw in q_low for kw in SQL_KEYWORDS)
    graph_hit = any(kw in q_low for kw in GRAPH_KEYWORDS)
    hybrid_hit = any(h in q_low for h in HYBRID_HOOKS)

    if hybrid_hit or (sql_hit and graph_hit):
        return "HYBRID"
    elif graph_hit:
        return "GRAPH"
    else:
        return "SQL"


# -----------------------------------
# SQL Query Executor
# -----------------------------------

def run_sql_query(user_query):
    """
    Minimal natural-language SQL interpreter using heuristic rules.
    """

    session = Session()

    q = user_query.lower()

    # 1. "papers in cluster X"
    if "cluster" in q:
        match = re.search(r"cluster\s+(\d+)", q)
        if match:
            cid = match.group(1)
            cluster = session.query(Cluster).filter_by(label=cid).first()
            if cluster:
                papers = [
                    {
                        "paper_id": p.external_id,
                        "title": p.title,
                        "year": p.year
                    }
                    for p in cluster.papers
                ]
                session.close()
                return {"type": "sql", "papers": papers}

    # 2. "papers after YEAR"
    if "after" in q:
        match = re.search(r"after\s+(\d{4})", q)
        if match:
            year = int(match.group(1))
            rows = session.query(Paper).filter(Paper.year >= year).all()
            session.close()
            return {
                "type": "sql",
                "papers": [
                    {"paper_id": p.external_id, "title": p.title, "year": p.year}
                    for p in rows
                ]
            }

    # 3. keyword search
    if "keyword" in q:
        words = [w for w in q.split() if w not in ["keyword", "keywords"]]
        if words:
            term = words[-1]
            kws = session.query(Keyword).filter(Keyword.text.like(f"%{term}%")).all()
            out = []
            for k in kws:
                out.append({
                    "keyword": k.text,
                    "score": k.score,
                    "papers": [p.external_id for p in k.papers]
                })
            session.close()
            return {"type": "sql", "keywords": out}

    # Default: return all papers
    rows = session.query(Paper).limit(20).all()
    session.close()
    return {
        "type": "sql",
        "papers": [
            {"paper_id": p.external_id, "title": p.title, "year": p.year}
            for p in rows
        ]
    }


# -----------------------------------
# Graph Query Executor
# -----------------------------------

def run_graph_query(user_query):
    """
    Query the knowledge graph (Neo4j or placeholder).
    Returns entities or related papers based on query.
    """
    if not graph:
        return {"type": "graph", "error": "Graph client unavailable", "result": []}

    q = user_query.lower()

    try:
        # "entities" or "show entities"
        if "entity" in q or "entities" in q:
            # Extract entity type if specified
            entity_type = None
            if "gene" in q:
                entity_type = "gene"
            elif "protein" in q:
                entity_type = "protein"
            elif "organism" in q:
                entity_type = "organism"
            elif "condition" in q:
                entity_type = "condition"
            
            entities = graph.get_entities(entity_type=entity_type, limit=50)
            return {"type": "graph", "entities": entities}

        # "related to X" - find entity by name and get papers
        match = re.search(r"related to (\w+)", q)
        if match:
            entity_name = match.group(1)
            entity = _cached_get_entity_by_name(entity_name)
            if entity:
                papers = list(_cached_get_related_papers(entity['entity_id']))
                return {
                    "type": "graph",
                    "entity": entity,
                    "papers": papers
                }
            else:
                return {
                    "type": "graph",
                    "error": f"Entity '{entity_name}' not found",
                    "result": []
                }

        return {"type": "graph", "result": []}
    
    except Exception as e:
        warnings.warn(f"Graph query failed: {e}", RuntimeWarning)
        return {"type": "graph", "error": str(e), "result": []}


# -----------------------------------
# Hybrid Query Executor
# -----------------------------------

def run_hybrid_query(user_query):
    """
    Graph → paper_ids → SQL filtering
    Combines knowledge graph entity relationships with SQL paper database.
    """
    if not graph:
        # Fallback to SQL-only if graph unavailable
        return run_sql_query(user_query)

    try:
        # Step 1: get graph-based papers (entity → related papers)
        match = re.search(r"related to (\w+)", user_query.lower())
        related_papers = []
        entity_info = None
        
        if match:
            entity_name = match.group(1)
            entity = _cached_get_entity_by_name(entity_name)
            if entity:
                entity_info = entity
                related_papers = list(_cached_get_related_papers(entity['entity_id']))

        # Step 2: SQL filter (example: cluster or year)
        sql_results = run_sql_query(user_query)

        # Step 3: intersection of graph papers and SQL results
        combined = []

        if "papers" in sql_results:
            sql_papers = sql_results["papers"]
            if related_papers:
                # Filter SQL papers to only those mentioned in graph
                combined = [p for p in sql_papers if p["paper_id"] in related_papers]
            else:
                combined = sql_papers

        return {
            "type": "hybrid",
            "entity": entity_info,
            "graph_papers": related_papers,
            "sql": sql_results,
            "combined": combined
        }
    
    except Exception as e:
        warnings.warn(f"Hybrid query failed, falling back to SQL: {e}", RuntimeWarning)
        return run_sql_query(user_query)


# -----------------------------------
# MAIN ENTRYPOINT
# -----------------------------------

def run_query(user_query):
    """
    Analyze → classify → call SQL/Graph/Hybrid executor → return unified result.
    """
    qtype = classify_query(user_query)

    if qtype == "SQL":
        return run_sql_query(user_query)
    elif qtype == "GRAPH":
        return run_graph_query(user_query)
    else:
        return run_hybrid_query(user_query)
