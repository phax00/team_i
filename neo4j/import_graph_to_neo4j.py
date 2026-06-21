"""Import a SkillWiki JSON graph directly into Neo4j through the Bolt driver."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = ROOT / ".env"
GRAPH_PATHS = {
    "core": ROOT / "docs" / "data" / "knowledge_graph_core_normalized.json",
    "detailed": ROOT / "docs" / "data" / "knowledge_graph_school_mvp_normalized.json",
}
VALID_TOKEN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_simple_env(path: Path) -> None:
    """Load simple KEY=VALUE entries without overwriting existing variables."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def first_env(*keys: str, default: str | None = None) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return default


def parse_args() -> argparse.Namespace:
    load_simple_env(DEFAULT_ENV_PATH)

    parser = argparse.ArgumentParser(
        description="Import a normalized SkillWiki JSON graph directly into Neo4j."
    )
    parser.add_argument(
        "--dataset",
        choices=sorted(GRAPH_PATHS),
        default="detailed",
        help="Built-in graph dataset to import. Default: detailed.",
    )
    parser.add_argument(
        "--graph",
        type=Path,
        help="Optional custom normalized graph JSON path. Overrides --dataset.",
    )
    parser.add_argument(
        "--uri",
        default=first_env("NEO4J_URI", "neo4j_uri", default="bolt://localhost:7687"),
        help="Neo4j URI. Default: NEO4J_URI or bolt://localhost:7687.",
    )
    parser.add_argument(
        "--user",
        default=first_env("NEO4J_USER", "neo4j_user", default="neo4j"),
        help="Neo4j username. Default: NEO4J_USER or neo4j.",
    )
    parser.add_argument(
        "--password",
        default=first_env("NEO4J_PASSWORD", "neo4j_password"),
        help="Neo4j password. Prefer NEO4J_PASSWORD in .env.",
    )
    parser.add_argument(
        "--database",
        default=first_env("NEO4J_DATABASE", "neo4j_database", default="neo4j"),
        help="Neo4j database. Default: NEO4J_DATABASE or neo4j.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Number of nodes or relationships per transaction. Default: 200.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and summarize the graph without connecting to Neo4j.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete all existing Neo4j nodes before import.",
    )
    parser.add_argument(
        "--confirm-replace",
        action="store_true",
        help="Required together with --replace to confirm destructive deletion.",
    )
    return parser.parse_args()


def load_graph(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload.get("nodes"), list) or not isinstance(payload.get("relationships"), list):
        raise ValueError("Graph JSON must contain nodes and relationships arrays.")
    return payload


def chunked(items: list[dict[str, Any]], batch_size: int) -> Iterable[list[dict[str, Any]]]:
    if batch_size < 1:
        raise ValueError("Batch size must be at least 1.")
    for index in range(0, len(items), batch_size):
        yield items[index : index + batch_size]


def sanitize_token(value: str, kind: str) -> str:
    if not VALID_TOKEN.fullmatch(value):
        raise ValueError(f"Invalid Neo4j {kind}: {value!r}")
    return value


