# member1_pipeline/generate_graph_visualization.py
"""
Generate interactive HTML graph visualization using PyVis.
Creates a beautiful network view that can be embedded in the dashboard.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pyvis.network import Network
from nosql import GraphClient
from pathlib import Path

# Output directory
OUTPUT_DIR = Path(__file__).parent
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
    
    # Connect to graph (Neo4j or placeholder)
    graph = GraphClient()
    print(f"\n✓ Connected to graph backend")
    
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
    
    # Add click handler to show entity details panel
    with open(output_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Create entity data map for JavaScript access
    entity_data = {}
    for entity_id, entity in entity_map.items():
        # Get relations for this entity
        entity_relations = [r for r in unique_relations 
                           if r['source_id'] == entity_id or r['target_id'] == entity_id]
        entity_data[entity_id] = {
            'name': entity['name'],
            'type': entity['type'],
            'importance': entity['importance_score'],
            'papers': entity['paper_count'],
            'relation_count': entity['relation_count'],
            'relations': [
                {
                    'source': r['source'],
                    'relation': r['relation'],
                    'target': r['target'],
                    'evidence': r['evidence_count'],
                    'confidence': r['confidence']
                }
                for r in entity_relations[:20]  # Limit to first 20 relations
            ]
        }
    
    import json
    entity_data_json = json.dumps(entity_data, indent=2)
    
    # Inject styles and JavaScript for entity details panel
    click_handler_js = f"""
    <style>
    #entity-details {{
        position: fixed;
        top: 20px;
        right: 20px;
        width: 350px;
        max-height: 80vh;
        overflow-y: auto;
        background: rgba(30, 30, 30, 0.95);
        border: 2px solid #4CAF50;
        border-radius: 10px;
        padding: 20px;
        color: white;
        font-family: Arial, sans-serif;
        display: none;
        z-index: 1000;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }}
    #entity-details h3 {{
        margin: 0 0 10px 0;
        color: #4CAF50;
        font-size: 18px;
    }}
    #entity-details .close-btn {{
        position: absolute;
        top: 10px;
        right: 10px;
        background: #f44336;
        color: white;
        border: none;
        border-radius: 50%;
        width: 25px;
        height: 25px;
        cursor: pointer;
        font-size: 16px;
        line-height: 25px;
        text-align: center;
    }}
    #entity-details .metric {{
        margin: 10px 0;
        padding: 8px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 5px;
    }}
    #entity-details .metric-label {{
        color: #aaa;
        font-size: 12px;
    }}
    #entity-details .metric-value {{
        color: white;
        font-size: 16px;
        font-weight: bold;
    }}
    #entity-details .relations {{
        margin-top: 15px;
    }}
    #entity-details .relation-item {{
        margin: 8px 0;
        padding: 8px;
        background: rgba(255, 255, 255, 0.05);
        border-left: 3px solid #2196F3;
        border-radius: 3px;
        font-size: 12px;
    }}
    #entity-details .relation-type {{
        color: #4CAF50;
        font-weight: bold;
    }}
    </style>
    
    <div id="entity-details">
        <button class="close-btn" onclick="document.getElementById('entity-details').style.display='none'">×</button>
        <div id="details-content"></div>
    </div>
    
    <script>
    const entityData = {entity_data_json};
    
    // Handle node clicks to show entity details
    network.on("click", function(params) {{
        const detailsPanel = document.getElementById('entity-details');
        const detailsContent = document.getElementById('details-content');
        
        if (params.nodes.length > 0) {{
            const nodeId = params.nodes[0];
            const data = entityData[nodeId];
            
            if (data) {{
                let html = `
                    <h3>${{data.name}}</h3>
                    <div class="metric">
                        <div class="metric-label">Type</div>
                        <div class="metric-value">${{data.type}}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Importance Score</div>
                        <div class="metric-value">${{data.importance.toFixed(1)}}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Papers</div>
                        <div class="metric-value">${{data.papers}}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Relations</div>
                        <div class="metric-value">${{data.relation_count}}</div>
                    </div>
                `;
                
                if (data.relations && data.relations.length > 0) {{
                    html += '<div class="relations"><strong>Relationships:</strong>';
                    data.relations.forEach(rel => {{
                        html += `
                            <div class="relation-item">
                                <strong>${{rel.source}}</strong> 
                                <span class="relation-type">${{rel.relation}}</span> 
                                <strong>${{rel.target}}</strong><br>
                                <span style="color: #aaa; font-size: 11px;">
                                    Evidence: ${{rel.evidence}} | Confidence: ${{rel.confidence.toFixed(2)}}
                                </span>
                            </div>
                        `;
                    }});
                    html += '</div>';
                }}
                
                detailsContent.innerHTML = html;
                detailsPanel.style.display = 'block';
            }}
        }} else {{
            detailsPanel.style.display = 'none';
        }}
    }});
    </script>
    """
    
    # Insert before closing body tag
    html_content = html_content.replace('</body>', f'{click_handler_js}</body>')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
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
    # Generate with all entities for full knowledge graph
    generate_graph_visualization(max_entities=200, output_file="knowledge_graph_full.html")
