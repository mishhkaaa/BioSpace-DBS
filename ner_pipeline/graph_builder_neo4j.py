"""
Neo4j Graph Database Builder

Imports filtered entities and relations into Neo4j graph database.
Creates Entity nodes and RELATION edges with full metadata.

Prerequisites:
- Neo4j installed and running (or Neo4j Aura cloud instance)
- neo4j Python driver installed (pip install neo4j)
- Config updated in config/neo4j_config.py
"""

import json
from pathlib import Path
from neo4j import GraphDatabase
from tqdm import tqdm
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.config import ROOT
from config.neo4j_config import get_neo4j_config

# Paths
GRAPH_DATA_DIR = ROOT / "graph_data"


class Neo4jGraphBuilder:
    """Handles Neo4j graph construction."""
    
    def __init__(self):
        """Initialize Neo4j connection using config."""
        config = get_neo4j_config()
        uri = config['uri']
        user = config['user']
        password = config['password']
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            print(f"✓ Connected to Neo4j at {uri}")
        except Exception as e:
            print(f"❌ Failed to connect to Neo4j: {e}")
            print(f"\nPlease ensure:")
            print(f"  1. Neo4j is running (or Aura instance is active)")
            print(f"  2. URI is correct: {uri}")
            print(f"  3. Username/password are correct")
            print(f"  4. Update config/neo4j_config.py if needed")
            raise
    
    def close(self):
        """Close Neo4j connection."""
        self.driver.close()
    
    def clear_database(self):
        """Clear all nodes and relationships from database."""
        print("\n🗑️  Clearing existing graph data...")
        with self.driver.session() as session:
            # Delete all relationships first
            session.run("MATCH ()-[r]->() DELETE r")
            # Then delete all nodes
            session.run("MATCH (n) DELETE n")
        print("✓ Database cleared")
    
    def create_constraints(self):
        """Create uniqueness constraints and indexes."""
        print("\n📋 Creating constraints and indexes...")
        
        with self.driver.session() as session:
            # Constraint on entity_id (ensures uniqueness)
            try:
                session.run(
                    "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS "
                    "FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE"
                )
                print("✓ Created uniqueness constraint on Entity.entity_id")
            except Exception as e:
                print(f"  Note: Constraint may already exist ({e})")
            
            # Indexes for better query performance
            indexes = [
                ("Entity", "name"),
                ("Entity", "type"),
                ("Entity", "importance_score")
            ]
            
            for label, property in indexes:
                try:
                    session.run(
                        f"CREATE INDEX {label.lower()}_{property}_index IF NOT EXISTS "
                        f"FOR (n:{label}) ON (n.{property})"
                    )
                    print(f"✓ Created index on {label}.{property}")
                except Exception as e:
                    print(f"  Note: Index may already exist ({e})")
    
    def create_entities(self, entities):
        """
        Create Entity nodes in Neo4j.
        
        Args:
            entities: List of entity dictionaries
        """
        print(f"\n📊 Creating {len(entities)} entity nodes...")
        
        with self.driver.session() as session:
            for entity in tqdm(entities, desc="Creating entities"):
                session.run(
                    """
                    CREATE (e:Entity {
                        entity_id: $entity_id,
                        name: $name,
                        type: $type,
                        papers: $papers,
                        paper_count: $paper_count,
                        importance_score: $importance_score,
                        relation_count: $relation_count,
                        synonyms: $synonyms
                    })
                    """,
                    entity_id=entity['entity_id'],
                    name=entity['name'],
                    type=entity['type'],
                    papers=entity['papers'],
                    paper_count=len(entity['papers']),
                    importance_score=entity.get('importance_score', 0),
                    relation_count=entity.get('relation_count', 0),
                    synonyms=entity.get('synonyms', [])
                )
        
        print(f"✓ Created {len(entities)} entities")
    
    def create_relations(self, relations):
        """
        Create relationship edges in Neo4j.
        
        Args:
            relations: List of relation dictionaries
        """
        print(f"\n🔗 Creating {len(relations)} relationships...")
        
        # Group relations by type for better performance
        relations_by_type = {}
        for rel in relations:
            rel_type = rel['relation'].upper()
            if rel_type not in relations_by_type:
                relations_by_type[rel_type] = []
            relations_by_type[rel_type].append(rel)
        
        with self.driver.session() as session:
            for rel_type, rels in tqdm(relations_by_type.items(), desc="Creating relations"):
                # Batch create relationships of same type
                for rel in rels:
                    # Neo4j relationship types must be uppercase and valid identifiers
                    # Replace any invalid characters
                    safe_rel_type = rel_type.replace('-', '_').replace(' ', '_')
                    
                    session.run(
                        f"""
                        MATCH (source:Entity {{entity_id: $source_id}})
                        MATCH (target:Entity {{entity_id: $target_id}})
                        CREATE (source)-[r:{safe_rel_type} {{
                            relation_id: $relation_id,
                            relation_type: $relation_type,
                            papers: $papers,
                            evidence_count: $evidence_count,
                            confidence: $confidence
                        }}]->(target)
                        """,
                        source_id=rel['source'],
                        target_id=rel['target'],
                        relation_id=rel['relation_id'],
                        relation_type=rel['relation'],
                        papers=rel['papers'],
                        evidence_count=rel['evidence_count'],
                        confidence=rel.get('confidence', 0.5)
                    )
        
        print(f"✓ Created {len(relations)} relationships")
    
    def verify_import(self):
        """Verify the import was successful."""
        print("\n✅ Verifying import...")
        
        with self.driver.session() as session:
            # Count nodes
            result = session.run("MATCH (e:Entity) RETURN count(e) as count")
            node_count = result.single()['count']
            print(f"  Entities in database: {node_count}")
            
            # Count relationships
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()['count']
            print(f"  Relations in database: {rel_count}")
            
            # Sample top entities
            result = session.run(
                """
                MATCH (e:Entity)
                RETURN e.name as name, e.type as type, e.importance_score as score
                ORDER BY e.importance_score DESC
                LIMIT 5
                """
            )
            
            print(f"\n  Top 5 entities by importance:")
            for i, record in enumerate(result, 1):
                print(f"    {i}. {record['name']} ({record['type']}) - Score: {record['score']:.1f}")
    
    def print_sample_queries(self):
        """Print sample Cypher queries for exploration."""
        print("\n" + "="*70)
        print("SAMPLE NEO4J CYPHER QUERIES")
        print("="*70)
        
        queries = [
            ("Find all entities of a specific type", 
             "MATCH (e:Entity {type: 'condition'}) RETURN e.name, e.paper_count LIMIT 10"),
            
            ("Find relations from microgravity",
             "MATCH (e:Entity {name: 'microgravity'})-[r]->(target) RETURN type(r), target.name LIMIT 20"),
            
            ("Find shortest path between two entities",
             "MATCH path = shortestPath((a:Entity {name: 'microgravity'})-[*]-(b:Entity {name: 'bone loss'})) RETURN path"),
            
            ("Find most connected entities",
             "MATCH (e:Entity)-[r]-() RETURN e.name, e.type, count(r) as connections ORDER BY connections DESC LIMIT 10"),
            
            ("Find entities related to spaceflight",
             "MATCH (s:Entity {name: 'spaceflight'})-[r]->(e) RETURN e.name, e.type, type(r) as relation LIMIT 20"),
            
            ("Find all papers mentioning an entity",
             "MATCH (e:Entity {name: 'mouse'}) RETURN e.papers"),
            
            ("Find common targets of two entities",
             "MATCH (a:Entity {name: 'microgravity'})-[]->(common)<-[]-(b:Entity {name: 'radiation'}) RETURN common.name"),
            
            ("Find entities by importance score",
             "MATCH (e:Entity) WHERE e.importance_score >= 100 RETURN e.name, e.type, e.importance_score ORDER BY e.importance_score DESC")
        ]
        
        for i, (description, query) in enumerate(queries, 1):
            print(f"\n{i}. {description}:")
            print(f"   {query}")


