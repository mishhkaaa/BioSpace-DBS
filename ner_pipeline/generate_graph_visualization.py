# member1_pipeline/generate_graph_visualization.py
"""
Generate interactive HTML graph visualization using PyVis.
Creates a beautiful network view that can be embedded in the dashboard.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pyvis.network import Network
from nosql.graph_backend import GraphPlaceholder
from pathlib import Path

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def generate_graph_visualization(
    max_entities=50,
    output_file="knowledge_graph.html"
):
    """
    Generate interactive graph visualization.
    
    Args:
        max_entities: Number of top entities to include (default: 50)
        output_file: Output HTML filename
    """
    print("=" * 70)
    print("GENERATING INTERACTIVE GRAPH VISUALIZATION")
    print("=" * 70)
    
    # Connect to Neo4j
    graph = GraphPlaceholder()
    print(f"\n✓ Connected to Neo4j")
    
    # Fetch top entities
    print(f"\n📊 Fetching top {max_entities} entities...")
    entities = graph.get_entities(limit=max_entities)
    print(f"✓ Found {len(entities)} entities")
    
    # Create entity ID to name mapping
    entity_map = {e['entity_id']: e for e in entities}
    entity_ids = set(entity_map.keys())
    
    # Fetch all relations between these entities
    print(f"\n🔗 Fetching relationships...")
    all_relations = []
    for entity_id in entity_ids:
        relations = graph.get_entity_relations(entity_id)
        # Only keep relations where both source and target are in our entity set
        filtered = [r for r in relations 
                   if r['source_id'] in entity_ids and r['target_id'] in entity_ids]
        all_relations.extend(filtered)
    
    # Deduplicate relations
    seen = set()
    unique_relations = []
    for rel in all_relations:
        key = (rel['source_id'], rel['relation'], rel['target_id'])
        if key not in seen:
            seen.add(key)
            unique_relations.append(rel)
    
    print(f"✓ Found {len(unique_relations)} relationships")
    
    # Create PyVis network
    print(f"\n🎨 Building visualization...")
    net = Network(
        height="800px",
        width="100%",
        bgcolor="#222222",
        font_color="white",
        notebook=False
    )
    
    # Configure physics for better layout
    net.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -30000,
          "centralGravity": 0.3,
          "springLength": 200,
          "springConstant": 0.04,
          "damping": 0.09
        },
        "minVelocity": 0.75
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100,
        "navigationButtons": true,
        "keyboard": true
      }
    }
    """)
    
    # Color scheme by entity type
    type_colors = {
        'condition': '#FF6B6B',      # Red
        'tissue': '#4ECDC4',          # Teal
        'gene': '#95E1D3',            # Light green
        'protein': '#F38181',         # Pink
        'organism': '#AA96DA',        # Purple
        'process': '#FCBAD3',         # Light pink
        'assay': '#FFFFD2',           # Light yellow
        'disease': '#FFD93D',         # Yellow
        'cell_type': '#A8D8EA',       # Light blue
        'chemical': '#AA96DA'         # Purple
    }
    
    # Add nodes
    for entity_id, entity in entity_map.items():
        color = type_colors.get(entity['type'], '#CCCCCC')
        
        # Node size based on importance
        size = 10 + (entity['importance_score'] / 10)
        
        # Hover title with details
        title = f"""
        <b>{entity['name']}</b><br>
        Type: {entity['type']}<br>
        Importance: {entity['importance_score']:.1f}<br>
        Papers: {entity['paper_count']}<br>
        Relations: {entity['relation_count']}
        """
        
        net.add_node(
            entity_id,
            label=entity['name'],
            title=title,
            color=color,
            size=size
        )
    
    # Add edges
    relation_colors = {
        'increases': '#4CAF50',      # Green
        'decreases': '#F44336',      # Red
        'affects': '#2196F3',        # Blue
        'associated_with': '#9C27B0', # Purple
        'induces': '#FF9800',        # Orange
        'inhibits': '#795548',       # Brown
        'regulates': '#00BCD4',      # Cyan
        'causes': '#E91E63',         # Pink
        'expressed_in': '#8BC34A',   # Light green
        'measured_in': '#FFC107',    # Amber
        'used_in': '#607D8B',        # Blue grey
        'part_of': '#009688'         # Teal
    }
    
    for rel in unique_relations:
        color = relation_colors.get(rel['relation'], '#CCCCCC')
        
        title = f"""
        {rel['relation']}<br>
        Evidence: {rel['evidence_count']}<br>
        Confidence: {rel['confidence']:.2f}
        """
        
        net.add_edge(
            rel['source_id'],
            rel['target_id'],
            title=title,
            color=color,
            arrows='to',
            width=1 + rel['evidence_count']
        )
    
    # Save to HTML
    output_path = OUTPUT_DIR / output_file
    net.save_graph(str(output_path))
    
    print(f"\n✅ Visualization generated successfully!")
    print("=" * 70)
    print(f"\n📁 Output file: {output_path}")
    print(f"\n📊 Graph contains:")
    print(f"   - {len(entity_map)} entity nodes")
    print(f"   - {len(unique_relations)} relationship edges")
    print(f"\n🌐 Open in browser: file:///{output_path}")
    print("\n💡 Features:")
    print("   - Zoom: Mouse wheel")
    print("   - Pan: Click and drag")
    print("   - Hover: See entity/relation details")
    print("   - Click: Select nodes")
    print("   - Navigation buttons: Bottom right")
    print("\n🎨 Color coding:")
    print("   - Red: Conditions")
    print("   - Teal: Tissues")
    print("   - Light green: Genes")
    print("   - Size: Based on importance score")
    print("=" * 70)
    
    graph.close()
    
    return output_path


if __name__ == "__main__":
    # Generate with top 50 entities (adjust as needed)
    generate_graph_visualization(max_entities=50)
