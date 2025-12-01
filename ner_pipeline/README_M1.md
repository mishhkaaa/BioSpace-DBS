# Member 1: Knowledge Graph Pipeline

## What Was Built

### Phase A: Entity Extraction
- **Script:** `entity_pipeline.py`
- **Input:** 80 papers from `data_prep/cleaned_80.csv`
- **Method:** scispacy NER models + custom regex
- **Output:** 593 entities → `graph_data/entities.json`

### Phase B: Relation Extraction
- **Script:** `relation_pipeline.py`
- **Method:** Pattern matching + dependency parsing
- **Output:** 1,303 relations → `graph_data/relations.json`

### Phase C: Filtering
- **Script:** `filter_entities.py`
- **Algorithm:** importance_score = (papers × 1.0) + (relations × 2.0) + (diversity × 1.5), threshold >= 20
- **Output:** 107 entities, 758 relations → `graph_data/filtered_*.json`

### Phase D: Neo4j Cloud Deployment
- **Script:** `graph_builder_neo4j.py`
- **Platform:** Neo4j Aura (cloud-hosted)
- **Database:** 107 nodes, 758 relationships

### Phase E: GraphBackend API
- **Script:** `nosql/graph_backend.py`
- **Class:** `GraphPlaceholder`
- **Methods:** `get_entities()`, `get_entity_by_name()`, `get_related_papers()`, `get_entity_relations()`

### Phase F: Interactive Visualization
- **Script:** `generate_graph_visualization.py`
- **Output:** `ner_pipeline/knowledge_graph_full.html`
- **Features:** Interactive PyVis graph with zoom/pan

---

## Setup for Member 2

1. Install dependencies: `pip install -r requirements.txt`
2. Get `.env` file with Neo4j credentials from Member 1, place in project root
3. Test: `python test_cloud_access.py`

## Using GraphBackend

```python
from nosql.graph_backend import GraphPlaceholder

graph = GraphPlaceholder()
entities = graph.get_entities(limit=10)
entity = graph.get_entity_by_name('spaceflight')
papers = graph.get_related_papers(entity['entity_id'])
relations = graph.get_entity_relations(entity['entity_id'])
graph.close()
```

## Dashboard Integration

**Embed PyVis graph:**
```python
import streamlit.components.v1 as components
with open('ner_pipeline/knowledge_graph_full.html', 'r') as f:
    components.html(f.read(), height=800)
```

**Neo4j Browser link:**
```
https://browser.neo4j.io/?connectURL=neo4j+s://78b1da4c.databases.neo4j.io&username=neo4j
```

## Files
- `ner_pipeline/` - All pipeline scripts
- `nosql/graph_backend.py` - API for dashboard
- `graph_data/filtered_*.json` - Final filtered data
- `ner_pipeline/knowledge_graph_full.html` - Interactive visualization
- `.env` - Neo4j credentials (not in Git)

## Stats
- 107 entities (filtered from 593)
- 758 relationships (filtered from 1,303)