# member1_pipeline/deploy_to_cloud.py
"""
Deploy knowledge graph to Neo4j Aura (cloud).
Run this after updating config/neo4j_config.py with your Aura credentials.
"""

import os
os.environ['NEO4J_ENV'] = 'cloud'  # Force cloud mode

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from graph_builder_neo4j import GraphBuilder
from config.neo4j_config import get_neo4j_config

def deploy_to_cloud():
    print("=" * 70)
    print("DEPLOYING KNOWLEDGE GRAPH TO NEO4J AURA (CLOUD)")
    print("=" * 70)
    
    # Verify cloud config
    config = get_neo4j_config()
    print(f"\n📡 Target: {config['uri']}")
    print(f"👤 User: {config['user']}")
    
    if 'YOUR_INSTANCE_ID' in config['uri'] or 'YOUR_AURA_PASSWORD' in config['password']:
        print("\n❌ ERROR: Please update config/neo4j_config.py with your Neo4j Aura credentials!")
        print("\nSteps:")
        print("1. Go to https://console.neo4j.io/")
        print("2. Create a new instance (Free tier)")
        print("3. Copy the connection URI and password")
        print("4. Update CLOUD_CONFIG in config/neo4j_config.py")
        print("5. Run this script again")
        return
    
    # Confirm deployment
    print("\n⚠️  This will upload your graph to the cloud.")
    confirm = input("Continue? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("❌ Deployment cancelled.")
        return
    
    # Load data paths
    entities_path = "../graph_data/filtered_entities.json"
    relations_path = "../graph_data/filtered_relations.json"
    
    # Initialize builder
    builder = GraphBuilder()
    
    try:
        # Build graph in cloud
        builder.build_graph(entities_path, relations_path)
        
        print("\n" + "=" * 70)
        print("✅ DEPLOYMENT SUCCESSFUL!")
        print("=" * 70)
        print(f"\n🌐 Your graph is now accessible at: {config['uri']}")
        print(f"👥 Share these credentials with Member 2:")
        print(f"   URI: {config['uri']}")
        print(f"   User: {config['user']}")
        print(f"   Password: {config['password']}")
        print("\n💡 Member 2 should update her config/neo4j_config.py with these credentials.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        print("\nTroubleshooting:")
        print("- Check your internet connection")
        print("- Verify Neo4j Aura instance is running")
        print("- Confirm credentials are correct")
    
    finally:
        builder.close()

if __name__ == "__main__":
    deploy_to_cloud()
