# Zep → Graphiti Migration Design Spec

**Date:** 2026-03-31
**Status:** Approved
**Author:** Remon + Claude

## 1. Overview

Replace Zep Cloud with self-hosted Graphiti + Neo4j for MiroFish's knowledge graph layer. Clean break — all Zep code removed, no backward compatibility.

### Goals

- **Self-hosted** — no cloud dependency, Neo4j runs in Docker alongside MiroFish
- **Gemini-native** — Graphiti supports Gemini for LLM + embeddings (already have key)
- **Clean break** — remove all Zep code, replace with Graphiti idiomatically
- **Preserve functionality** — graph building, ontology, search, entity reading, real-time updates all work

## 2. Infrastructure

### Neo4j via Docker Compose

New `docker-compose.yml` at project root:

```yaml
services:
  neo4j:
    image: neo4j:5.26-community
    ports:
      - "7687:7687"
      - "7474:7474"
    environment:
      NEO4J_AUTH: neo4j/mirofish123
      NEO4J_PLUGINS: '["apoc"]'
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: cypher-shell -u neo4j -p mirofish123 "RETURN 1"
      interval: 10s
      retries: 5

volumes:
  neo4j_data:
```

### Config Changes

Remove from `.env`:
```
ZEP_API_KEY=...
```

Add to `.env`:
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=mirofish123
```

Update `Config` class: remove `ZEP_API_KEY`, add `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`.

## 3. Shared Graphiti Client

New file: `backend/app/services/graphiti_client.py`

Singleton async client factory using Gemini for LLM + embeddings:

```python
from graphiti_core import Graphiti
from graphiti_core.llm_client.gemini_client import GeminiClient, LLMConfig
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig

async def get_graphiti() -> Graphiti:
    # Returns singleton, initializes indices on first call
    # Uses Config.NEO4J_URI, Config.NEO4J_USER, Config.NEO4J_PASSWORD
    # Uses Config.LLM_API_KEY for Gemini
```

## 4. group_id Strategy

Graphiti doesn't create separate graphs — it uses `group_id` to partition data within Neo4j. Each MiroFish project uses its `project_id` as the `group_id`.

- `graph_id = "mirofish_{hex}"` → `group_id = project.project_id`
- Project model: `graph_id` field renamed/repurposed to store the `group_id` (same value as `project_id`)

## 5. File Changes

### DELETE (4 files):
- `backend/app/services/zep_tools.py`
- `backend/app/services/zep_entity_reader.py`
- `backend/app/services/zep_graph_memory_updater.py`
- `backend/app/utils/zep_paging.py`

### CREATE (4 files):
- `backend/app/services/graphiti_client.py` — shared client factory
- `backend/app/services/graphiti_tools.py` — search/retrieval (replaces zep_tools.py)
- `backend/app/services/graphiti_entity_reader.py` — entity/edge reading (replaces zep_entity_reader.py)
- `backend/app/services/graphiti_memory_updater.py` — real-time simulation logging (replaces zep_graph_memory_updater.py)

### MODIFY (8 files):
- `backend/app/config.py` — swap ZEP for NEO4J config
- `backend/app/services/graph_builder.py` — rewrite for Graphiti API
- `backend/app/services/ontology_generator.py` — swap Zep types for Pydantic models
- `backend/app/services/oasis_profile_generator.py` — swap Zep search for Graphiti search
- `backend/app/services/simulation_runner.py` — swap memory manager
- `backend/app/services/__init__.py` — update imports
- `backend/app/api/graph.py` — update graph CRUD endpoints
- `backend/app/api/report.py` — update tool references

### Dependencies:
- Remove: `zep-cloud` from pyproject.toml/requirements.txt
- Add: `graphiti-core[google-genai]`

## 6. API Mapping

| Zep Call | Graphiti Replacement |
|----------|---------------------|
| `Zep(api_key=...)` | `get_graphiti()` singleton |
| `client.graph.create(graph_id, name)` | Not needed — use `group_id=project_id` |
| `client.graph.set_ontology(entities, edges)` | Pydantic models passed to `add_episode(entity_types=..., edge_types=...)` |
| `client.graph.add_batch(graph_id, episodes)` | `graphiti.add_episode_bulk(raw_episodes)` |
| `client.graph.episode.get(uuid)` | Not needed — `add_episode_bulk` completes synchronously |
| `client.graph.add(graph_id, type, data)` | `graphiti.add_episode(name, body, source=EpisodeType.text, group_id=pid)` |
| `client.graph.search(graph_id, query)` | `graphiti.search(query, group_ids=[pid])` |
| `client.graph.node.get(uuid)` | `EntityNode.get_by_uuid(driver, uuid)` |
| `client.graph.node.get_by_graph_id(graph_id)` | Cypher: `MATCH (n:Entity) WHERE n.group_id = $gid RETURN n` |
| `client.graph.node.get_entity_edges(uuid)` | Cypher: `MATCH (n {uuid: $uuid})-[r]-(m) RETURN r, m` |
| `client.graph.edge.get_by_graph_id(graph_id)` | Cypher: `MATCH ()-[r]->() WHERE r.group_id = $gid RETURN r` |
| `client.graph.delete(graph_id)` | Cypher: `MATCH (n) WHERE n.group_id = $gid DETACH DELETE n` |

## 7. Ontology Migration

Current Zep approach: dynamically create `EntityModel` and `EdgeModel` subclasses, pass to `set_ontology()`.

Graphiti approach: define Pydantic BaseModel classes, pass as `entity_types` and `edge_types` dicts to `add_episode()`.

The `ontology_generator.py` already produces entity/edge type definitions as JSON. We convert these to Pydantic models dynamically (same pattern, different base class).

## 8. Search Migration

Zep: `client.graph.search(graph_id, query, limit, scope, reranker)`

Graphiti: `graphiti.search_(query, config=SearchConfig)` with recipes:
- `EDGE_HYBRID_SEARCH_CROSS_ENCODER` — for fact/relationship search
- `NODE_HYBRID_SEARCH_RRF` — for entity search
- `COMBINED_HYBRID_SEARCH_CROSS_ENCODER` — for combined

All searches filter by `group_ids=[project_id]`.

## 9. Real-Time Memory Updates

Current: `ZepGraphMemoryUpdater` batches agent activities and sends via `client.graph.add()`.

New: `GraphitiMemoryUpdater` batches activities and sends via `graphiti.add_episode()` with `source=EpisodeType.text` and `group_id=project_id`.

Same batching/threading logic, different API call.

## 10. Testing Strategy

- Start Neo4j via Docker
- Run existing MiroFish flow: upload file → build graph → simulate
- Run new OSINT flow: research topic → build graph → simulate
- Verify entities and relationships are created in Neo4j (check via http://localhost:7474 browser)
- Verify search returns relevant results
- Verify real-time memory updates during simulation
