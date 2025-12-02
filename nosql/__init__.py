# nosql/__init__.py
"""
Knowledge graph client loader with hot-swappable adapter pattern.

Environment variables:
    KG_ADAPTER: "neo4j" or "placeholder" (default: "placeholder")
    NEO4J_URI: Neo4j connection URI (required if KG_ADAPTER=neo4j)
    NEO4J_USER: Neo4j username (required if KG_ADAPTER=neo4j)
    NEO4J_PASSWORD: Neo4j password (required if KG_ADAPTER=neo4j)

Usage:
    from nosql import GraphClient
    
    # GraphClient will be Neo4jAdapter or GraphPlaceholder based on KG_ADAPTER
    client = GraphClient()
    entities = client.get_entities(limit=10)
    client.close()
"""

import os
import warnings


def _load_graph_client():
    """
    Loads the appropriate graph client based on KG_ADAPTER environment variable.
    
    Returns:
        Neo4jAdapter class if KG_ADAPTER='neo4j', otherwise GraphPlaceholder
    """
    adapter_type = os.environ.get('KG_ADAPTER', 'placeholder').lower()
    
    if adapter_type == 'neo4j':
        try:
            from nosql.neo4j_adapter import Neo4jAdapter
            return Neo4jAdapter
        except ImportError as e:
            warnings.warn(
                f"Failed to import Neo4jAdapter: {e}. "
                f"Falling back to GraphPlaceholder. "
                f"Ensure neo4j package is installed: pip install neo4j",
                RuntimeWarning
            )
            from nosql.graph_placeholder import GraphPlaceholder
            return GraphPlaceholder
    else:
        # Default to placeholder
        from nosql.graph_placeholder import GraphPlaceholder
        return GraphPlaceholder


# Export the selected client class as GraphClient
GraphClient = _load_graph_client()

__all__ = ['GraphClient']
