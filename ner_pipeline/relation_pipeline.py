"""
Microstep B: Relationship Extraction Pipeline for Biomedical Entities

Extracts semantic relationships between entities (e.g., "microgravity affects bone",
"TP53 regulates apoptosis") using dependency parsing and pattern matching.
"""

import json
import re
import pandas as pd
import spacy
from pathlib import Path
from tqdm import tqdm
from collections import defaultdict
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_m1 import RELATION_TYPES, RELATION_PATTERNS
from config.config import ROOT

# Output directories
GRAPH_DATA_DIR = ROOT / "graph_data"

# Load spacy for dependency parsing
print("Loading spacy model for dependency parsing...")
try:
    nlp = spacy.load("en_core_sci_sm")
    print("✓ Scispacy model loaded")
except OSError:
    print("Installing en_core_sci_sm model...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", 
                   "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz"])
    nlp = spacy.load("en_core_sci_sm")


def load_entities_and_papers():
    """
    Load entities catalog and paper-entity mapping.
    
    Returns:
        tuple: (entities_dict, paper_entities_dict, entity_name_to_id)
    """
    # Load entities
    entities_path = GRAPH_DATA_DIR / "entities.json"
    with open(entities_path, 'r', encoding='utf-8') as f:
        entities_list = json.load(f)
    
    # Create lookup dictionaries
    entities_dict = {e['entity_id']: e for e in entities_list}
    
    # Create name->id mapping (including synonyms)
    entity_name_to_id = {}
    for entity in entities_list:
        # Add main name
        entity_name_to_id[entity['name'].lower()] = entity['entity_id']
        # Add all synonyms
        for syn in entity['synonyms']:
            entity_name_to_id[syn.lower()] = entity['entity_id']
    
    # Load paper-entity mapping
    paper_entities_path = GRAPH_DATA_DIR / "paper_entities.json"
    with open(paper_entities_path, 'r', encoding='utf-8') as f:
        paper_entities = json.load(f)
    
    return entities_dict, paper_entities, entity_name_to_id


def find_entity_mentions_in_text(text, entity_name_to_id):
    """
    Find all entity mentions in text with their positions.
    
    Args:
        text: Text to search
        entity_name_to_id: Dictionary mapping entity names/synonyms to IDs
        
    Returns:
        List of dicts with: entity_id, surface_form, start, end
    """
    mentions = []
    text_lower = text.lower()
    
    # Sort entity names by length (longest first) to match longer phrases first
    sorted_names = sorted(entity_name_to_id.keys(), key=len, reverse=True)
    
    for name in sorted_names:
        # Use word boundaries for better matching
        pattern = r'\b' + re.escape(name) + r'\b'
        
        for match in re.finditer(pattern, text_lower):
            entity_id = entity_name_to_id[name]
            mentions.append({
                'entity_id': entity_id,
                'surface_form': text[match.start():match.end()],
                'start': match.start(),
                'end': match.end()
            })
    
    # Remove overlapping mentions (keep longer ones)
    mentions.sort(key=lambda x: (x['start'], -(x['end'] - x['start'])))
    filtered_mentions = []
    last_end = -1
    
    for mention in mentions:
        if mention['start'] >= last_end:
            filtered_mentions.append(mention)
            last_end = mention['end']
    
    return filtered_mentions


def extract_relations_by_patterns(text, entities_in_text, entity_name_to_id):
    """
    Extract relations using regex patterns defined in config.
    
    Args:
        text: Text to analyze
        entities_in_text: List of entity mentions in the text
        entity_name_to_id: Entity name lookup
        
    Returns:
        List of relation dictionaries
    """
    relations = []
    
    # Split into sentences for better context
    doc = nlp(text)
    sentences = [sent.text for sent in doc.sents]
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        # Find entities in this sentence
        sent_entities = find_entity_mentions_in_text(sentence, entity_name_to_id)
        
        if len(sent_entities) < 2:
            continue  # Need at least 2 entities for a relation
        
        # Try each relation type's patterns
        for relation_type, patterns in RELATION_PATTERNS.items():
            for pattern in patterns:
                matches = list(re.finditer(pattern, sentence_lower, re.IGNORECASE))
                
                for match in matches:
                    # Find entities near this match
                    match_start = match.start()
                    match_end = match.end()
                    
                    # Find source entity (before or overlapping match start)
                    source_entities = [e for e in sent_entities if e['end'] <= match_end + 50]
                    # Find target entity (after or overlapping match end)
                    target_entities = [e for e in sent_entities if e['start'] >= match_start - 50]
                    
                    # Create relations for entity pairs
                    for source in source_entities:
                        for target in target_entities:
                            if source['entity_id'] != target['entity_id']:
                                relations.append({
                                    'source': source['entity_id'],
                                    'relation': relation_type,
                                    'target': target['entity_id'],
                                    'sentence': sentence.strip(),
                                    'confidence': 0.7  # Pattern-based confidence
                                })
    
    return relations


