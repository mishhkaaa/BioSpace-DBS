# dashboard_integration/query_engine.py
"""
Microstep 16:
Unified Query Engine — routes user queries to:
    - SQL
    - Graph (NoSQL)
    - Hybrid (SQL + Graph)
"""

import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pathlib import Path

from sql.models import Paper, Summary, Keyword, Cluster
from nosql.graph_placeholder import GraphPlaceholder

# -----------------------------------
# DB + Graph initialization
# -----------------------------------

DB_PATH = Path(__file__).resolve().parents[1] / "sql" / "space_bio.db"
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)

graph = GraphPlaceholder()

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
    Simple placeholder-based graph fetch.
    """

    q = user_query.lower()

    # "entities"
    if "entity" in q or "entities" in q:
        return {"type": "graph", "entities": graph.get_entities()}

    # "related to X"
    match = re.search(r"related to (\w+)", q)
    if match:
        ent = match.group(1)
        papers = graph.get_related_papers(ent)
        return {"type": "graph", "papers": papers}

    return {"type": "graph", "result": []}


# -----------------------------------
# Hybrid Query Executor
# -----------------------------------

def run_hybrid_query(user_query):
    """
    Graph → paper_ids → SQL filtering
    """

    # Step 1: get graph-based papers
    match = re.search(r"related to (\w+)", user_query.lower())
    related_papers = []
    if match:
        ent = match.group(1)
        related_papers = graph.get_related_papers(ent)   # returns paper_ids

    # Step 2: SQL filter (example: cluster or year)
    sql_results = run_sql_query(user_query)

    # Step 3: intersection
    combined = []

    if "papers" in sql_results:
        sql_papers = sql_results["papers"]
        if related_papers:
            combined = [p for p in sql_papers if p["paper_id"] in related_papers]
        else:
            combined = sql_papers

    return {
        "type": "hybrid",
        "graph_papers": related_papers,
        "sql": sql_results,
        "combined": combined
    }


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
