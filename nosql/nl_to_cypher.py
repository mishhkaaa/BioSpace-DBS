# nosql/nl_to_cypher.py
"""
Natural Language to Cypher Query Converter
Converts English questions to Cypher queries for Neo4j
"""
import re
from typing import Dict, List, Tuple, Optional


class NLToCypherConverter:
    """Converts natural language queries to Cypher"""
    
    def __init__(self):
        # Common query patterns: (regex, cypher_template, description)
        self.patterns = [
            # "What affects X?"
            (r"what (?:affects|impacts|influences) (.+)",
             "MATCH (n:Entity)-[r:AFFECTS|INCREASES|DECREASES|INDUCES]->(m:Entity) WHERE toLower(m.name) = toLower($entity) RETURN n.name as source, r.relation_type as relation, m.name as target, r.evidence_count as evidence, r.confidence as confidence ORDER BY r.evidence_count DESC LIMIT 20",
             "Finding what affects {entity}"),
            
            # "What is affected by X?"
            (r"what (?:is )?affected by (.+)",
             "MATCH (n:Entity)-[r:AFFECTS|INCREASES|DECREASES|INDUCES]->(m:Entity) WHERE toLower(n.name) = toLower($entity) RETURN n.name as source, r.relation_type as relation, m.name as target, r.evidence_count as evidence, r.confidence as confidence ORDER BY r.evidence_count DESC LIMIT 20",
             "Finding what is affected by {entity}"),
            
            # "What causes X?"
            (r"what causes (.+)",
             "MATCH (n:Entity)-[r]->(m:Entity) WHERE toLower(m.name) = toLower($entity) AND (r.relation_type = 'causes' OR r.relation_type = 'induces') RETURN n.name as source, r.relation_type as relation, m.name as target, r.evidence_count as evidence, r.confidence as confidence ORDER BY r.evidence_count DESC LIMIT 20",
             "Finding what causes {entity}"),
            
            # "What increases/decreases X?"
            (r"what (increases|decreases) (.+)",
             "MATCH (n:Entity)-[r]->(m:Entity) WHERE toLower(m.name) = toLower($entity) AND r.relation_type = $relation RETURN n.name as source, r.relation_type as relation, m.name as target, r.evidence_count as evidence, r.confidence as confidence ORDER BY r.evidence_count DESC LIMIT 20",
             "Finding what {relation} {entity}"),
            
            # "Show relationships for X"
            (r"(?:show|find|get) (?:relationships|relations|connections) (?:for|of) (.+)",
             "MATCH (n:Entity)-[r]-(m:Entity) WHERE toLower(n.name) = toLower($entity) RETURN n.name as entity1, r.relation_type as relation, m.name as entity2, r.evidence_count as evidence, r.confidence as confidence ORDER BY r.evidence_count DESC LIMIT 30",
             "Finding all relationships for {entity}"),
            
            # "Find genes related to X"
            (r"(?:find|show|get) (gene|protein|tissue|condition|organism|chemical|disease)s? (?:related to|associated with) (.+)",
             "MATCH (n:Entity)-[r]-(m:Entity) WHERE toLower(m.name) = toLower($entity) AND n.type = $type RETURN n.name as name, n.type as type, r.relation_type as relation, m.name as related_to, r.evidence_count as evidence ORDER BY r.evidence_count DESC LIMIT 20",
             "Finding {type} related to {entity}"),
            
            # "What are the top entities?"
            (r"(?:what are |show |find )?(?:the )?top (\d+)? ?entities",
             "MATCH (e:Entity) RETURN e.name as name, e.type as type, e.importance_score as score, size(e.papers) as papers ORDER BY e.importance_score DESC LIMIT $limit",
             "Finding top {limit} entities"),
            
            # "Show all genes/proteins/conditions"
            (r"(?:show|find|get|list) (?:all )?(gene|protein|tissue|condition|organism|chemical|disease|cell_type|assay)s?$",
             "MATCH (e:Entity) WHERE e.type = $type RETURN e.name as name, e.type as type, e.importance_score as score, size(e.papers) as papers ORDER BY e.importance_score DESC LIMIT 30",
             "Finding all {type} entities"),
            
            # "Path between X and Y"
            (r"(?:path|connection) between (.+) and (.+)",
             "MATCH path = shortestPath((a:Entity)-[*..4]-(b:Entity)) WHERE toLower(a.name) = toLower($entity1) AND toLower(b.name) = toLower($entity2) WITH path, relationships(path) as rels, nodes(path) as nodes RETURN [n in nodes | n.name] as path_nodes, [r in rels | r.relation_type] as relations, length(path) as path_length LIMIT 5",
             "Finding path between {entity1} and {entity2}"),
            
            # "Papers about X"
            (r"(?:papers|studies|research) (?:about|on|for) (.+)",
             "MATCH (e:Entity) WHERE toLower(e.name) = toLower($entity) RETURN e.name as entity, e.papers as paper_ids, size(e.papers) as paper_count ORDER BY size(e.papers) DESC",
             "Finding papers about {entity}"),
        ]
    
    def convert(self, nl_query: str) -> Tuple[Optional[str], Optional[str], Optional[Dict]]:
        """
        Convert natural language query to Cypher.
        
        Args:
            nl_query: Natural language question
        
        Returns:
            Tuple of (cypher_query, explanation, parameters) or (None, None, None) if no match
        """
        nl_query = nl_query.lower().strip()
        
        for pattern, cypher_template, description in self.patterns:
            match = re.search(pattern, nl_query, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                # Build substitution dict for description
                desc_subs = {}
                # Build parameters dict for Cypher query
                params = {}
                
                if len(groups) == 1:
                    # Single entity queries
                    entity = groups[0].strip().rstrip('?!.,;:')  # Remove trailing punctuation
                    
                    # Check if this is a "show all X" type query (captured entity type, not entity name)
                    if '$type' in cypher_template:
                        # This is "show all conditions" type query - group is the type
                        params['type'] = entity
                        desc_subs['type'] = entity
                    else:
                        # Regular entity query
                        params['entity'] = entity
                        desc_subs['entity'] = entity
                    
                    params['limit'] = 10
                    
                    # Handle "top N entities"
                    if '$limit' in cypher_template and re.search(r"top (\d+)", nl_query):
                        limit_match = re.search(r"top (\d+)", nl_query)
                        params['limit'] = int(limit_match.group(1))
                        desc_subs['limit'] = limit_match.group(1)
                
                elif len(groups) == 2:
                    # Two entity queries (path finding, find genes related to, or increase/decrease)
                    if '$entity1' in cypher_template:
                        # Path queries
                        params['entity1'] = groups[0].strip().rstrip('?!.,;:')
                        params['entity2'] = groups[1].strip().rstrip('?!.,;:')
                        desc_subs['entity1'] = groups[0].strip().rstrip('?!.,;:')
                        desc_subs['entity2'] = groups[1].strip().rstrip('?!.,;:')
                    elif '$type' in cypher_template:
                        # "Find genes related to X" queries
                        params['type'] = groups[0].strip()
                        params['entity'] = groups[1].strip().rstrip('?!.,;:')
                        desc_subs['type'] = groups[0].strip()
                        desc_subs['entity'] = groups[1].strip().rstrip('?!.,;:')
                    elif '$relation' in cypher_template:
                        # "What increases/decreases X" queries
                        params['relation'] = groups[0].strip()
                        params['entity'] = groups[1].strip().rstrip('?!.,;:')
                        desc_subs['relation'] = groups[0].strip()
                        desc_subs['entity'] = groups[1].strip().rstrip('?!.,;:')
                    else:
                        params['entity'] = groups[1].strip().rstrip('?!.,;:')
                        desc_subs['entity'] = groups[1].strip().rstrip('?!.,;:')
                
                # Generate query and description
                cypher_query = cypher_template  # No formatting needed - uses parameters
                explanation = description.format(**desc_subs)
                
                return cypher_query, explanation, params
        
        return None, None, None
    
    def get_example_queries(self) -> List[str]:
        """Return list of example queries users can try"""
        return [
            "What affects bone?",
            "What is affected by spaceflight?",
            "Show relationships for microgravity",
            "Find genes related to spaceflight",
            "Show top 10 entities",
            "Path between spaceflight and bone",
            "Papers about radiation",
        ]


def execute_cypher_query(cypher_query: str, graph_backend, parameters: Dict = None):
    """
    Execute a Cypher query using the Neo4j driver.
    
    Args:
        cypher_query: Cypher query string with parameterized placeholders
        graph_backend: GraphPlaceholder instance  
        parameters: Dictionary of parameters for the query
    
    Returns:
        List of result records as dicts
    """
    try:
        with graph_backend.driver.session() as session:
            result = session.run(cypher_query, parameters or {})
            records = []
            for record in result:
                records.append(dict(record))
            return records
    except Exception as e:
        raise Exception(f"Query execution failed: {str(e)}")
