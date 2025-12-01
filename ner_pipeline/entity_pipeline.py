"""
Microstep A: Named Entity Recognition Pipeline for Biomedical Space Research Papers

Extracts domain-specific entities (genes, proteins, conditions, tissues, etc.) from paper abstracts
using scispacy biomedical NER models combined with custom rule-based extraction for space-related terms.
"""

import json
import re
import spacy
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from collections import defaultdict
from fuzzywuzzy import fuzz
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config_m1 import ENTITY_TYPES, SPACE_CONDITIONS, ENTITY_SYNONYMS
from config.config import DATA_DIR, ROOT

# Output directories
GRAPH_DATA_DIR = ROOT / "graph_data"
GRAPH_DATA_DIR.mkdir(exist_ok=True)

# Load scispacy models
print("Loading scispacy NER models...")
try:
    # BC5CDR model for diseases and chemicals
    nlp_bc5cdr = spacy.load("en_ner_bc5cdr_md")
    # BioNLP13CG model for broader biomedical entities
    nlp_bionlp = spacy.load("en_ner_bionlp13cg_md")
    print("✓ Models loaded successfully")
except OSError as e:
    print(f"Error loading models: {e}")
    print("Please install models using:")
    print("  pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_bc5cdr_md-0.5.4.tar.gz")
    print("  pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_bionlp13cg_md-0.5.4.tar.gz")
    nlp_bc5cdr = None
    nlp_bionlp = None


def map_scispacy_type_to_our_schema(ent_label):
    """
    Map scispacy entity labels to our entity type schema.
    
    Scispacy labels:
    - BC5CDR: DISEASE, CHEMICAL
    - BioNLP13CG: AMINO_ACID, ANATOMICAL_SYSTEM, CANCER, CELL, CELLULAR_COMPONENT,
                  DEVELOPING_ANATOMICAL_STRUCTURE, GENE_OR_GENE_PRODUCT, IMMATERIAL_ANATOMICAL_ENTITY,
                  MULTI-TISSUE_STRUCTURE, ORGAN, ORGANISM, ORGANISM_SUBDIVISION, 
                  ORGANISM_SUBSTANCE, PATHOLOGICAL_FORMATION, SIMPLE_CHEMICAL, TISSUE
    """
    mapping = {
        # BC5CDR labels
        "DISEASE": "disease",
        "CHEMICAL": "chemical",
        
        # BioNLP13CG labels
        "GENE_OR_GENE_PRODUCT": "gene",
        "SIMPLE_CHEMICAL": "chemical",
        "CANCER": "disease",
        "CELL": "cell_type",
        "TISSUE": "tissue",
        "ORGAN": "tissue",
        "ORGANISM": "organism",
        "ANATOMICAL_SYSTEM": "tissue",
        "MULTI-TISSUE_STRUCTURE": "tissue",
        "ORGANISM_SUBDIVISION": "tissue",
        "CELLULAR_COMPONENT": "cell_type",
        "AMINO_ACID": "chemical",
        "ORGANISM_SUBSTANCE": "chemical",
        "PATHOLOGICAL_FORMATION": "disease",
        "DEVELOPING_ANATOMICAL_STRUCTURE": "tissue",
        "IMMATERIAL_ANATOMICAL_ENTITY": "tissue",
    }
    return mapping.get(ent_label, "process")  # Default to process if unknown


def extract_space_conditions(text):
    """
    Extract space-related condition entities using keyword matching.
    Returns list of entity dictionaries.
    """
    entities = []
    text_lower = text.lower()
    
    for condition in SPACE_CONDITIONS:
        # Use word boundaries for better matching
        pattern = r'\b' + re.escape(condition.lower()) + r'\b'
        matches = re.finditer(pattern, text_lower)
        
        for match in matches:
            entities.append({
                "surface_form": text[match.start():match.end()],
                "normalized_name": condition,
                "type": "condition",
                "start": match.start(),
                "end": match.end()
            })
    
    return entities


def extract_techniques_and_assays(text):
    """
    Extract experimental techniques and assays using regex patterns.
    """
    entities = []
    
    # Common technique patterns
    technique_patterns = [
        (r'\bRNA-seq\b', "RNA-seq"),
        (r'\bRNA sequencing\b', "RNA sequencing"),
        (r'\bq?RT-?PCR\b', "qPCR"),
        (r'\bWestern blot(?:ting)?\b', "Western blot"),
        (r'\bflow cytometry\b', "flow cytometry"),
        (r'\bimmunohistochemistry\b', "immunohistochemistry"),
        (r'\bIHC\b', "immunohistochemistry"),
        (r'\bELISA\b', "ELISA"),
        (r'\bmicroarray\b', "microarray"),
        (r'\bconfocal microscopy\b', "confocal microscopy"),
        (r'\bMRI\b', "MRI"),
        (r'\bCT scan\b', "CT scan"),
        (r'\bmass spectrometry\b', "mass spectrometry"),
        (r'\bChIP-seq\b', "ChIP-seq"),
        (r'\bATAC-seq\b', "ATAC-seq"),
    ]
    
    for pattern, normalized_name in technique_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            entities.append({
                "surface_form": match.group(0),
                "normalized_name": normalized_name,
                "type": "assay",
                "start": match.start(),
                "end": match.end()
            })
    
    return entities


