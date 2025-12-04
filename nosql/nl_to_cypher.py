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
             "MATCH (n)-[r:AFFECTS|INCREASES|DECREASES|INDUCES]->(m) WHERE toLower(m.name) CONTAINS toLower('{entity}') RETURN n.name as source, type(r) as relation, m.name as target, r.evidence_count as evidence LIMIT 20",
             "Finding what affects {entity}"),
            
            # "What is affected by X?"
            (r"what (?:is )?affected by (.+)",
             "MATCH (n)-[r:AFFECTS|INCREASES|DECREASES|INDUCES]->(m) WHERE toLower(n.name) CONTAINS toLower('{entity}') RETURN n.name as source, type(r) as relation, m.name as target, r.evidence_count as evidence LIMIT 20",
             "Finding what is affected by {entity}"),
            
            # "What causes X?"
            (r"what causes (.+)",
             "MATCH (n)-[r:CAUSES|INDUCES]->(m) WHERE toLower(m.name) CONTAINS toLower('{entity}') RETURN n.name as source, type(r) as relation, m.name as target, r.evidence_count as evidence LIMIT 20",
             "Finding what causes {entity}"),
            
            # "What increases/decreases X?"
            (r"what (increases|decreases) (.+)",
             "MATCH (n)-[r:{relation_upper}]->(m) WHERE toLower(m.name) CONTAINS toLower('{entity}') RETURN n.name as source, type(r) as relation, m.name as target, r.evidence_count as evidence LIMIT 20",
             "Finding what {relation} {entity}"),
            
            # "Show relationships for X"
            (r"(?:show|find|get) (?:relationships|relations|connections) (?:for|of) (.+)",
             "MATCH (n)-[r]-(m) WHERE toLower(n.name) CONTAINS toLower('{entity}') RETURN n.name as source, type(r) as relation, m.name as target, r.evidence_count as evidence LIMIT 30",
             "Finding all relationships for {entity}"),
            
            # "Find genes related to X"
            (r"(?:find|show|get) (\w+) (?:related to|associated with) (.+)",
             "MATCH (n)-[r]-(m) WHERE toLower(n.name) CONTAINS toLower('{entity}') AND n.type = '{type}' RETURN n.name as source, type(r) as relation, m.name as target LIMIT 20",
             "Finding {type} related to {entity}"),
            
            # "What are the top entities?"
            (r"(?:what are |show |find )?(?:the )?top (\d+)? ?entities",
             "MATCH (e:Entity) RETURN e.name as name, e.type as type, e.importance_score as score, e.paper_count as papers ORDER BY e.importance_score DESC LIMIT {limit}",
             "Finding top {limit} entities"),
            
            # "Show all genes/proteins/conditions"
            (r"(?:show|find|get|list) (?:all )?(\w+)s?",
             "MATCH (e:Entity) WHERE e.type = '{type}' RETURN e.name as name, e.importance_score as score, e.paper_count as papers ORDER BY e.importance_score DESC LIMIT 30",
             "Finding all {type} entities"),
            
            # "Path between X and Y"
            (r"(?:path|connection) between (.+) and (.+)",
             "MATCH path = shortestPath((a:Entity)-[*..5]-(b:Entity)) WHERE toLower(a.name) CONTAINS toLower('{entity1}') AND toLower(b.name) CONTAINS toLower('{entity2}') RETURN path LIMIT 5",
             "Finding path between {entity1} and {entity2}"),
            
            # "Papers about X"
            (r"(?:papers|studies|research) (?:about|on|for) (.+)",
             "MATCH (e:Entity) WHERE toLower(e.name) CONTAINS toLower('{entity}') RETURN e.name as entity, e.papers as paper_ids, size(e.papers) as count",
             "Finding papers about {entity}"),
        ]
    
    def convert(self, nl_query: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Convert natural language query to Cypher.
        
        Args:
            nl_query: Natural language question
        
        Returns:
            Tuple of (cypher_query, explanation) or (None, None) if no match
        """
        nl_query = nl_query.lower().strip()
        
        for pattern, cypher_template, description in self.patterns:
            match = re.search(pattern, nl_query, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                # Build substitution dict
                subs = {}
                
                if len(groups) == 1:
                    # Single entity queries
                    entity = groups[0].strip()
                    subs['entity'] = entity
                    subs['limit'] = '10'
                    
                    # Handle type extraction for "find genes related to"
                    if 'type' in cypher_template:
                        # First group is the type, second is entity
                        type_match = re.search(r"(?:find|show|get) (\w+) (?:related to|associated with) (.+)", nl_query)
                        if type_match:
                            subs['type'] = type_match.group(1).rstrip('s')  # Remove plural
                            subs['entity'] = type_match.group(2).strip()
                    
                    # Handle "what increases/decreases X"
                    if 'relation_upper' in cypher_template:
                        relation_match = re.search(r"what (increases|decreases) (.+)", nl_query)
                        if relation_match:
                            subs['relation_upper'] = relation_match.group(1).upper()
                            subs['relation'] = relation_match.group(1)
                            subs['entity'] = relation_match.group(2).strip()
                    
                    # Handle "top N entities"
                    if 'limit' in cypher_template and re.search(r"top (\d+)", nl_query):
                        limit_match = re.search(r"top (\d+)", nl_query)
                        subs['limit'] = limit_match.group(1)
                    
                    # Handle entity type queries
                    if 'type' in cypher_template and 'entity' not in subs:
                        type_match = re.search(r"(?:show|find|get|list) (?:all )?(\w+)s?", nl_query)
                        if type_match:
                            subs['type'] = type_match.group(1).rstrip('s')
                
                elif len(groups) == 2:
                    # Two entity queries (path finding, or increase/decrease)
                    if 'entity1' in cypher_template:
                        subs['entity1'] = groups[0].strip()
                        subs['entity2'] = groups[1].strip()
                    elif 'relation' in cypher_template:
                        subs['relation'] = groups[0].strip()
                        subs['relation_upper'] = groups[0].strip().upper()
                        subs['entity'] = groups[1].strip()
                    else:
                        subs['entity'] = groups[1].strip()
                
                # Generate query and description
                cypher_query = cypher_template.format(**subs)
                explanation = description.format(**subs)
                
                return cypher_query, explanation
        
        return None, None
    
    def get_example_queries(self) -> List[str]:
        """Return list of example queries users can try"""
        return [
            "What affects bone?",
            "What is affected by spaceflight?",
            "What causes radiation damage?",
            "What increases myc?",
            "Show relationships for microgravity",
            "Find genes related to spaceflight",
            "Show top 10 entities",
            "Show all conditions",
            "Path between spaceflight and bone",
            "Papers about radiation",
        ]


def execute_cypher_query(cypher_query: str, graph_backend):
    """
    Execute a Cypher query using the Neo4j driver.
    
    Args:
        cypher_query: Cypher query string
        graph_backend: GraphPlaceholder instance
    
    Returns:
        List of result records as dicts
    """
    try:
        with graph_backend.driver.session() as session:
            result = session.run(cypher_query)
            records = []
            for record in result:
                records.append(dict(record))
            return records
    except Exception as e:
        raise Exception(f"Query execution failed: {str(e)}")
