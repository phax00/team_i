# SkillWiki

SkillWiki is a graph-grounded enterprise knowledge assistant. It combines structured knowledge graph retrieval with optional LLM assistance while keeping final answers tied to graph evidence.

The repository contains:

- `streamlit_app_clean.py`: simplified user-facing chat.
- `streamlit_app.py`: full internal/demo interface with evidence details.
- `docs/`: static knowledge graph visualizer for GitHub Pages or local use.
- `docs/data/knowledge_graph_core_normalized.json`: Basic normalized graph.
- `docs/data/knowledge_graph_school_mvp_normalized.json`: Detailed normalized graph.
- `tests/`: automated functional, regression, integrity, routing, performance, and scalability tests.
- `neo4j/`: optional Neo4j import and production scalability path.

## Quick Start

### Requirements

- Python 3.11 or newer.
- `pip`.
- Optional: Ollama for local LLM assistance.
- Optional: Gemini API key for online LLM assistance.
- Optional: Neo4j Desktop for the graph database version.

### 1. Install Dependencies

Open PowerShell in the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation, the app can also be run with the system Python after installing the dependencies.

### 2. Configure Optional Models

Create a local `.env` file if model assistance is required:

```env
GEMINI_API_KEY=your_gemini_key
APP_RUNTIME_MODE=local
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
```

For local Ollama:

```powershell
ollama pull llama3.2
```

Ollama Desktop normally starts the local service automatically. If it is not
running, start Ollama Desktop or run:

```powershell
ollama serve
```

Verify that Ollama is available:

```powershell
ollama list
curl.exe http://127.0.0.1:11434/api/tags
```

Model behavior:

- Local runtime: Ollama is preferred when model assistance is enabled.
- Online runtime: Gemini is optional and Graph Search remains the default.
- If a model is unavailable, times out, reaches its quota, or produces an unsupported answer, the app falls back to Graph Search.

### 3. Run SkillWiki

Run the clean MVP:

```powershell
streamlit run streamlit_app_clean.py
```

Run the full internal/demo app:

```powershell
streamlit run streamlit_app.py
```

The terminal prints the local Streamlit URL, normally `http://localhost:8501`.

## Knowledge Graph Visualizer

Start a local static server from the project root:

```powershell
python -m http.server 8000
```

Open:

```text
http://127.0.0.1:8000/docs/
```

The visualizer defaults to the Detailed Graph and supports dataset switching, presets, filters, search, node selection, and relationship exploration.

Online visualizer:

https://phax00.github.io/team_i/

## Architecture and Data Flow

SkillWiki separates offline graph construction from runtime retrieval:

```text
Job descriptions + person profiles + optional GitHub/Jira evidence
-> graph construction
-> taxonomy normalization
-> Basic and Detailed normalized JSON graphs
-> Streamlit chat + static graph visualizer
```

The Basic Graph contains the organizational model. The Detailed Graph adds
synthetic Jira and mapped public GitHub activity evidence.

At runtime:

```text
User question
-> query normalization and entity resolution
-> structured graph handler when available
-> optional Ollama/Gemini interpretation
-> graph evidence retrieval
-> answer validation
-> final answer or safe graph-only fallback
```

The knowledge graph remains the source of truth. Models may interpret or phrase
questions, but unsupported people, roles, relationships, or skills are rejected.

Editable diagrams:

- `drawio_diagrams/ARCHITECTURE_DIAGRAM.drawio`
- `drawio_diagrams/DATA_LINEAGE.drawio`

## Automated Tests

Run the complete test suite from the project root:

```powershell
python run_tests.py
```

This runner suppresses harmless Streamlit `bare mode` warnings that occur because the app is imported without `streamlit run`. It does not hide test failures or Python exceptions.

The standard unittest command also works, but prints Streamlit runtime warnings:

```powershell
python -m unittest discover -s tests -v
```

The suite currently contains 82 tests covering:

