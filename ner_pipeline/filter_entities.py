"""
Entity and Relation Filtering based on Importance Scores

Filters entities and relations to keep only high-quality, well-connected nodes
for knowledge graph construction. Uses a combined scoring metric:
  Score = (paper_count × 1.0) + (relation_count × 2.0) + (relation_type_diversity × 1.5)
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

# Filtering threshold
IMPORTANCE_THRESHOLD = 20  # Entities must score >= 20 to be included


def calculate_entity_scores(entities, relations):
    """
    Calculate importance scores for all entities.
    
    Args:
        entities: List of entity dictionaries
        relations: List of relation dictionaries
        
    Returns:
        Dictionary mapping entity_id to score data
    """
    print("📊 Calculating entity importance scores...")
    
    # Count relations per entity
    entity_relation_count = defaultdict(int)
    entity_relation_types = defaultdict(set)
    
    for rel in relations:
        for entity_id in [rel['source'], rel['target']]:
            entity_relation_count[entity_id] += 1
            entity_relation_types[entity_id].add(rel['relation'])
    
    # Calculate scores
    entity_scores = {}
    
    for entity in entities:
        eid = entity['entity_id']
        paper_count = len(entity['papers'])
        relation_count = entity_relation_count.get(eid, 0)
        relation_type_diversity = len(entity_relation_types.get(eid, set()))
        
        # Combined importance score
        score = (paper_count * 1.0) + (relation_count * 2.0) + (relation_type_diversity * 1.5)
        
        entity_scores[eid] = {
            'score': score,
            'paper_count': paper_count,
            'relation_count': relation_count,
            'diversity': relation_type_diversity,
            'passes_threshold': score >= IMPORTANCE_THRESHOLD
        }
    
    return entity_scores


def filter_entities(entities, entity_scores, threshold=IMPORTANCE_THRESHOLD):
    """
    Filter entities based on importance score threshold.
    
    Args:
        entities: List of all entities
        entity_scores: Score data from calculate_entity_scores
        threshold: Minimum score to keep entity
        
    Returns:
        List of filtered entities
    """
    print(f"\n🔍 Filtering entities (threshold: score >= {threshold})...")
    
    filtered = []
    
    for entity in entities:
        eid = entity['entity_id']
        if entity_scores[eid]['passes_threshold']:
            # Add score metadata to entity
            entity_copy = entity.copy()
            entity_copy['importance_score'] = entity_scores[eid]['score']
            entity_copy['relation_count'] = entity_scores[eid]['relation_count']
            filtered.append(entity_copy)
    
    print(f"✓ Kept {len(filtered)} entities (removed {len(entities) - len(filtered)})")
    
    # Print statistics by type
    type_counts = defaultdict(int)
    for entity in filtered:
        type_counts[entity['type']] += 1
    
    print("\n📈 Filtered entities by type:")
    for entity_type in sorted(type_counts.keys()):
        print(f"  {entity_type}: {type_counts[entity_type]}")
    
    return filtered


def filter_relations(relations, filtered_entity_ids):
    """
    Filter relations to only include those between filtered entities.
    
    Args:
        relations: List of all relations
        filtered_entity_ids: Set of entity IDs that passed filtering
        
    Returns:
        List of filtered relations
    """
    print(f"\n🔗 Filtering relations (both source and target must be in filtered set)...")
    
    filtered = []
    
    for rel in relations:
        if rel['source'] in filtered_entity_ids and rel['target'] in filtered_entity_ids:
            filtered.append(rel)
    
    print(f"✓ Kept {len(filtered)} relations (removed {len(relations) - len(filtered)})")
    
    # Print statistics by type
    type_counts = defaultdict(int)
    for rel in filtered:
        type_counts[rel['relation']] += 1
    
    print("\n📈 Filtered relations by type:")
    for rel_type in sorted(type_counts.keys()):
        print(f"  {rel_type}: {type_counts[rel_type]}")
    
    return filtered


def run_filtering():
    """
    Main filtering pipeline.
    
    Reads:
        - graph_data/entities.json
        - graph_data/relations.json
        
    Outputs:
        - graph_data/filtered_entities.json (high-quality entities)
        - graph_data/filtered_relations.json (relations between filtered entities)
        - graph_data/filtering_report.json (statistics and metadata)
    """
    print("\n🚀 Starting Entity and Relation Filtering Pipeline")
    print(f"📁 Reading from: {GRAPH_DATA_DIR}")
    
    # Load data
    entities_path = GRAPH_DATA_DIR / "entities.json"
    relations_path = GRAPH_DATA_DIR / "relations.json"
    
    with open(entities_path, 'r', encoding='utf-8') as f:
        entities = json.load(f)
    
    with open(relations_path, 'r', encoding='utf-8') as f:
        relations = json.load(f)
    
    print(f"✓ Loaded {len(entities)} entities")
    print(f"✓ Loaded {len(relations)} relations")
    
    # Calculate importance scores
    entity_scores = calculate_entity_scores(entities, relations)
    
    # Filter entities
    filtered_entities = filter_entities(entities, entity_scores, IMPORTANCE_THRESHOLD)
    filtered_entity_ids = set(e['entity_id'] for e in filtered_entities)
    
    # Filter relations
    filtered_relations = filter_relations(relations, filtered_entity_ids)
    
    # Calculate statistics
    original_isolated = sum(1 for eid, data in entity_scores.items() 
                          if data['relation_count'] == 0)
    filtered_isolated = sum(1 for e in filtered_entities 
                          if e['relation_count'] == 0)
    
    avg_relations = (len(filtered_relations) * 2 / len(filtered_entities)) if filtered_entities else 0
    density = (len(filtered_relations) / (len(filtered_entities) * (len(filtered_entities) - 1))) if len(filtered_entities) > 1 else 0
    
    # Create filtering report
    report = {
        'filtering_threshold': IMPORTANCE_THRESHOLD,
        'original_stats': {
            'entities': len(entities),
            'relations': len(relations),
            'isolated_entities': original_isolated
        },
        'filtered_stats': {
            'entities': len(filtered_entities),
            'relations': len(filtered_relations),
            'isolated_entities': filtered_isolated,
            'avg_relations_per_entity': round(avg_relations, 2),
            'graph_density_percent': round(density * 100, 2)
        },
        'reduction': {
            'entities_removed': len(entities) - len(filtered_entities),
            'entities_removed_percent': round((len(entities) - len(filtered_entities)) / len(entities) * 100, 1),
            'relations_removed': len(relations) - len(filtered_relations),
            'relations_removed_percent': round((len(relations) - len(filtered_relations)) / len(relations) * 100, 1)
        },
        'top_entities_by_score': [
            {
                'entity_id': e['entity_id'],
                'name': e['name'],
                'type': e['type'],
                'score': e['importance_score'],
                'papers': len(e['papers']),
                'relations': e['relation_count']
            }
            for e in sorted(filtered_entities, key=lambda x: x['importance_score'], reverse=True)[:20]
        ]
    }
    
    # Save filtered entities
    filtered_entities_path = GRAPH_DATA_DIR / "filtered_entities.json"
    with open(filtered_entities_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_entities, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Filtered entities saved to: {filtered_entities_path}")
    
    # Save filtered relations
    filtered_relations_path = GRAPH_DATA_DIR / "filtered_relations.json"
    with open(filtered_relations_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_relations, f, indent=2, ensure_ascii=False)
    print(f"✓ Filtered relations saved to: {filtered_relations_path}")
    
    # Save report
    report_path = GRAPH_DATA_DIR / "filtering_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"✓ Filtering report saved to: {report_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("✅ FILTERING COMPLETE")
    print("="*60)
    print(f"📊 Original: {len(entities)} entities, {len(relations)} relations")
    print(f"📊 Filtered: {len(filtered_entities)} entities, {len(filtered_relations)} relations")
    print(f"📊 Reduction: {report['reduction']['entities_removed_percent']}% entities, {report['reduction']['relations_removed_percent']}% relations")
    print(f"📊 Graph density: {report['filtered_stats']['graph_density_percent']}%")
    print(f"📊 Avg relations/entity: {report['filtered_stats']['avg_relations_per_entity']}")
    print(f"\n✨ All isolated entities removed: {original_isolated} → {filtered_isolated}")
    
    return filtered_entities, filtered_relations, report


if __name__ == "__main__":
    filtered_entities, filtered_relations, report = run_filtering()
