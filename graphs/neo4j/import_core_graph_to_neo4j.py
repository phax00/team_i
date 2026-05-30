import argparse
import json
import os
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRAPH_PATH = ROOT / "graphs" / "core" / "knowledge_graph_core.json"
DEFAULT_ENV_PATH = ROOT / ".env"
VALID_TOKEN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_simple_env(path: Path) -> None:
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
        description="Import the core enterprise knowledge graph JSON into Neo4j."
    )
    parser.add_argument(
        "--graph",
        type=Path,
        default=DEFAULT_GRAPH_PATH,
        help="Path to the knowledge graph JSON file.",
    )
    parser.add_argument(
        "--uri",
        default=first_env("NEO4J_URI", "neo4j_uri", default="bolt://localhost:7687"),
        help="Neo4j connection URI. Defaults to NEO4J_URI or bolt://localhost:7687.",
    )
    parser.add_argument(
        "--user",
        default=first_env("NEO4J_USER", "neo4j_user", default="neo4j"),
        help="Neo4j username. Defaults to NEO4J_USER or neo4j.",
    )
    parser.add_argument(
        "--password",
        default=first_env("NEO4J_PASSWORD", "neo4j_password"),
        help="Neo4j password. Defaults to NEO4J_PASSWORD.",
    )
    parser.add_argument(
        "--database",
        default=first_env("NEO4J_DATABASE", "neo4j_database", default="neo4j"),
        help="Neo4j database name. Defaults to NEO4J_DATABASE or neo4j.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Transaction batch size for nodes and relationships.",
    )
    return parser.parse_args()


def load_graph(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def chunked(items: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    return [items[index : index + batch_size] for index in range(0, len(items), batch_size)]


def sanitize_token(value: str, kind: str) -> str:
    if not VALID_TOKEN.fullmatch(value):
        raise ValueError(f"Invalid Neo4j {kind}: {value}")
    return value


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
    MERGE (start)-[r:{safe_type}]->(end)
    SET r += row.properties
    """


def prepare_node_rows(nodes: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        label = node["label"]
        properties = {key: value for key, value in node.items() if key != "label"}
        grouped.setdefault(label, []).append({"id": node["id"], "properties": properties})
    return grouped


def prepare_relationship_rows(
    relationships: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for rel in relationships:
        rel_type = rel["type"]
        properties = {
            key: value
            for key, value in rel.items()
            if key not in {"start", "type", "end"}
        }
        grouped.setdefault(rel_type, []).append(
            {
                "start_id": rel["start"],
                "end_id": rel["end"],
                "properties": properties,
            }
        )
    return grouped


def ensure_base_constraint(driver: Any, database: str) -> None:
    query = """
    CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
    FOR (n:Entity)
    REQUIRE n.id IS UNIQUE
    """
    driver.execute_query(query, database_=database)


def import_nodes(driver: Any, database: str, nodes: list[dict[str, Any]], batch_size: int) -> None:
    grouped = prepare_node_rows(nodes)
    for label, rows in grouped.items():
        query = build_node_query(label)
        for batch in chunked(rows, batch_size):
            driver.execute_query(query, rows=batch, database_=database)
        print(f"Imported {len(rows)} nodes with label {label}")


def import_relationships(
    driver: Any,
    database: str,
    relationships: list[dict[str, Any]],
    batch_size: int,
) -> None:
    grouped = prepare_relationship_rows(relationships)
    for rel_type, rows in grouped.items():
        query = build_relationship_query(rel_type)
        for batch in chunked(rows, batch_size):
            driver.execute_query(query, rows=batch, database_=database)
        print(f"Imported {len(rows)} relationships of type {rel_type}")


def main() -> None:
    args = parse_args()
    graph_path = args.graph.resolve()

    if not graph_path.exists():
        raise FileNotFoundError(f"Graph JSON not found: {graph_path}")

    if not args.password:
        raise ValueError(
            "Neo4j password is missing. Set NEO4J_PASSWORD or pass --password."
        )

    try:
        from neo4j import GraphDatabase
    except ImportError as exc:
        raise SystemExit(
            "The neo4j Python driver is not installed. Run: pip install neo4j"
        ) from exc

    graph = load_graph(graph_path)
    nodes = graph.get("nodes", [])
    relationships = graph.get("relationships", [])

    print(f"Graph file: {graph_path}")
    print(f"Nodes: {len(nodes)}")
    print(f"Relationships: {len(relationships)}")
    print(f"Connecting to {args.uri} / database {args.database}")

    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))
    try:
        driver.verify_connectivity()
        ensure_base_constraint(driver, args.database)
        import_nodes(driver, args.database, nodes, args.batch_size)
        import_relationships(driver, args.database, relationships, args.batch_size)
    finally:
        driver.close()

    print("Neo4j import finished successfully.")


if __name__ == "__main__":
    main()