def extract_relations_by_dependency(text, entities_in_text, entities_dict):
    """
    Extract relations using spacy dependency parsing.
    Looks for verb-mediated connections between entities.
    
    Args:
        text: Text to analyze
        entities_in_text: List of entity mentions
        entities_dict: Entity information
        
    Returns:
        List of relation dictionaries
    """
    relations = []
    doc = nlp(text)
    
    # Create entity span mapping
    entity_spans = {}
    for ent in entities_in_text:
        # Find token indices that overlap with entity
        for token in doc:
            if token.idx >= ent['start'] and token.idx < ent['end']:
                entity_spans[token.i] = ent['entity_id']
    
    # Look for dependency patterns
    for sent in doc.sents:
        # Find all entity tokens in this sentence
        sent_entity_tokens = [(token, entity_spans[token.i]) 
                             for token in sent if token.i in entity_spans]
        
        if len(sent_entity_tokens) < 2:
            continue
        
        # Look for verb connections between entities
        for token1, ent1 in sent_entity_tokens:
            for token2, ent2 in sent_entity_tokens:
                if ent1 == ent2:
                    continue
                
                # Find connecting verbs
                connecting_verb = None
                
                # Check if tokens share a verb ancestor
                if token1.head.pos_ == 'VERB':
                    connecting_verb = token1.head
                elif token2.head.pos_ == 'VERB':
                    connecting_verb = token2.head
                
                if connecting_verb:
                    # Map verb to relation type
                    verb_lemma = connecting_verb.lemma_.lower()
                    relation_type = map_verb_to_relation(verb_lemma)
                    
                    if relation_type:
                        relations.append({
                            'source': ent1,
                            'relation': relation_type,
                            'target': ent2,
                            'sentence': sent.text.strip(),
                            'confidence': 0.6  # Dependency-based confidence
                        })
    
    return relations


def map_verb_to_relation(verb):
    """
    Map verb lemmas to relation types.
    """
    verb_mapping = {
        'affect': 'affects',
        'impact': 'affects',
        'influence': 'affects',
        'increase': 'increases',
        'elevate': 'increases',
        'upregulate': 'increases',
        'enhance': 'increases',
        'decrease': 'decreases',
        'reduce': 'decreases',
        'downregulate': 'decreases',
        'inhibit': 'inhibits',
        'suppress': 'decreases',
        'induce': 'induces',
        'trigger': 'induces',
        'promote': 'induces',
        'cause': 'causes',
        'lead': 'causes',
        'result': 'causes',
        'associate': 'associated_with',
        'correlate': 'associated_with',
        'link': 'associated_with',
        'relate': 'associated_with',
        'regulate': 'regulates',
        'control': 'regulates',
        'express': 'expressed_in',
        'measure': 'measured_in',
        'use': 'used_in',
    }
    return verb_mapping.get(verb, None)


def extract_relations_for_paper(paper_id, text, paper_entities, entities_dict, entity_name_to_id):
    """
    Extract all relations from a single paper.
    
    Args:
        paper_id: Paper identifier
        text: Combined title + abstract
        paper_entities: List of entity IDs for this paper
        entities_dict: Full entity catalog
        entity_name_to_id: Name->ID lookup
        
    Returns:
        List of relation dictionaries
    """
    if not text or pd.isna(text):
        return []
    
    # Find all entity mentions in text
    entities_in_text = find_entity_mentions_in_text(text, entity_name_to_id)
    
    # Filter to only entities that belong to this paper
    paper_entity_set = set(paper_entities)
    entities_in_text = [e for e in entities_in_text if e['entity_id'] in paper_entity_set]
    
    if len(entities_in_text) < 2:
        return []  # Need at least 2 entities
    
    relations = []
    
    # Extract using pattern matching
    try:
        pattern_relations = extract_relations_by_patterns(text, entities_in_text, entity_name_to_id)
        relations.extend(pattern_relations)
    except Exception as e:
        print(f"Warning: Pattern extraction failed for {paper_id}: {e}")
    
    # Extract using dependency parsing
    try:
        dep_relations = extract_relations_by_dependency(text, entities_in_text, entities_dict)
        relations.extend(dep_relations)
    except Exception as e:
        print(f"Warning: Dependency extraction failed for {paper_id}: {e}")
    
    # Add paper_id to all relations
    for rel in relations:
        rel['paper_id'] = paper_id
    
    return relations


