# nosql/graph_placeholder.py
"""
Placeholder graph client for testing and demo mode.
Returns empty/demo data without requiring Neo4j connection.

Use this when KG_ADAPTER=placeholder or when Neo4j is unavailable.
"""

import warnings


class GraphPlaceholder:
    """
    Placeholder implementation of graph client interface.
    Returns empty or demo data to allow dashboard operation without Neo4j.
    
    This class matches the Neo4jAdapter interface but doesn't require any configuration.
    Useful for:
    - Local development without Neo4j
    - Testing and CI/CD pipelines
    - Demo mode presentations
    """
    
    def __init__(self):
        """Initialize placeholder (no connection required)."""
        warnings.warn(
            "Using GraphPlaceholder - no real knowledge graph data available. "
            "Set KG_ADAPTER=neo4j in .env to connect to Neo4j Aura.",
            UserWarning
        )
        self._demo_entities = self._generate_demo_entities()
    
    def close(self):
        """Close connection (no-op for placeholder)."""
        pass
    
    def get_entity_by_name(self, name):
        """
        Look up an entity by name (returns demo data).
        
        Args:
            name: Entity name to search for
        
        Returns:
            Demo entity dict or None
        """
        # Return demo entity for common search terms
        name_lower = name.lower()
        for entity in self._demo_entities:
            if entity['name'].lower() == name_lower:
                return entity
        return None
    
    def get_entities(self, entity_type=None, limit=50):
        """
        Returns a list of demo entity dictionaries.
        
        Args:
            entity_type: Filter by entity type (e.g., 'gene', 'protein')
            limit: Maximum number of entities to return
        
        Returns:
            List of demo entity dicts
        """
        entities = self._demo_entities
        
        if entity_type:
            entities = [e for e in entities if e['type'] == entity_type]
        
        return entities[:limit]
    
    def get_related_papers(self, entity_id, limit=20):
        """
        Returns list of demo paper_ids related to this entity.
        
        Args:
            entity_id: The entity ID to find papers for
            limit: Maximum number of papers to return
        
        Returns:
            List of demo paper IDs (empty in placeholder)
        """
        # Return empty list - no paper relationships in placeholder mode
        return []
    
    def get_entity_relations(self, entity_id, relation_type=None):
        """
        Returns demo graph relations.
        
        Args:
            entity_id: The entity ID to find relations for
            relation_type: Filter by relation type
        
        Returns:
            List of demo relation dicts (empty in placeholder)
        """
        # Return empty list - no relations in placeholder mode
        return []
    
    def upsert_paper(self, paper):
        """
        Upsert paper (no-op in placeholder).
        
        Args:
            paper: Paper dict with fields like paper_id, title, etc.
        """
        warnings.warn(
            "upsert_paper called on GraphPlaceholder - operation ignored. "
            "Use KG_ADAPTER=neo4j to persist data.",
            UserWarning
        )
    
    def upsert_entity(self, entity):
        """
        Upsert entity (no-op in placeholder).
        
        Args:
            entity: Entity dict
        """
        warnings.warn(
            "upsert_entity called on GraphPlaceholder - operation ignored. "
            "Use KG_ADAPTER=neo4j to persist data.",
            UserWarning
        )
    
    def create_relation(self, src_id, dst_id, rel_type, properties=None):
        """
        Create relation (no-op in placeholder).
        
        Args:
            src_id: Source entity ID
            dst_id: Target entity ID
            rel_type: Relation type
            properties: Optional relation properties
        """
        warnings.warn(
            "create_relation called on GraphPlaceholder - operation ignored. "
            "Use KG_ADAPTER=neo4j to persist data.",
            UserWarning
        )
    
    def _generate_demo_entities(self):
        """Generate demo entities from cluster keywords for fallback display."""
        # Demo entities based on common space biology topics
        return [
            {
                'entity_id': 'DEMO_001',
                'name': 'spaceflight',
                'type': 'condition',
                'importance_score': 100.0,
                'paper_count': 20,
                'relation_count': 45
            },
            {
                'entity_id': 'DEMO_002',
                'name': 'microgravity',
                'type': 'condition',
                'importance_score': 95.0,
                'paper_count': 18,
                'relation_count': 40
            },
            {
                'entity_id': 'DEMO_003',
                'name': 'radiation',
                'type': 'condition',
                'importance_score': 90.0,
                'paper_count': 15,
                'relation_count': 35
            },
            {
                'entity_id': 'DEMO_004',
                'name': 'mouse',
                'type': 'organism',
                'importance_score': 85.0,
                'paper_count': 25,
                'relation_count': 50
            },
            {
                'entity_id': 'DEMO_005',
                'name': 'bone',
                'type': 'tissue',
                'importance_score': 80.0,
                'paper_count': 12,
                'relation_count': 30
            },
            {
                'entity_id': 'DEMO_006',
                'name': 'cell',
                'type': 'cell_type',
                'importance_score': 75.0,
                'paper_count': 22,
                'relation_count': 48
            },
            {
                'entity_id': 'DEMO_007',
                'name': 'gene expression',
                'type': 'process',
                'importance_score': 70.0,
                'paper_count': 16,
                'relation_count': 38
            },
            {
                'entity_id': 'DEMO_008',
                'name': 'immune system',
                'type': 'tissue',
                'importance_score': 65.0,
                'paper_count': 14,
                'relation_count': 32
            }
        ]
