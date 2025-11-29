# sql/test_db.py
"""
Microstep 12:
Quick sanity checks for the SQL database.
"""

import sys
from pathlib import Path

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sql.models import Paper, Summary, Keyword, Cluster

DB_PATH = Path(__file__).resolve().parent / "space_bio.db"

def main():
    print("Connecting to DB:", DB_PATH)

    engine = create_engine(f"sqlite:///{DB_PATH}")
    Session = sessionmaker(bind=engine)
    session = Session()

    # 1. Count papers
    paper_count = session.query(Paper).count()
    print(f"Total papers in DB: {paper_count}")

    # 2. Count summaries
    summary_count = session.query(Summary).count()
    print(f"Total summaries: {summary_count}")

    # 3. Count clusters
    cluster_count = session.query(Cluster).count()
    print(f"Total clusters: {cluster_count}")

    # 4. Count keywords
    keyword_count = session.query(Keyword).count()
    print(f"Total keywords: {keyword_count}")

    # 5. Print 3 papers with their clusters
    print("\nSample papers with clusters:")
    papers = session.query(Paper).limit(3).all()
    for p in papers:
        print(f"- {p.external_id}: {[c.label for c in p.clusters]}")

    # 6. Print top 5 keywords
    print("\nTop 5 keywords:")
    kws = session.query(Keyword).limit(5).all()
    for k in kws:
        print(f"- {k.text} (score={k.score})")

if __name__ == "__main__":
    main()
