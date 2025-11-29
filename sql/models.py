# sql/models.py
"""
Microstep 10:
SQLAlchemy ORM models for Space Bio DB.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, ForeignKey, Table
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# ------------------------
# Association Tables
# ------------------------

paper_keyword = Table(
    "paper_keyword",
    Base.metadata,
    Column("paper_id", Integer, ForeignKey("papers.id"), primary_key=True),
    Column("keyword_id", Integer, ForeignKey("keywords.id"), primary_key=True)
)

paper_cluster = Table(
    "paper_cluster",
    Base.metadata,
    Column("paper_id", Integer, ForeignKey("papers.id"), primary_key=True),
    Column("cluster_id", Integer, ForeignKey("clusters.id"), primary_key=True)
)

# ------------------------
# Main Tables
# ------------------------

class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String, index=True, unique=True)   # paper_id from CSV
    title = Column(String)
    authors = Column(String)
    year = Column(Integer)
    journal = Column(String)
    doi_url = Column(String)
    abstract = Column(Text)

    summary = relationship("Summary", uselist=False, back_populates="paper")
    keywords = relationship("Keyword", secondary=paper_keyword, back_populates="papers")
    clusters = relationship("Cluster", secondary=paper_cluster, back_populates="papers")


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text)
    method = Column(String)

    paper_id = Column(Integer, ForeignKey("papers.id"), unique=True)
    paper = relationship("Paper", back_populates="summary")


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(String)
    score = Column(Float)

    papers = relationship("Paper", secondary=paper_keyword, back_populates="keywords")


class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String)  # cluster_id number → string
    summary_text = Column(Text)
    representative_keyword = Column(String)

    papers = relationship("Paper", secondary=paper_cluster, back_populates="clusters")