def build_neo4j_graph(clear_existing=True):
    """
    Main function to build Neo4j graph from filtered data.
    
    Args:
        clear_existing: Whether to clear existing data first
    """
    print("🚀 Starting Neo4j Graph Construction")
    print(f"📁 Reading from: {GRAPH_DATA_DIR}")
    
    # Load filtered data
    entities_path = GRAPH_DATA_DIR / "filtered_entities.json"
    relations_path = GRAPH_DATA_DIR / "filtered_relations.json"
    
    with open(entities_path, 'r', encoding='utf-8') as f:
        entities = json.load(f)
    
    with open(relations_path, 'r', encoding='utf-8') as f:
        relations = json.load(f)
    
    print(f"✓ Loaded {len(entities)} entities")
    print(f"✓ Loaded {len(relations)} relations")
    
    # Build graph using config
    builder = Neo4jGraphBuilder()
    
    try:
        if clear_existing:
            builder.clear_database()
        
        builder.create_constraints()
        builder.create_entities(entities)
        builder.create_relations(relations)
        builder.verify_import()
        builder.print_sample_queries()
        
        config = get_neo4j_config()
        print("\n" + "="*70)
        print("✅ NEO4J GRAPH CONSTRUCTION COMPLETE")
        config = get_neo4j_config()
        print("\n" + "="*70)
        print("✅ NEO4J GRAPH CONSTRUCTION COMPLETE")
        print("="*70)
        
        if 'localhost' in config['uri'] or '127.0.0.1' in config['uri']:
            print(f"\n🌐 Access Neo4j Browser at: http://localhost:7474")
        else:
            print(f"\n🌐 Access Neo4j Browser at: https://console.neo4j.io/")
        
        print(f"   URI: {config['uri']}")
        print(f"   Username: {config['user']}")
        print(f"\n📊 Graph contains:")
        print(f"   - {len(entities)} entity nodes")
        print(f"   - {len(relations)} relationship edges")
        
    finally:
        builder.close()


if __name__ == "__main__":
    import sys
    from config.neo4j_config import get_neo4j_config
    
    config = get_neo4j_config()
    
    print(f"\n📍 Target URI: {config['uri']}")
    
    try:
        build_neo4j_graph()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"\nTroubleshooting:")
        print(f"  1. Check Neo4j is running: http://localhost:7474")
        print(f"  2. Verify password is correct")
        print(f"  3. Ensure neo4j driver is installed: pip install neo4j")
        sys.exit(1)
