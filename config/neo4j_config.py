# config/neo4j_config.py
"""
Neo4j connection configuration.
All credentials are loaded from .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

def get_neo4j_config():
    """
    Returns Neo4j configuration from environment variables.
    All credentials must be set in .env file.
    """
    return {
        'uri': os.getenv('NEO4J_URI'),
        'user': os.getenv('NEO4J_USER', 'neo4j'),
        'password': os.getenv('NEO4J_PASSWORD')
    }