def extract_entities_for_paper(paper_id, text):
    """
    Extract all entities from a single paper's text (title + abstract).
    Combines scispacy NER with custom rule-based extraction.
    
    Args:
        paper_id: Unique paper identifier (e.g., PMC4136787)
        text: Combined title and abstract text
        
    Returns:
        List of entity dictionaries with keys: paper_id, surface_form, normalized_name, type, start, end
    """
    entities = []
    
    if not text or pd.isna(text):
        return entities
    
    # 1. Extract using BC5CDR model (diseases and chemicals)
    if nlp_bc5cdr:
        try:
            doc_bc5cdr = nlp_bc5cdr(text)
            for ent in doc_bc5cdr.ents:
                entities.append({
                    "paper_id": paper_id,
                    "surface_form": ent.text,
                    "normalized_name": ent.text.lower().strip(),
                    "type": map_scispacy_type_to_our_schema(ent.label_),
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "source": "bc5cdr"
                })
        except Exception as e:
            print(f"Warning: BC5CDR extraction failed for {paper_id}: {e}")
    
    # 2. Extract using BioNLP13CG model (broader biomedical entities)
    if nlp_bionlp:
        try:
            doc_bionlp = nlp_bionlp(text)
            for ent in doc_bionlp.ents:
                entities.append({
                    "paper_id": paper_id,
                    "surface_form": ent.text,
                    "normalized_name": ent.text.lower().strip(),
                    "type": map_scispacy_type_to_our_schema(ent.label_),
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "source": "bionlp"
                })
        except Exception as e:
            print(f"Warning: BioNLP extraction failed for {paper_id}: {e}")
    
    # 3. Extract space-related conditions
    space_entities = extract_space_conditions(text)
    for ent in space_entities:
        ent["paper_id"] = paper_id
        ent["source"] = "rule_based"
    entities.extend(space_entities)
    
    # 4. Extract techniques and assays
    technique_entities = extract_techniques_and_assays(text)
    for ent in technique_entities:
        ent["paper_id"] = paper_id
        ent["source"] = "rule_based"
    entities.extend(technique_entities)
    
    return entities


def normalize_entity_name(surface_form):
    """
    Normalize entity surface form using synonym dictionary and text processing.
    
    Args:
        surface_form: Raw entity text
        
    Returns:
        Normalized entity name
    """
    # Convert to lowercase and strip
    normalized = surface_form.lower().strip()
    
    # Remove trailing punctuation
    normalized = re.sub(r'[.,;:!?]+$', '', normalized)
    
    # Check synonym dictionary
    if normalized in ENTITY_SYNONYMS:
        return ENTITY_SYNONYMS[normalized]
    
    # Check if any synonym key is in the text
    for key, value in ENTITY_SYNONYMS.items():
        if key in normalized:
            normalized = normalized.replace(key, value)
    
    return normalized


