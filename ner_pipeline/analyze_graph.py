"""
Entity and Relation Analysis Module

Provides analysis functions for the filtered knowledge graph including:
- Entity ranking by centrality metrics
- Relation pattern analysis
- Entity type distribution
- Paper coverage statistics
"""

import json
from pathlib import Path
from collections import defaultdict
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.config import ROOT

# Paths
GRAPH_DATA_DIR = ROOT / "graph_data"


def load_filtered_data():
    """Load filtered entities and relations."""
    entities_path = GRAPH_DATA_DIR / "filtered_entities.json"
    relations_path = GRAPH_DATA_DIR / "filtered_relations.json"
    
    with open(entities_path, 'r', encoding='utf-8') as f:
        entities = json.load(f)
    
    with open(relations_path, 'r', encoding='utf-8') as f:
        relations = json.load(f)
    
    return entities, relations


def calculate_centrality_metrics(entities, relations):
    """
    Calculate graph centrality metrics for entities.
    
    Returns:
        Dictionary mapping entity_id to centrality scores
    """
    entity_lookup = {e['entity_id']: e for e in entities}
    
    # Degree centrality (number of connections)
    degree = defaultdict(int)
    for rel in relations:
        degree[rel['source']] += 1
        degree[rel['target']] += 1
    
    # In-degree and out-degree
    in_degree = defaultdict(int)
    out_degree = defaultdict(int)
    for rel in relations:
        out_degree[rel['source']] += 1
        in_degree[rel['target']] += 1
    
    # Calculate metrics for each entity
    metrics = {}
    for entity in entities:
        eid = entity['entity_id']
        metrics[eid] = {
            'entity_id': eid,
            'name': entity['name'],
            'type': entity['type'],
            'degree': degree.get(eid, 0),
            'in_degree': in_degree.get(eid, 0),
            'out_degree': out_degree.get(eid, 0),
            'paper_count': len(entity['papers']),
            'importance_score': entity.get('importance_score', 0)
        }
    
    return metrics


def analyze_entity_rankings(metrics):
    """
    Rank entities by different metrics.
    
    Returns:
        Dictionary with rankings by different criteria
    """
    rankings = {
        'by_degree': sorted(metrics.values(), key=lambda x: x['degree'], reverse=True),
        'by_importance': sorted(metrics.values(), key=lambda x: x['importance_score'], reverse=True),
        'by_papers': sorted(metrics.values(), key=lambda x: x['paper_count'], reverse=True),
        'by_out_degree': sorted(metrics.values(), key=lambda x: x['out_degree'], reverse=True),
        'by_in_degree': sorted(metrics.values(), key=lambda x: x['in_degree'], reverse=True)
    }
    
    return rankings


def analyze_relation_patterns(relations, entity_lookup):
    """
    Analyze common relation patterns and entity interactions.
    
    Returns:
        Dictionary with pattern statistics
    """
    # Most common relation types
    relation_counts = defaultdict(int)
    for rel in relations:
        relation_counts[rel['relation']] += 1
    
    # Entity pair interactions (regardless of relation type)
    entity_pairs = defaultdict(list)
    for rel in relations:
        pair = tuple(sorted([rel['source'], rel['target']]))
        entity_pairs[pair].append(rel['relation'])
    
    # Find most interconnected pairs
    top_pairs = sorted(entity_pairs.items(), key=lambda x: len(x[1]), reverse=True)[:20]
    
    # Relations by entity type pairs
    type_pair_counts = defaultdict(int)
    for rel in relations:
        source_type = entity_lookup[rel['source']]['type']
        target_type = entity_lookup[rel['target']]['type']
        type_pair = f"{source_type} → {target_type}"
        type_pair_counts[type_pair] += 1
    
    return {
        'relation_type_counts': dict(relation_counts),
        'top_entity_pairs': [
            {
                'entities': [entity_lookup[eid]['name'] for eid in pair],
                'relation_count': len(rels),
                'relation_types': rels
            }
            for pair, rels in top_pairs
        ],
        'type_pair_counts': dict(sorted(type_pair_counts.items(), 
                                       key=lambda x: x[1], reverse=True))
    }


def generate_analysis_report():
    """
    Generate comprehensive analysis report of the filtered graph.
    
    Outputs:
        - graph_data/entity_rankings.json
        - graph_data/relation_patterns.json
    """
    print("\n🚀 Starting Graph Analysis")
    
    # Load data
    entities, relations = load_filtered_data()
    entity_lookup = {e['entity_id']: e for e in entities}
    
    print(f"✓ Loaded {len(entities)} entities and {len(relations)} relations")
    
    # Calculate centrality metrics
    print("\n📊 Calculating centrality metrics...")
    metrics = calculate_centrality_metrics(entities, relations)
    
    # Generate rankings
    print("📊 Generating entity rankings...")
    rankings = analyze_entity_rankings(metrics)
    
    # Analyze relation patterns
    print("📊 Analyzing relation patterns...")
    patterns = analyze_relation_patterns(relations, entity_lookup)
    
    # Prepare output reports
    rankings_report = {
        'top_by_degree': rankings['by_degree'][:30],
        'top_by_importance': rankings['by_importance'][:30],
        'top_by_papers': rankings['by_papers'][:30],
        'top_influencers': rankings['by_out_degree'][:20],  # High out-degree
        'top_influenced': rankings['by_in_degree'][:20]     # High in-degree
    }
    
    # Save reports
    rankings_path = GRAPH_DATA_DIR / "entity_rankings.json"
    with open(rankings_path, 'w', encoding='utf-8') as f:
        json.dump(rankings_report, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Entity rankings saved to: {rankings_path}")
    
    patterns_path = GRAPH_DATA_DIR / "relation_patterns.json"
    with open(patterns_path, 'w', encoding='utf-8') as f:
        json.dump(patterns, f, indent=2, ensure_ascii=False)
    print(f"✓ Relation patterns saved to: {patterns_path}")
    
    # Print summary
    print("\n" + "="*70)
    print("ANALYSIS SUMMARY")
    print("="*70)
    
    print("\n🏆 Top 10 Entities by Degree (Most Connected):")
    for i, ent in enumerate(rankings['by_degree'][:10], 1):
        print(f"{i:2d}. {ent['name']:30s} ({ent['type']:12s}) - {ent['degree']} connections")
    
    print("\n🔬 Top 10 Most Common Relation Types:")
    sorted_rels = sorted(patterns['relation_type_counts'].items(), 
                        key=lambda x: x[1], reverse=True)
    for i, (rel_type, count) in enumerate(sorted_rels[:10], 1):
        print(f"{i:2d}. {rel_type:20s} - {count} relations")
    
    print("\n🔗 Top 5 Most Interconnected Entity Pairs:")
    for i, pair in enumerate(patterns['top_entity_pairs'][:5], 1):
        ents = pair['entities']
        print(f"{i}. {ents[0]} ↔ {ents[1]} ({pair['relation_count']} relations)")
        print(f"   Types: {', '.join(pair['relation_types'])}")
    
    print("\n📊 Top 10 Entity Type Interactions:")
    sorted_types = sorted(patterns['type_pair_counts'].items(), 
                         key=lambda x: x[1], reverse=True)
    for i, (type_pair, count) in enumerate(sorted_types[:10], 1):
        print(f"{i:2d}. {type_pair:40s} - {count} relations")
    
    print("\n✅ Analysis complete!")
    
    return rankings_report, patterns


if __name__ == "__main__":
    rankings, patterns = generate_analysis_report()
