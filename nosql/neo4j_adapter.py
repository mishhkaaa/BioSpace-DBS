# nosql/neo4j_adapter.py
"""
Neo4j adapter for knowledge graph access.
Provides programmatic access to the Neo4j knowledge graph for dashboard integration.
"""

from neo4j import GraphDatabase
import os
import sys

# Add parent directory to path for config import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.neo4j_config import get_neo4j_config


class Neo4jAdapter:
    """
    Neo4j adapter for knowledge graph access.
    Connects to Neo4j Aura instance and provides query methods for entities, papers, and relations.
    
    Required environment variables:
        NEO4J_URI: Neo4j connection URI (e.g., neo4j+s://xxxxx.databases.neo4j.io)
        NEO4J_USER: Neo4j username (typically 'neo4j')
        NEO4J_PASSWORD: Neo4j password
    """
    
    def __init__(self):
        """Initialize Neo4j connection. Raises ValueError if credentials are missing."""
        config = get_neo4j_config()
        
        # Validate required credentials
        if not config.get('uri'):
            raise ValueError(
                "NEO4J_URI environment variable is required. "
                "Please set it in your .env file."
            )
        if not config.get('password'):
            raise ValueError(
                "NEO4J_PASSWORD environment variable is required. "
                "Please set it in your .env file."
            )
        
        self.uri = config['uri']
        self.user = config['user']
        self.password = config['password']
        
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Verify connection
            self.driver.verify_connectivity()
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Neo4j at {self.uri}. "
                f"Error: {str(e)}. "
                f"Please check your NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD."
            )
    
    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
    
    def get_entity_by_name(self, name):
        """
        Look up an entity by name.
        
        Args:
            name: Entity name to search for (case-insensitive)
        
        Returns:
            Entity dict or None if not found
        """
        with self.driver.session() as session:
            query = """
            MATCH (e:Entity)
            WHERE toLower(e.name) = toLower($name)
            RETURN e.entity_id AS entity_id,
                   e.name AS name,
                   e.type AS type,
                   e.importance_score AS importance_score,
                   size(e.papers) AS paper_count,
                   e.relation_count AS relation_count
            LIMIT 1
            """
            result = session.run(query, name=name)
            record = result.single()
            
            if record:
                return {
                    'entity_id': record['entity_id'],
                    'name': record['name'],
                    'type': record['type'],
                    'importance_score': record['importance_score'],
                    'paper_count': record['paper_count'],
                    'relation_count': record['relation_count']
                }
            return None
    
    def get_entities(self, entity_type=None, limit=50):
        """
        Returns a list of entity dictionaries from Neo4j.
        
        Args:
            entity_type: Filter by entity type (e.g., 'gene', 'protein'). None = all types.
            limit: Maximum number of entities to return (default: 50)
        
        Returns:
            List of dicts with keys: entity_id, name, type, importance_score, paper_count, relation_count
        """
        with self.driver.session() as session:
            if entity_type:
                query = """
                MATCH (e:Entity)
                WHERE e.type = $entity_type
                RETURN e.entity_id AS entity_id, 
                       e.name AS name, 
                       e.type AS type,
                       e.importance_score AS importance_score,
                       size(e.papers) AS paper_count,
                       e.relation_count AS relation_count
                ORDER BY e.importance_score DESC
                LIMIT $limit
                """
                result = session.run(query, entity_type=entity_type, limit=limit)
            else:
                query = """
                MATCH (e:Entity)
                RETURN e.entity_id AS entity_id, 
                       e.name AS name, 
                       e.type AS type,
                       e.importance_score AS importance_score,
                       size(e.papers) AS paper_count,
                       e.relation_count AS relation_count
                ORDER BY e.importance_score DESC
                LIMIT $limit
                """
                result = session.run(query, limit=limit)
            
            entities = []
            for record in result:
                entities.append({
                    'entity_id': record['entity_id'],
                    'name': record['name'],
                    'type': record['type'],
                    'importance_score': record['importance_score'],
                    'paper_count': record['paper_count'],
                    'relation_count': record['relation_count']
                })
            
            return entities

    def get_related_papers(self, entity_id, limit=20):
        """
        Returns list of paper_ids related to this entity.
        
        Args:
            entity_id: The entity ID to find papers for
            limit: Maximum number of papers to return (default: 20)
        
        Returns:
            List of paper IDs (strings) where this entity appears
        """
        with self.driver.session() as session:
            query = """
            MATCH (e:Entity {entity_id: $entity_id})
            RETURN e.papers AS papers
            """
            result = session.run(query, entity_id=entity_id)
            record = result.single()
            
            if record and record['papers']:
                papers_list = list(record['papers'])
                return papers_list[:limit]
            return []

    def get_entity_relations(self, entity_id, relation_type=None):
        """
        Returns graph edges / relation triples involving this entity.
        
        Args:
            entity_id: The entity ID to find relations for
            relation_type: Filter by relation type (e.g., 'increases', 'affects'). None = all types.
        
        Returns:
            List of dicts with keys: source, relation, target, evidence_count, confidence, papers
        """
        with self.driver.session() as session:
            if relation_type:
                # Get relations where entity is source OR target, filtered by type
                # Neo4j relationship type names are uppercase, so convert for matching
                neo4j_rel_type = relation_type.upper()
                query = """
                MATCH (source:Entity)-[r]->(target:Entity)
                WHERE (source.entity_id = $entity_id OR target.entity_id = $entity_id)
                  AND type(r) = $relation_type
                RETURN source.name AS source_name,
                       source.entity_id AS source_id,
                       r.relation_type AS relation_type,
                       target.name AS target_name,
                       target.entity_id AS target_id,
                       r.evidence_count AS evidence_count,
                       r.confidence AS confidence,
                       r.papers AS papers
                """
                result = session.run(query, entity_id=entity_id, relation_type=neo4j_rel_type)
            else:
                # Get all relations where entity is source OR target
                query = """
                MATCH (source:Entity)-[r]->(target:Entity)
                WHERE source.entity_id = $entity_id OR target.entity_id = $entity_id
                RETURN source.name AS source_name,
                       source.entity_id AS source_id,
                       r.relation_type AS relation_type,
                       target.name AS target_name,
                       target.entity_id AS target_id,
                       r.evidence_count AS evidence_count,
                       r.confidence AS confidence,
                       r.papers AS papers
                """
                result = session.run(query, entity_id=entity_id)
            
            relations = []
            for record in result:
                relations.append({
                    'source': record['source_name'],
                    'source_id': record['source_id'],
                    'relation': record['relation_type'],
                    'target': record['target_name'],
                    'target_id': record['target_id'],
                    'evidence_count': record['evidence_count'],
                    'confidence': record['confidence'],
                    'papers': list(record['papers']) if record['papers'] else []
                })
            
            return relations