def deduplicate_relations(raw_relations):
    """
    Aggregate and deduplicate relations across all papers.
    
    Args:
        raw_relations: List of all raw relation dictionaries
        
    Returns:
        List of deduplicated relations with evidence counts
    """
    print("\n📊 Deduplicating and aggregating relations...")
    
    # Group by (source, relation, target)
    relation_groups = defaultdict(lambda: {
        'papers': set(),
        'sentences': [],
        'confidence_scores': []
    })
    
    for rel in raw_relations:
        key = (rel['source'], rel['relation'], rel['target'])
        relation_groups[key]['papers'].add(rel['paper_id'])
        relation_groups[key]['sentences'].append(rel['sentence'])
        relation_groups[key]['confidence_scores'].append(rel.get('confidence', 0.5))
    
    # Create deduplicated relation catalog
    relation_catalog = []
    relation_id_counter = 1
    
    for (source, relation_type, target), data in relation_groups.items():
        relation_id = f"R{relation_id_counter:05d}"
        relation_id_counter += 1
        
        # Calculate aggregate confidence
        avg_confidence = sum(data['confidence_scores']) / len(data['confidence_scores'])
        
        relation_catalog.append({
            'relation_id': relation_id,
            'source': source,
            'relation': relation_type,
            'target': target,
            'papers': list(data['papers']),
            'evidence_count': len(data['papers']),
            'confidence': round(avg_confidence, 3),
            'sample_sentences': data['sentences'][:3]  # Keep up to 3 example sentences
        })
    
    # Sort by evidence count
    relation_catalog.sort(key=lambda x: x['evidence_count'], reverse=True)
    
    print(f"✓ Deduplication complete: {len(relation_catalog)} unique relations")
    
    # Print statistics
    relation_type_counts = defaultdict(int)
    for rel in relation_catalog:
        relation_type_counts[rel['relation']] += 1
    
    print("\n📈 Relation counts by type:")
    for rel_type in sorted(relation_type_counts.keys()):
        print(f"  {rel_type}: {relation_type_counts[rel_type]}")
    
    return relation_catalog


def run_relation_extraction(csv_path=None):
    """
    Run relation extraction over all papers.
    
    Args:
        csv_path: Path to cleaned papers CSV
        
    Outputs:
        - graph_data/raw_relations.jsonl: Raw relation mentions
        - graph_data/relations.json: Deduplicated relation catalog
    """
    if csv_path is None:
        csv_path = ROOT / "data_prep" / "cleaned_80.csv"
    
    print("\n🚀 Starting Relation Extraction Pipeline")
    print(f"📁 Reading papers from: {csv_path}")
    
    # Load entities
    entities_dict, paper_entities, entity_name_to_id = load_entities_and_papers()
    print(f"✓ Loaded {len(entities_dict)} entities")
    
    # Read papers
    df = pd.read_csv(csv_path)
    print(f"✓ Loaded {len(df)} papers")
    
    # Extract relations for each paper
    print(f"\n🔍 Extracting relations from papers...")
    all_relations = []
    raw_output_path = GRAPH_DATA_DIR / "raw_relations.jsonl"
    
    with open(raw_output_path, 'w', encoding='utf-8') as f:
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing papers"):
            paper_id = row["paper_id"]
            
            # Skip papers with no entities
            if paper_id not in paper_entities:
                continue
            
            # Combine title and abstract
            text = ""
            if pd.notna(row.get("title")):
                text += str(row["title"]) + ". "
            if pd.notna(row.get("abstract")):
                text += str(row["abstract"])
            
            # Extract relations
            relations = extract_relations_for_paper(
                paper_id, text, paper_entities[paper_id], 
                entities_dict, entity_name_to_id
            )
            
            # Write to JSONL
            if relations:
                f.write(json.dumps({
                    'paper_id': paper_id,
                    'relation_count': len(relations),
                    'relations': relations
                }) + '\n')
            
            all_relations.extend(relations)
    
    print(f"\n✓ Extracted {len(all_relations)} raw relations")
    print(f"✓ Raw relations saved to: {raw_output_path}")
    
    # Deduplicate and aggregate
    relation_catalog = deduplicate_relations(all_relations)
    
    # Save relation catalog
    relations_path = GRAPH_DATA_DIR / "relations.json"
    with open(relations_path, 'w', encoding='utf-8') as f:
        json.dump(relation_catalog, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Relation catalog saved to: {relations_path}")
    
    return relation_catalog


if __name__ == "__main__":
    # Run the full relation extraction pipeline
    relation_catalog = run_relation_extraction()
    
    print("\n" + "="*60)
    print("✅ RELATION EXTRACTION COMPLETE")
    print("="*60)
    print(f"📊 Total unique relations: {len(relation_catalog)}")
    print(f"📂 Outputs in: {GRAPH_DATA_DIR}")