- Graph structure, IDs, labels, relationship endpoints, and organizational context.
- Expected chat behavior and previously observed regressions.
- Acronyms, aliases, typo normalization, follow-up questions, and entity resolution.
- Hallucination guards and LLM answer validation.
- Ollama, Gemini, timeout, quota, and Graph Search routing through mocks.
- Streamlit application imports and shared clean/full app logic.
- Static visualizer HTML, CSS, JavaScript, presets, and data contracts.
- Direct JSON-to-Neo4j validation, batching, idempotence, and safety checks.
- Retrieval performance and synthetic graph scaling.

The tests do not require a real Gemini key, running Ollama, Streamlit Cloud, or a live Neo4j database. External model behavior is mocked.

### Run One Test Module

```powershell
python -m unittest discover -s tests -p "test_graph_integrity.py" -v
python -m unittest discover -s tests -p "test_chat_behavior.py" -v
python -m unittest discover -s tests -p "test_model_routing_and_fallbacks.py" -v
python -m unittest discover -s tests -p "test_neo4j_direct_import.py" -v
```

### Retrieval Scaling Benchmark

Run the repeatable benchmark over synthetic 1x, 2x, 5x, and 10x versions of the Detailed Graph:

```powershell
python scripts\benchmark_graph_retrieval_scaling.py --multipliers 1 2 5 10
```

The benchmark measures:

- Index build time.
- Average and P95 evidence retrieval latency.
- Average and P95 graph-only answer latency.

Measured benchmark results:

| Scale | Nodes | Relationships | Index build | P95 evidence retrieval | P95 graph-only answer |
|---:|---:|---:|---:|---:|---:|
| 1x | 678 | 1,103 | 0.0573 s | 36.738 ms | 234.669 ms |
| 2x | 1,356 | 2,206 | 0.0710 s | 61.551 ms | 290.602 ms |
| 5x | 3,390 | 5,515 | 0.1352 s | 161.072 ms | 975.288 ms |
| 10x | 6,780 | 11,030 | 0.2197 s | 300.290 ms | 1,482.894 ms |

These results support JSON plus in-memory indexes for the current read-mostly
MVP. Concurrent updates, fine-grained access control, larger traversals, and
incremental ingestion are the triggers for moving runtime retrieval to Neo4j.

## Optional Neo4j Version

Neo4j is an additional scalability path. It does not replace the working JSON-based Streamlit MVP, and the current chat application is not yet configured to query Neo4j directly.

Current MVP:

```text
Normalized JSON graph -> in-memory Python indexes -> Streamlit + visualizer
```

Prepared Neo4j path:

```text
Normalized JSON graph -> direct batched Bolt import -> Neo4j
```

Recommended production path:

```text
JD + people + HR/operational sources
-> staging and validation
-> canonical graph tables
-> Neo4j
-> retrieval API
-> SkillWiki
```

### Direct Python Import

For a local Neo4j Desktop database, direct import through the Python driver is the easiest approach.

#### 1. Create and Start a Neo4j Database

1. Open Neo4j Desktop.
2. Create a local DBMS/project if one does not already exist.
3. Set and remember the database password.
4. Start the DBMS.
5. Confirm that the Bolt connection is available, normally at `bolt://localhost:7687`.


#### 2. Configure the Connection

Configure `.env`:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
```

The `.env` file is excluded by `.gitignore`. Never commit the password.

#### 3. Validate the Source Graph

First validate the graph without changing Neo4j:

```powershell
python neo4j\import_graph_to_neo4j.py --dataset detailed --dry-run
```

The dry run checks node IDs, labels, relationship types, and relationship endpoints. It does not require a running Neo4j server.

#### 4. Import the Graph

With the Neo4j DBMS running:

```powershell
python neo4j\import_graph_to_neo4j.py --dataset detailed
```

For the Basic Graph:

```powershell
python neo4j\import_graph_to_neo4j.py --dataset core
```

The direct importer:

- Uses batched `MERGE` queries through the official Neo4j Python driver.
- Creates a shared `Entity` label plus each domain label, such as `Person`, `Role`, or `Skill`.
- Preserves node properties, relationship properties, and parallel relationships with different provenance.
- Is idempotent when rerun with the same source graph and relationship order.

It does not remove nodes that disappeared from a newer source file. Importing Core after Detailed without replacement also leaves the Detailed-only nodes in Neo4j.

For a clean replacement in a dedicated SkillWiki database:

```powershell
python neo4j\import_graph_to_neo4j.py --dataset detailed --replace --confirm-replace
```

Both flags are required because this command deletes all existing nodes in the selected database before import.

If the importer reports `Cannot connect to Neo4j at bolt://localhost:7687`, start the DBMS in Neo4j Desktop and confirm its Bolt connection URI. If authentication fails, verify the username and password in `.env`.

