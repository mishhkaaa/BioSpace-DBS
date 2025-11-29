# nosql/graph_placeholder.py
"""
Microstep 14:
Graph database placeholder.
These functions return empty results so the dashboard can run
even without Member 1's actual graph implementation.
"""

class GraphPlaceholder:
    def __init__(self):
        pass

    def get_entities(self, entity_type=None, limit=50):
        """
        Returns a list of entity dictionaries.
        For now returns empty list.
        """
        return []

    def get_related_papers(self, entity_id, limit=20):
        """
        Returns list of paper_ids related to this entity.
        Placeholder: empty list.
        """
        return []

    def get_entity_relations(self, entity_id, relation_type=None):
        """
        Returns graph edges / relation triples.
        Placeholder: empty list.
        """
        return []
