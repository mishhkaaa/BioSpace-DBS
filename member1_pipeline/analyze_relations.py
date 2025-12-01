import json

# Load relations
with open('graph_data/relations.json', 'r', encoding='utf-8') as f:
    relations = json.load(f)

# Load entities for name lookup
with open('graph_data/entities.json', 'r', encoding='utf-8') as f:
    entities = json.load(f)

entity_lookup = {e['entity_id']: e for e in entities}

print("="*70)
print("RELATION EXTRACTION ANALYSIS")
print("="*70)

# Top relations by evidence count
print("\nTop 20 relations by evidence count:")
sorted_rels = sorted(relations, key=lambda x: x['evidence_count'], reverse=True)

for i, rel in enumerate(sorted_rels[:20]):
    source_name = entity_lookup.get(rel['source'], {}).get('name', rel['source'])
    target_name = entity_lookup.get(rel['target'], {}).get('name', rel['target'])
    print(f"{i+1:2d}. {source_name:25s} --[{rel['relation']:15s}]--> {target_name:25s} ({rel['evidence_count']} papers)")

# Sample sentences for top relation
print(f"\nSample sentences for top relation:")
top_rel = sorted_rels[0]
source_name = entity_lookup.get(top_rel['source'], {}).get('name', top_rel['source'])
target_name = entity_lookup.get(top_rel['target'], {}).get('name', top_rel['target'])
print(f"\n{source_name} --[{top_rel['relation']}]--> {target_name}")
for i, sent in enumerate(top_rel['sample_sentences'][:3], 1):
    print(f"  {i}. {sent[:150]}...")

# Entity connectivity analysis
print("\n" + "="*70)
print("ENTITY CONNECTIVITY (based on relations)")
print("="*70)

# Count relations per entity
entity_relation_count = {}
entity_relation_types = {}

for rel in relations:
    for entity_id in [rel['source'], rel['target']]:
        entity_relation_count[entity_id] = entity_relation_count.get(entity_id, 0) + 1
        if entity_id not in entity_relation_types:
            entity_relation_types[entity_id] = set()
        entity_relation_types[entity_id].add(rel['relation'])

# Top entities by connectivity
sorted_entities = sorted(entity_relation_count.items(), key=lambda x: x[1], reverse=True)

print("\nTop 20 most connected entities:")
for i, (entity_id, count) in enumerate(sorted_entities[:20]):
    entity = entity_lookup.get(entity_id, {})
    name = entity.get('name', entity_id)
    ent_type = entity.get('type', 'unknown')
    paper_count = len(entity.get('papers', []))
    rel_type_count = len(entity_relation_types[entity_id])
    print(f"{i+1:2d}. {name:30s} ({ent_type:12s}) - {count} relations, {rel_type_count} types, {paper_count} papers")

# Filtering recommendations
print("\n" + "="*70)
print("FILTERING RECOMMENDATIONS")
print("="*70)

isolated_entities = [e['entity_id'] for e in entities if e['entity_id'] not in entity_relation_count]
print(f"\nIsolated entities (no relations): {len(isolated_entities)} ({len(isolated_entities)/len(entities)*100:.1f}%)")

weak_entities = [eid for eid, count in entity_relation_count.items() if count <= 2]
print(f"Weakly connected entities (1-2 relations): {len(weak_entities)} ({len(weak_entities)/len(entities)*100:.1f}%)")

strong_entities = [eid for eid, count in entity_relation_count.items() if count >= 5]
print(f"Strongly connected entities (5+ relations): {len(strong_entities)} ({len(strong_entities)/len(entities)*100:.1f}%)")

print(f"\n💡 RECOMMENDATION:")
print(f"   Keep entities with 3+ relations: {sum(1 for c in entity_relation_count.values() if c >= 3)} entities")
print(f"   Keep entities with 5+ relations: {len(strong_entities)} entities")

# Calculate importance scores
print("\n" + "="*70)
print("ENTITY IMPORTANCE SCORING")
print("="*70)

entity_scores = []
for entity in entities:
    eid = entity['entity_id']
    paper_count = len(entity['papers'])
    relation_count = entity_relation_count.get(eid, 0)
    relation_type_diversity = len(entity_relation_types.get(eid, set()))
    
    # Combined score: paper_count * 1.0 + relation_count * 2.0 + diversity * 1.5
    score = (paper_count * 1.0) + (relation_count * 2.0) + (relation_type_diversity * 1.5)
    
    entity_scores.append({
        'entity_id': eid,
        'name': entity['name'],
        'type': entity['type'],
        'score': score,
        'papers': paper_count,
        'relations': relation_count,
        'diversity': relation_type_diversity
    })

# Sort by score
entity_scores.sort(key=lambda x: x['score'], reverse=True)

print("\nTop 30 entities by importance score:")
print(f"{'Rank':<5} {'Name':<30} {'Type':<12} {'Score':<7} {'Papers':<7} {'Rels':<6} {'Div':<5}")
print("-" * 85)
for i, ent in enumerate(entity_scores[:30], 1):
    print(f"{i:<5} {ent['name']:<30} {ent['type']:<12} {ent['score']:<7.1f} {ent['papers']:<7} {ent['relations']:<6} {ent['diversity']:<5}")

# Thresholds
print(f"\n📊 Entities by score threshold:")
for threshold in [10, 20, 30, 40, 50]:
    count = sum(1 for e in entity_scores if e['score'] >= threshold)
    print(f"   Score >= {threshold}: {count} entities")
