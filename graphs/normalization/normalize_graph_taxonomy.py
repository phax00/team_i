import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = ROOT / "graphs" / "normalization" / "normalization_rules.json"
INPUTS = {
    "core": ROOT / "graphs" / "core" / "knowledge_graph_core.json",
    "school": ROOT / "graphs" / "school_mvp" / "knowledge_graph_school_mvp.json",
}
OUTPUTS = {
    "core": ROOT / "graphs" / "core" / "knowledge_graph_core_normalized.json",
    "school": ROOT / "graphs" / "school_mvp" / "knowledge_graph_school_mvp_normalized.json",
}
REPORT_PATH = ROOT / "graphs" / "normalization" / "normalization_report.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def cleanup_text(value: str) -> str:
    value = value.replace("—", "-").replace("–", "-")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def merge_values(existing: Any, incoming: Any) -> Any:
    if existing in (None, "", []):
        return incoming
    if incoming in (None, "", []):
        return existing

    if isinstance(existing, list) and isinstance(incoming, list):
        combined: list[Any] = []
        for item in existing + incoming:
            if item not in combined:
                combined.append(item)
        return combined

    if isinstance(existing, list):
        return merge_values(existing, [incoming])

    if isinstance(incoming, list):
        return merge_values([existing], incoming)

    if existing == incoming:
        return existing

    if isinstance(existing, str) and isinstance(incoming, str):
        return existing if len(existing) >= len(incoming) else incoming

    return existing


def build_alias_map(rules_payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    alias_map: dict[str, dict[str, str]] = {}
    for label, config in rules_payload["rules"].items():
        label_map: dict[str, str] = {}
        for alias, canonical in config.get("aliases", {}).items():
            label_map[cleanup_text(alias).casefold()] = cleanup_text(canonical)
            label_map[cleanup_text(canonical).casefold()] = cleanup_text(canonical)
        alias_map[label] = label_map
    return alias_map


def canonicalize_name(label: str, name: str, alias_map: dict[str, dict[str, str]]) -> str:
    cleaned = cleanup_text(name)
    label_aliases = alias_map.get(label, {})
    return label_aliases.get(cleaned.casefold(), cleaned)


def normalize_graph(payload: dict[str, Any], alias_map: dict[str, dict[str, str]]) -> tuple[dict[str, Any], dict[str, Any]]:
    old_to_new: dict[str, str] = {}
    normalized_nodes: dict[str, dict[str, Any]] = {}
    node_merge_log: list[dict[str, Any]] = []

    for node in payload["nodes"]:
        label = node["label"]
        original_name = node["name"]
        canonical_name = canonicalize_name(label, original_name, alias_map)
        new_id = f"{label}:{slugify(canonical_name)}"

        old_to_new[node["id"]] = new_id
        node_copy = deepcopy(node)
        node_copy["id"] = new_id
        node_copy["name"] = canonical_name

        if new_id not in normalized_nodes:
            normalized_nodes[new_id] = node_copy
            if original_name != canonical_name:
                normalized_nodes[new_id]["normalized_from"] = [original_name]
        else:
            target = normalized_nodes[new_id]
            if original_name != canonical_name:
                target.setdefault("normalized_from", [])
                if original_name not in target["normalized_from"]:
                    target["normalized_from"].append(original_name)

            for key, value in node_copy.items():
                if key in {"id", "label"}:
                    continue
                target[key] = merge_values(target.get(key), value)

            node_merge_log.append(
                {
                    "merged_into": new_id,
                    "source_node_id": node["id"],
                    "source_name": original_name,
                    "canonical_name": canonical_name,
                }
            )

    normalized_relationships: list[dict[str, Any]] = []
    seen_rels = set()
    for rel in payload["relationships"]:
        rel_copy = deepcopy(rel)
        rel_copy["start"] = old_to_new[rel["start"]]
        rel_copy["end"] = old_to_new[rel["end"]]
        key = (
            rel_copy["start"],
            rel_copy["type"],
            rel_copy["end"],
            tuple(sorted((k, json.dumps(v, ensure_ascii=False, sort_keys=True)) for k, v in rel_copy.items() if k not in {"start", "type", "end"})),
        )
        if key in seen_rels:
            continue
        seen_rels.add(key)
        normalized_relationships.append(rel_copy)

    normalized_payload = deepcopy(payload)
    normalized_payload["meta"] = deepcopy(payload["meta"])
    normalized_payload["meta"]["normalization_rules"] = str(RULES_PATH.relative_to(ROOT)).replace("\\", "/")
    normalized_payload["meta"]["normalization_applied"] = True
    normalized_payload["meta"]["node_count"] = len(normalized_nodes)
    normalized_payload["meta"]["relationship_count"] = len(normalized_relationships)
    normalized_payload["nodes"] = sorted(normalized_nodes.values(), key=lambda item: (item["label"], item["id"]))
    normalized_payload["relationships"] = normalized_relationships

    report = {
        "node_merges": node_merge_log,
        "total_nodes_before": len(payload["nodes"]),
        "total_nodes_after": len(normalized_nodes),
        "total_relationships_before": len(payload["relationships"]),
        "total_relationships_after": len(normalized_relationships),
    }
    return normalized_payload, report


def main() -> None:
    rules_payload = load_json(RULES_PATH)
    alias_map = build_alias_map(rules_payload)

    final_report = {
        "rules_file": str(RULES_PATH.relative_to(ROOT)).replace("\\", "/"),
        "outputs": {},
    }

    for graph_key, input_path in INPUTS.items():
        payload = load_json(input_path)
        normalized_payload, report = normalize_graph(payload, alias_map)
        output_path = OUTPUTS[graph_key]
        save_json(output_path, normalized_payload)
        final_report["outputs"][graph_key] = {
            "input": str(input_path.relative_to(ROOT)).replace("\\", "/"),
            "output": str(output_path.relative_to(ROOT)).replace("\\", "/"),
            **report,
        }

    save_json(REPORT_PATH, final_report)
    print(f"Wrote {OUTPUTS['core'].name}")
    print(f"Wrote {OUTPUTS['school'].name}")
    print(f"Wrote {REPORT_PATH.name}")


if __name__ == "__main__":
    main()
