from __future__ import annotations

import argparse
import copy
import json
import logging
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.getLogger("streamlit").setLevel(logging.ERROR)

import streamlit_app as app

BASE_GRAPH = ROOT / "docs" / "data" / "knowledge_graph_school_mvp_normalized.json"
DEFAULT_MULTIPLIERS = [1, 2, 5, 10]
DEFAULT_QUERIES = [
    "who works in slovakia",
    "who knows erp",
    "who works with api",
    "petra novakova",
    "filip hruby",
    "data governance",
    "list all roles",
]


def clone_graph(payload: dict[str, Any], multiplier: int) -> dict[str, Any]:
    """Create a larger synthetic graph by duplicating the real MVP graph.

    The benchmark keeps the same node names and relationship types but rewrites IDs.
    This preserves retrieval characteristics while increasing graph size in a
    deterministic way without adding external dependencies.
    """
    if multiplier < 1:
        raise ValueError("Multiplier must be at least 1.")

    cloned_nodes: list[dict[str, Any]] = []
    cloned_relationships: list[dict[str, Any]] = []

    for copy_index in range(multiplier):
        suffix = f"__scale_{copy_index}"
        for node in payload.get("nodes", []):
            cloned = copy.deepcopy(node)
            cloned["id"] = f"{node['id']}{suffix}"
            cloned_nodes.append(cloned)

        for rel in payload.get("relationships", []):
            cloned_relationships.append(
                {
                    **copy.deepcopy(rel),
                    "start": f"{rel['start']}{suffix}",
                    "end": f"{rel['end']}{suffix}",
                }
            )

    meta = copy.deepcopy(payload.get("meta", {}))
    meta["synthetic_scale_multiplier"] = multiplier
    meta["node_count"] = len(cloned_nodes)
    meta["relationship_count"] = len(cloned_relationships)

    return {
        **copy.deepcopy(payload),
        "meta": meta,
        "nodes": cloned_nodes,
        "relationships": cloned_relationships,
    }


def write_temp_graph(payload: dict[str, Any]) -> str:
    temp = tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False)
    with temp:
        json.dump(payload, temp)
    return temp.name


def benchmark_multiplier(base_payload: dict[str, Any], multiplier: int, queries: list[str]) -> dict[str, Any]:
    scaled_payload = clone_graph(base_payload, multiplier)
    graph_path = write_temp_graph(scaled_payload)
    try:
        build_start = time.perf_counter()
        indexes = app.build_indexes(graph_path)
        build_seconds = time.perf_counter() - build_start

        query_times = []
        answer_times = []
        for query in queries:
            evidence_start = time.perf_counter()
            evidence = app.build_evidence(indexes, query)
            query_times.append(time.perf_counter() - evidence_start)

            answer_start = time.perf_counter()
            app.answer_question(
                question=query,
                dataset_name=f"Synthetic {multiplier}x",
                graph_payload=scaled_payload,
                indexes=indexes,
                gemini_model_name="",
                ollama_model_name="",
                ollama_host="",
            )
            answer_times.append(time.perf_counter() - answer_start)

        return {
            "multiplier": multiplier,
            "nodes": len(scaled_payload["nodes"]),
            "relationships": len(scaled_payload["relationships"]),
            "index_build_seconds": build_seconds,
            "avg_evidence_ms": statistics.mean(query_times) * 1000,
            "p95_evidence_ms": percentile(query_times, 95) * 1000,
            "avg_answer_ms": statistics.mean(answer_times) * 1000,
            "p95_answer_ms": percentile(answer_times, 95) * 1000,
        }
    finally:
        Path(graph_path).unlink(missing_ok=True)


def percentile(values: list[float], percentile_value: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((percentile_value / 100) * (len(ordered) - 1)))
    return ordered[index]


def run_benchmark(multipliers: list[int] | None = None, queries: list[str] | None = None) -> list[dict[str, Any]]:
    base_payload = json.loads(BASE_GRAPH.read_text(encoding="utf-8"))
    return [
        benchmark_multiplier(base_payload, multiplier, queries or DEFAULT_QUERIES)
        for multiplier in (multipliers or DEFAULT_MULTIPLIERS)
    ]


def format_markdown(results: list[dict[str, Any]]) -> str:
    lines = [
        "| Scale | Nodes | Relationships | Index build | Avg evidence retrieval | P95 evidence retrieval | Avg full graph answer | P95 full graph answer |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        lines.append(
            "| "
            f"{row['multiplier']}x | "
            f"{row['nodes']} | "
            f"{row['relationships']} | "
            f"{row['index_build_seconds']:.4f}s | "
            f"{row['avg_evidence_ms']:.3f} ms | "
            f"{row['p95_evidence_ms']:.3f} ms | "
            f"{row['avg_answer_ms']:.3f} ms | "
            f"{row['p95_answer_ms']:.3f} ms |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark SkillWiki graph retrieval at synthetic graph scales.")
    parser.add_argument("--multipliers", nargs="+", type=int, default=DEFAULT_MULTIPLIERS)
    args = parser.parse_args()

    results = run_benchmark(args.multipliers)
    print(format_markdown(results))


if __name__ == "__main__":
    main()
