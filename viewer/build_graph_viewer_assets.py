import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
DATA_DIR = DOCS_DIR / "data"
GRAPH_SOURCES = {
    "knowledge_graph_core_normalized.json": ROOT / "graphs" / "core" / "knowledge_graph_core_normalized.json",
    "knowledge_graph_school_mvp_normalized.json": ROOT / "graphs" / "school_mvp" / "knowledge_graph_school_mvp_normalized.json",
}
TARGET_SUMMARY = DATA_DIR / "graph_summary.json"


def normalize_person_file_labels(payload: dict[str, object]) -> dict[str, object]:
    text = json.dumps(payload, ensure_ascii=False)
    replacements = {
        "people/data/Person_Profiles_Linked.verbose_backup.json": "people/data/Person_Profiles_Master.json",
        "people/data/Person_Profiles_Linked.json": "people/data/Person_Profiles_Lean.json",
        "people/data/Person_Profiles_Resolved.json": "people/data/Person_Profiles_Graph_Input.json",
        "Person_Profiles_Linked.verbose_backup.json": "Person_Profiles_Master.json",
        "Person_Profiles_Linked.json": "Person_Profiles_Lean.json",
        "Person_Profiles_Resolved.json": "Person_Profiles_Graph_Input.json",
    }
    for old_value, new_value in replacements.items():
        text = text.replace(old_value, new_value)
    return json.loads(text)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    summary: dict[str, dict[str, object]] = {}

    for target_name, source_path in GRAPH_SOURCES.items():
        if not source_path.exists():
            raise FileNotFoundError(f"Missing source graph: {source_path}")

        target_path = DATA_DIR / target_name
        graph = json.loads(source_path.read_text(encoding="utf-8"))
        graph = normalize_person_file_labels(graph)
        target_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
        summary[target_name] = {
            "meta": graph.get("meta", {}),
            "node_labels": sorted({node["label"] for node in graph.get("nodes", [])}),
            "relationship_types": sorted({rel["type"] for rel in graph.get("relationships", [])}),
        }
        print(f"Copied graph JSON to {target_path}")

    TARGET_SUMMARY.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote summary JSON to {TARGET_SUMMARY}")


if __name__ == "__main__":
    main()