def normalize_property(value: Any) -> Any:
    """Convert unsupported nested values into deterministic JSON strings."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list) and all(
        item is None or isinstance(item, (str, int, float, bool)) for item in value
    ):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def validate_graph(payload: dict[str, Any]) -> dict[str, int]:
    nodes = payload["nodes"]
    relationships = payload["relationships"]
    node_ids = [str(node.get("id", "")) for node in nodes]
    known_ids = set(node_ids)

    if any(not node_id for node_id in node_ids):
        raise ValueError("Every node must have a non-empty id.")
    if len(node_ids) != len(known_ids):
        raise ValueError("Node IDs must be unique.")

    for node in nodes:
        sanitize_token(str(node.get("label", "")), "label")

    missing_endpoints = []
    for relationship in relationships:
        sanitize_token(str(relationship.get("type", "")), "relationship type")
        if relationship.get("start") not in known_ids or relationship.get("end") not in known_ids:
            missing_endpoints.append(
                (relationship.get("start"), relationship.get("type"), relationship.get("end"))
            )
    if missing_endpoints:
        raise ValueError(f"Relationships reference missing node IDs: {missing_endpoints[:5]}")

    return {
        "nodes": len(nodes),
        "relationships": len(relationships),
        "labels": len({node["label"] for node in nodes}),
        "relationship_types": len({rel["type"] for rel in relationships}),
    }


def build_node_query(label: str) -> str:
    safe_label = sanitize_token(label, "label")
    return f"""
    UNWIND $rows AS row
    MERGE (n:Entity:{safe_label} {{id: row.id}})
    SET n += row.properties
    """


def build_relationship_query(rel_type: str) -> str:
    safe_type = sanitize_token(rel_type, "relationship type")
    return f"""
    UNWIND $rows AS row
    MATCH (start:Entity {{id: row.start_id}})
    MATCH (end:Entity {{id: row.end_id}})
    MERGE (start)-[r:{safe_type} {{import_key: row.import_key}}]->(end)
    SET r += row.properties
    """


def prepare_node_rows(nodes: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        label = sanitize_token(str(node["label"]), "label")
        properties = {
            key: normalize_property(value)
            for key, value in node.items()
            if key != "label"
        }
        grouped.setdefault(label, []).append(
            {"id": str(node["id"]), "properties": properties}
        )
    return grouped


def prepare_relationship_rows(
    relationships: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    occurrence_by_triple: dict[tuple[str, str, str], int] = defaultdict(int)
    for relationship in relationships:
        rel_type = sanitize_token(str(relationship["type"]), "relationship type")
        start_id = str(relationship["start"])
        end_id = str(relationship["end"])
        triple = (start_id, rel_type, end_id)
        occurrence = occurrence_by_triple[triple]
        occurrence_by_triple[triple] += 1
        import_key = str(relationship.get("import_key") or "").strip()
        if not import_key:
            import_key = hashlib.sha256(
                f"{start_id}|{rel_type}|{end_id}|{occurrence}".encode("utf-8")
            ).hexdigest()
        properties = {
            key: normalize_property(value)
            for key, value in relationship.items()
            if key not in {"start", "type", "end"}
        }
        properties["import_key"] = import_key
        grouped.setdefault(rel_type, []).append(
            {
                "start_id": start_id,
                "end_id": end_id,
                "import_key": import_key,
                "properties": properties,
            }
        )
    return grouped


def ensure_constraints(driver: Any, database: str) -> None:
    driver.execute_query(
        """
        CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
        FOR (n:Entity)
        REQUIRE n.id IS UNIQUE
        """,
        database_=database,
    )
    driver.execute_query(
        """
        CREATE INDEX entity_name IF NOT EXISTS
        FOR (n:Entity)
        ON (n.name)
        """,
        database_=database,
    )


def replace_database_contents(driver: Any, database: str) -> None:
    driver.execute_query("MATCH (n) DETACH DELETE n", database_=database)


def import_nodes(
    driver: Any,
    database: str,
    nodes: list[dict[str, Any]],
    batch_size: int,
) -> None:
    for label, rows in sorted(prepare_node_rows(nodes).items()):
        query = build_node_query(label)
        for batch in chunked(rows, batch_size):
            driver.execute_query(query, rows=batch, database_=database)
        print(f"Imported {len(rows)} nodes with label {label}.")


def import_relationships(
    driver: Any,
    database: str,
    relationships: list[dict[str, Any]],
    batch_size: int,
) -> None:
    for rel_type, rows in sorted(prepare_relationship_rows(relationships).items()):
        query = build_relationship_query(rel_type)
        for batch in chunked(rows, batch_size):
            driver.execute_query(query, rows=batch, database_=database)
        print(f"Imported {len(rows)} relationships of type {rel_type}.")


def read_database_counts(driver: Any, database: str) -> tuple[int, int]:
    node_records, _, _ = driver.execute_query(
        "MATCH (n:Entity) RETURN count(n) AS count",
        database_=database,
    )
    relationship_records, _, _ = driver.execute_query(
        "MATCH (:Entity)-[r]->(:Entity) RETURN count(r) AS count",
        database_=database,
    )
    return int(node_records[0]["count"]), int(relationship_records[0]["count"])


def main() -> None:
    args = parse_args()
    graph_path = (args.graph or GRAPH_PATHS[args.dataset]).resolve()

    if not graph_path.exists():
        raise FileNotFoundError(f"Graph JSON not found: {graph_path}")
    if args.replace and not args.confirm_replace:
        raise ValueError("--replace requires --confirm-replace.")

    graph = load_graph(graph_path)
    summary = validate_graph(graph)

    print(f"Graph file: {graph_path}")
    print(
        "Validated graph: "
        f"{summary['nodes']} nodes, "
        f"{summary['relationships']} relationships, "
        f"{summary['labels']} labels, "
        f"{summary['relationship_types']} relationship types."
    )

    if args.dry_run:
        print("Dry run completed. Neo4j was not modified.")
        return

    if not args.password:
        raise ValueError(
            "Neo4j password is missing. Set NEO4J_PASSWORD in .env or pass --password."
        )

    try:
        from neo4j import GraphDatabase
        from neo4j.exceptions import AuthError, ClientError, ServiceUnavailable
    except ImportError as exc:
        raise SystemExit(
            "The Neo4j Python driver is not installed. Run: "
            "python -m pip install -r requirements.txt"
        ) from exc

    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))
    try:
        try:
            driver.verify_connectivity()
            if args.replace:
                replace_database_contents(driver, args.database)
                print("Existing Neo4j graph data deleted.")

            ensure_constraints(driver, args.database)
            import_nodes(driver, args.database, graph["nodes"], args.batch_size)
            import_relationships(
                driver,
                args.database,
                graph["relationships"],
                args.batch_size,
            )
            nodes, relationships = read_database_counts(driver, args.database)
        except AuthError as exc:
            raise SystemExit(
                "Neo4j authentication failed. Check NEO4J_USER and "
                "NEO4J_PASSWORD in .env."
            ) from exc
        except ClientError as exc:
            error_code = getattr(exc, "code", "") or getattr(exc, "neo4j_code", "")
            if error_code == "Neo.ClientError.Database.DatabaseNotFound":
                raise SystemExit(
                    f"Neo4j database {args.database!r} does not exist. Create and "
                    "start it in Neo4j Desktop, or run this Cypher against the "
                    f"system database: CREATE DATABASE {args.database} IF NOT EXISTS"
                ) from exc
            raise
        except ServiceUnavailable as exc:
            raise SystemExit(
                f"Cannot connect to Neo4j at {args.uri}. Start the Neo4j DBMS "
                "and confirm that Bolt is enabled on port 7687."
            ) from exc
    finally:
        driver.close()

    print(
        "Neo4j import finished successfully. "
        f"Database now contains {nodes} Entity nodes and {relationships} relationships."
    )


if __name__ == "__main__":
    main()