### Validate the Neo4j Import

Run in Neo4j Browser:

```cypher
MATCH (n:Entity)
RETURN count(n) AS nodes;
```

```cypher
MATCH ()-[r]->()
RETURN count(r) AS relationships;
```

Expected counts for a clean, dedicated database:

Dataset: Detailed Graph
  - Nodes: 678
  - Relationships: 1103
  - Domain labels: 15
  - Relationship types: 28

Dataset: Basic Graph
  - Nodes: 568
  - Relationships: 746
  - Domain labels: 10
  - Relationship types: 16


Example business query:

```cypher
MATCH (p:Person)-[:KNOWS_SYSTEM]->(s:System {name: "ERP"})
RETURN p.name AS person, s.name AS system
ORDER BY person;
```

## Project Data

- Basic Graph: 568 nodes and 746 relationships.
- Detailed Graph: 678 nodes and 1103 relationships.
- Detailed Graph includes organizational data, job descriptions, skills, systems, topics, GitHub evidence, and Jira evidence.
- Demonstration data is synthetic to reduce privacy and GDPR risk.

## Security Notes

### Current MVP status

The current project is a demonstration MVP, not a production-secured HR
application. It does not implement user authentication, enterprise SSO,
role-based or attribute-based access control, evidence-level authorization,
application audit logging, or production HR data governance.

The security-related measures currently implemented are limited to:

- using synthetic data instead of confidential employee records;
- keeping local secrets in `.env` and online secrets in Streamlit secrets;
- excluding secrets, API keys, Neo4j passwords, caches, and local environments
  from Git;
- avoiding application-managed user passwords.

These measures reduce demonstration risk, but they are not a substitute for
production security controls.

### Future production security and governance strategy

Before using SkillWiki with real company or HR data, the following controls
would need to be designed, implemented, tested, and approved:

- enterprise SSO and authenticated user sessions;
- role-based or attribute-based authorization applied before graph retrieval,
  so restricted evidence never reaches an LLM or unauthorized user;
- node- and relationship-level metadata for source, owner, visibility,
  sensitivity, freshness, and validity;
- audit logs for queries, evidence access, graph imports, rejected records, and
  authorization decisions;
- retention, deletion, privacy-review, incident-response, backup, and recovery
  procedures;
- encryption and managed secret storage appropriate to the deployment platform;
- exclusion or separate handling of compensation, health, disciplinary, and
  other highly sensitive HR data;
- an approved model endpoint and contractual controls for any data sent to an
  external model provider;
- a governed integration flow: raw source -> staging -> validation and entity
  resolution -> canonical graph records -> Neo4j -> authorized retrieval API.

## Technical Standards

- `.env`, Streamlit secrets, virtual environments, logs, caches, and temporary
  render outputs are excluded through `.gitignore`.
- The clean Streamlit app reuses the full application's graph and answering
  logic rather than duplicating retrieval code.
- The online app defaults to Graph Search so it remains usable when Gemini quota
  is unavailable.
- Destructive Neo4j replacement requires both `--replace` and
  `--confirm-replace`.
- The project currently exposes no public API; therefore Swagger/Postman
  documentation is not applicable to the MVP.
- The MVP does not yet include a production security layer. A future production
  version would require a service layer between the UI and Neo4j, plus SSO,
  authorization, monitoring, audit logs, backups, and governed source refreshes.

## Online Links

- Knowledge Graph: https://phax00.github.io/team_i/
- SkillWiki Chat: https://skillwiki.streamlit.app/
