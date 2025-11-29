# dashboard_integration/data_access.py
"""
Microstep 15:
Dashboard Data Access Layer.
Provides clean functions for Streamlit / UI to read SQL + Graph data.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path

from sql.models import Paper, Summary, Keyword, Cluster
from nosql.graph_placeholder import GraphPlaceholder

# -------------------------
# Initialize DB + Graph
# -------------------------

DB_PATH = Path(__file__).resolve().parents[1] / "sql" / "space_bio.db"
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)

graph = GraphPlaceholder()


# -------------------------
# SQL Access Functions
# -------------------------

def list_papers(limit=50):
    """Return basic info for a list of papers."""
    session = Session()
    rows = session.query(Paper).limit(limit).all()
    session.close()

    return [
        {
            "paper_id": p.external_id,
            "title": p.title,
            "year": p.year,
            "journal": p.journal
        }
        for p in rows
    ]


def get_paper_details(paper_id):
    """Return full paper details including summary + keywords + clusters."""
    session = Session()
    p = session.query(Paper).filter_by(external_id=paper_id).first()

    if not p:
        session.close()
        return None

    data = {
        "paper_id": p.external_id,
        "title": p.title,
        "authors": p.authors,
        "year": p.year,
        "journal": p.journal,
        "doi": p.doi_url,
        "abstract": p.abstract,
        "summary": p.summary.text if p.summary else None,
        "keywords": [k.text for k in p.keywords],
        "clusters": [c.label for c in p.clusters]
    }

    session.close()
    return data


def get_cluster_summaries():
    """Return list of all cluster summaries."""
    session = Session()
    clusters = session.query(Cluster).all()

    data = [
        {
            "cluster_id": c.label,
            "summary": c.summary_text,
            "representative_keyword": c.representative_keyword
        }
        for c in clusters
    ]

    session.close()
    return data


def get_cluster_papers(cluster_id):
    """Return papers belonging to a specific cluster."""
    session = Session()
    c = session.query(Cluster).filter_by(label=str(cluster_id)).first()

    if not c:
        session.close()
        return []

    papers = [
        {
            "paper_id": p.external_id,
            "title": p.title,
            "year": p.year
        }
        for p in c.papers
    ]

    session.close()
    return papers


# -------------------------
# Graph Access Functions
# -------------------------

def get_entities(entity_type=None, limit=20):
    """Proxy to graph placeholder."""
    return graph.get_entities(entity_type, limit)


def get_related_papers_from_graph(entity_id):
    """Proxy to graph placeholder."""
    return graph.get_related_papers(entity_id)