def deduplicate_entities(raw_entities):
    """
    Deduplicate and normalize entities across all papers.
    Uses fuzzy matching to merge similar entity mentions.
    
    Args:
        raw_entities: List of all entity dictionaries from all papers
        
    Returns:
        tuple: (entities_catalog, paper_entity_map)
            - entities_catalog: List of unique entities with IDs
            - paper_entity_map: Dict mapping paper_id to list of entity_ids
    """
    print("\n📊 Deduplicating and normalizing entities...")
    
    # Group by type first for efficiency
    entities_by_type = defaultdict(list)
    for ent in raw_entities:
        entities_by_type[ent["type"]].append(ent)
    
    entity_catalog = []
    entity_id_counter = 1
    paper_entity_map = defaultdict(set)
    
    # For each entity type, deduplicate
    for entity_type, entities in entities_by_type.items():
        print(f"  Processing {entity_type}: {len(entities)} raw mentions")
        
        # Group by normalized name
        name_groups = defaultdict(list)
        for ent in entities:
            normalized = normalize_entity_name(ent["surface_form"])
            name_groups[normalized].append(ent)
        
        # Create unique entities with fuzzy matching for similar names
        processed_names = set()
        
        for normalized_name, ent_list in name_groups.items():
            if normalized_name in processed_names:
                continue
            
            # Check if this entity is similar to any already processed
            merged = False
            for existing_entity in entity_catalog:
                if existing_entity["type"] == entity_type:
                    # Use fuzzy matching to check similarity
                    similarity = fuzz.ratio(normalized_name, existing_entity["name"])
                    if similarity > 85:  # 85% similarity threshold
                        # Merge into existing entity
                        existing_entity["synonyms"].add(normalized_name)
                        for ent in ent_list:
                            existing_entity["papers"].add(ent["paper_id"])
                            paper_entity_map[ent["paper_id"]].add(existing_entity["entity_id"])
                        merged = True
                        break
            
            if not merged:
                # Create new entity
                entity_id = f"E{entity_id_counter:05d}"
                entity_id_counter += 1
                
                # Collect all surface forms as synonyms
                synonyms = set([ent["surface_form"] for ent in ent_list])
                papers = set([ent["paper_id"] for ent in ent_list])
                
                entity_catalog.append({
                    "entity_id": entity_id,
                    "name": normalized_name,
                    "type": entity_type,
                    "synonyms": synonyms,
                    "papers": papers
                })
                
                # Update paper-entity map
                for paper_id in papers:
                    paper_entity_map[paper_id].add(entity_id)
                
                processed_names.add(normalized_name)
    
    # Convert sets to lists for JSON serialization
    for entity in entity_catalog:
        entity["synonyms"] = list(entity["synonyms"])
        entity["papers"] = list(entity["papers"])
    
    # Convert paper_entity_map sets to lists
    paper_entity_map = {paper_id: list(entity_ids) 
                        for paper_id, entity_ids in paper_entity_map.items()}
    
    print(f"\n✓ Deduplication complete: {len(entity_catalog)} unique entities")
    
    # Print statistics by type
    type_counts = defaultdict(int)
    for entity in entity_catalog:
        type_counts[entity["type"]] += 1
    
    print("\n📈 Entity counts by type:")
    for entity_type in sorted(type_counts.keys()):
        print(f"  {entity_type}: {type_counts[entity_type]}")
    
    return entity_catalog, paper_entity_map


def run_ner_over_corpus(csv_path=None):
    """
    Run NER extraction over all papers in the corpus.
    
    Args:
        csv_path: Path to cleaned papers CSV (default: data_prep/cleaned_80.csv)
        
    Outputs:
        - graph_data/raw_entities_per_paper.jsonl: Raw entity mentions
        - graph_data/entities.json: Deduplicated entity catalog
        - graph_data/paper_entities.json: Paper-to-entity mapping
    """
    if csv_path is None:
        csv_path = ROOT / "data_prep" / "cleaned_80.csv"
    
    print(f"\n🚀 Starting NER extraction pipeline")
    print(f"📁 Reading papers from: {csv_path}")
    
    # Read papers
    df = pd.read_csv(csv_path)
    print(f"✓ Loaded {len(df)} papers")
    
    # Ensure required columns exist
    required_cols = ["paper_id", "title", "abstract"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    
    # Extract entities for each paper
    print(f"\n🔍 Extracting entities from papers...")
    all_entities = []
    raw_output_path = GRAPH_DATA_DIR / "raw_entities_per_paper.jsonl"
    
    with open(raw_output_path, 'w', encoding='utf-8') as f:
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing papers"):
            paper_id = row["paper_id"]
            
            # Combine title and abstract
            text = ""
            if pd.notna(row.get("title")):
                text += str(row["title"]) + ". "
            if pd.notna(row.get("abstract")):
                text += str(row["abstract"])
            
            # Extract entities
            entities = extract_entities_for_paper(paper_id, text)
            
            # Write to JSONL for debugging
            if entities:
                f.write(json.dumps({
                    "paper_id": paper_id,
                    "entity_count": len(entities),
                    "entities": entities
                }) + '\n')
            
            all_entities.extend(entities)
    
    print(f"\n✓ Extracted {len(all_entities)} raw entity mentions")
    print(f"✓ Raw entities saved to: {raw_output_path}")
    
    # Deduplicate and normalize
    entity_catalog, paper_entity_map = deduplicate_entities(all_entities)
    
    # Save entity catalog
    entities_path = GRAPH_DATA_DIR / "entities.json"
    with open(entities_path, 'w', encoding='utf-8') as f:
        json.dump(entity_catalog, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Entity catalog saved to: {entities_path}")
    
    # Save paper-entity mapping
    paper_entities_path = GRAPH_DATA_DIR / "paper_entities.json"
    with open(paper_entities_path, 'w', encoding='utf-8') as f:
        json.dump(paper_entity_map, f, indent=2, ensure_ascii=False)
    print(f"✓ Paper-entity mapping saved to: {paper_entities_path}")
    
    return entity_catalog, paper_entity_map


if __name__ == "__main__":
    # Run the full NER pipeline
    entity_catalog, paper_entity_map = run_ner_over_corpus()
    
    print("\n" + "="*60)
    print("✅ NER PIPELINE COMPLETE")
    print("="*60)
    print(f"📊 Total unique entities: {len(entity_catalog)}")
    print(f"📄 Papers processed: {len(paper_entity_map)}")
    print(f"📂 Outputs in: {GRAPH_DATA_DIR}")
