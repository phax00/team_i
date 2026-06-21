# Source-to-Neo4j Pipeline Strategy

## MVP Pipeline

The current implementation treats the normalized JSON graph as the canonical
intermediate artifact:

```text
Job descriptions + people profiles + optional activity evidence
-> graph construction and taxonomy normalization
-> validated normalized JSON
-> Streamlit retrieval
-> static visualizer
-> automated tests
-> direct Neo4j Bolt import
```

This is appropriate for the MVP because all consumers use the same validated
nodes, relationships, IDs, and properties.

## Production Pipeline

Production ingestion should begin with governed enterprise sources rather than
with the demonstration snapshot:

```text
HRIS / people system
Job descriptions
IAM / organizational hierarchy
Jira / GitHub / operational systems
-> immutable raw landing zone
-> staging and normalization
-> validation and entity resolution
-> canonical graph model
-> batched transactional Neo4j writes
-> Neo4j graph database
-> retrieval API
-> SkillWiki chat and visualizer
```

## Data Layers

### Raw Sources

Keep original source records unchanged for auditability, reprocessing, lineage,
and recovery when transformation rules change.

### Staging

Create normalized staging entities for people, roles, job descriptions,
departments, teams, sites, countries, skills, systems, topics, reporting lines,
and activity events.

Staging responsibilities include:

- standardizing names and identifiers;
- resolving aliases such as `COO` to `Chief Operating Officer`;
- normalizing locations and organizational structures;
- separating structured concepts from free text;
- excluding or classifying sensitive fields.

### Validation

Before graph loading, verify:

- stable and unique entity IDs;
- valid relationship endpoints;
- one current primary role where required;
- valid reporting lines;
- location-to-country consistency;
- approved skill, system, and topic taxonomies;
- reviewed aliases and entity matches;
- source ownership, retention, and privacy rules.

### Canonical Graph

Produce canonical node and relationship records in memory or in governed
staging tables. The graph writer should then send typed batches directly to
Neo4j using parameterized Cypher and stable IDs.

### Neo4j Load

Recommended controls:

- uniqueness constraints before loading;
- indexes on names and business lookup fields;
- batched `MERGE` operations;
- deterministic relationship keys;
- transaction retries for transient deadlocks;
- reconciliation of imported and rejected record counts;
- incremental checkpoints and audit logs.

## Why Raw Files Are Not Loaded Directly

Raw job descriptions and people profiles contain inconsistent names, embedded
skills, ambiguous locations, missing relationship endpoints, and free text.
Loading them directly would move data-quality logic into database queries and
make the process harder to test and audit.

The preferred pattern is:

```text
Raw sources -> governed normalization -> validated graph records -> Neo4j
```

## Migration Plan

1. Keep normalized JSON as the reproducible MVP artifact.
2. Add source-specific connectors and staging validation.
3. Version entity-resolution and taxonomy rules.
4. Reuse the current direct importer contract for canonical graph records.
5. Add incremental upserts, deletion reconciliation, and audit logging.
6. Introduce a Neo4j-backed retrieval API.
7. Keep JSON only as a snapshot and offline fallback once Neo4j becomes primary.
