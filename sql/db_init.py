# sql/db_init.py
"""
Microstep 11:
Create SQLite database and load all AI outputs into SQL tables.
"""

import sys
from pathlib import Path

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sql.models import Base, Paper, Summary, Cluster, Keyword

# Paths
ROOT = Path(__file__).resolve().parents[1]   # dbs/
DATA_DIR = ROOT / "data"
OUTPUTS = DATA_DIR / "outputs"

# Input files
PAPERS_CSV = DATA_DIR / "papers_clean.csv"
SUMMARIES_CSV = OUTPUTS / "summaries.csv"
CLUSTERS_CSV = OUTPUTS / "clusters.csv"
KEYWORDS_CSV = OUTPUTS / "cluster_keywords.csv"
CLUSTER_SUMMARIES_CSV = OUTPUTS / "cluster_summaries.csv"

# DB file path
DB_PATH = ROOT / "sql" / "space_bio.db"


def load_papers(session):
    df = pd.read_csv(PAPERS_CSV)

    for _, row in df.iterrows():
        # Check if paper already exists
        existing = session.query(Paper).filter_by(external_id=row["paper_id"]).first()
        if existing:
            continue
            
        p = Paper(
            external_id=row["paper_id"],
            title=row.get("title"),
            authors=row.get("authors"),
            year=row.get("year"),
            journal=row.get("journal"),
            doi_url=row.get("doi_url"),
            abstract=row.get("abstract")
        )
        session.add(p)
    session.commit()


def load_summaries(session):
    df = pd.read_csv(SUMMARIES_CSV)

    for _, row in df.iterrows():
        paper = session.query(Paper).filter_by(external_id=row["paper_id"]).first()
        if not paper:
            continue

        s = Summary(
            text=row["summary"],
            method=row["summary_model"],
            paper=paper
        )
        session.add(s)
    session.commit()


def load_clusters(session):
    df_clusters = pd.read_csv(CLUSTERS_CSV)
    df_cluster_summaries = pd.read_csv(CLUSTER_SUMMARIES_CSV)

    # Create Cluster rows
    for _, row in df_cluster_summaries.iterrows():
        c = Cluster(
            label=str(row["cluster_id"]),
            summary_text=row["cluster_summary"],
            representative_keyword=None
        )
        session.add(c)
    session.commit()

    # Link papers to clusters
    for _, row in df_clusters.iterrows():
        paper = session.query(Paper).filter_by(external_id=row["paper_id"]).first()
        cluster = session.query(Cluster).filter_by(label=str(row["cluster_id"])).first()

        if paper and cluster:
            # Check if relationship already exists
            if cluster not in paper.clusters:
                paper.clusters.append(cluster)

    session.commit()


def load_keywords(session):
    df = pd.read_csv(KEYWORDS_CSV)

    for _, row in df.iterrows():
        # create keyword
        k = Keyword(
            text=row["keyword"],
            score=row["score"]
        )
        session.add(k)
        session.commit()

        # link to paper
        paper = session.query(Paper).filter_by(external_id=row["paper_id"]).first()
        if paper:
            paper.keywords.append(k)

    session.commit()


def main():
    print("Creating SQLite database...")
    
    # Delete existing database if it exists
    if DB_PATH.exists():
        print(f"Removing existing database: {DB_PATH}")
        DB_PATH.unlink()

    engine = create_engine(f"sqlite:///{DB_PATH}")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    print("Loading papers...")
    load_papers(session)

    print("Loading summaries...")
    load_summaries(session)

    print("Loading clusters...")
    load_clusters(session)

    print("Loading keywords...")
    load_keywords(session)

    print("\nDatabase created successfully at:")
    print(DB_PATH)


if __name__ == "__main__":
    main()
