import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
GITHUB_ACTIVITY = ROOT / "activity" / "github" / "data" / "github_activity.json"
MAPPING_FILE = ROOT / "activity" / "github" / "data" / "github_employee_mapping_template.json"
OUTPUT = ROOT / "activity" / "github" / "data" / "github_activity_mapped.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply GitHub source identity mapping to synthetic employees.")
    parser.add_argument("--github-activity", type=Path, default=GITHUB_ACTIVITY)
    parser.add_argument("--mapping", type=Path, default=MAPPING_FILE)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    return parser.parse_args()


def mapping_index(mapping_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out = {}
    for item in mapping_data.get("mappings", []):
        login = item.get("source_login")
        if login:
            out[login] = item
    return out


def apply_mapping_to_commit(commit: dict[str, Any], idx: dict[str, dict[str, Any]]) -> dict[str, Any]:
    login = commit.get("author_login")
    mapping = idx.get(login, {})
    out = dict(commit)
    out["synthetic_employee_name"] = mapping.get("synthetic_employee_name")
    out["mapping_status"] = mapping.get("mapping_status")
    out["mapping_type"] = mapping.get("mapping_type")
    out["mapping_confidence"] = mapping.get("confidence")
    return out


def apply_mapping_to_pr(pr: dict[str, Any], idx: dict[str, dict[str, Any]]) -> dict[str, Any]:
    login = pr.get("user_login")
    mapping = idx.get(login, {})
    out = dict(pr)
    out["synthetic_employee_name"] = mapping.get("synthetic_employee_name")
    out["mapping_status"] = mapping.get("mapping_status")
    out["mapping_type"] = mapping.get("mapping_type")
    out["mapping_confidence"] = mapping.get("confidence")
    return out


def main() -> None:
    args = parse_args()
    github_data = load_json(args.github_activity)
    mapping_data = load_json(args.mapping)
    idx = mapping_index(mapping_data)

    repositories = []
    for repo in github_data.get("repositories", []):
        repo_out = dict(repo)
        repo_out["commits"] = [apply_mapping_to_commit(commit, idx) for commit in repo.get("commits", [])]
        repo_out["pull_requests"] = [apply_mapping_to_pr(pr, idx) for pr in repo.get("pull_requests", [])]
        repositories.append(repo_out)

    payload = {
        "meta": {
            "source_github_activity": str(args.github_activity.relative_to(ROOT)).replace("\\", "/"),
            "source_mapping": str(args.mapping.relative_to(ROOT)).replace("\\", "/"),
            "note": "This file keeps public GitHub activity but adds synthetic employee mapping fields for the school MVP."
        },
        "repositories": repositories,
        "source_identities": github_data.get("source_identities", []),
        "mappings_used": mapping_data.get("mappings", []),
    }

    save_json(args.out, payload)
    print(f"Wrote {args.out}")
    print(f"Repositories: {len(repositories)}")


if __name__ == "__main__":
    main()
