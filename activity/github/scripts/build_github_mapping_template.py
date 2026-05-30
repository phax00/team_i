import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
GITHUB_ACTIVITY = ROOT / "activity" / "github" / "data" / "github_activity.json"
PERSON_PROFILES = ROOT / "people" / "data" / "Person_Profiles_Lean.json"
OUTPUT = ROOT / "activity" / "github" / "data" / "github_employee_mapping_template.json"


REPO_CANDIDATES = {
    "FastAPI/FastAPI": [
        "Nina Havel",
        "Erik Sykora",
        "Filip Hruby",
    ],
    "apache/airflow": [
        "Barbora Klinec",
        "David Mraz",
        "Roman Kolar",
        "Filip Hruby",
    ],
    "dbt-labs/dbt-core": [
        "Barbora Klinec",
        "David Mraz",
        "Roman Kolar",
        "Filip Hruby",
    ],
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_bot(login: str | None) -> bool:
    if not login:
        return False
    login_lower = login.lower()
    return "[bot]" in login_lower or login_lower.endswith("bot")


def candidate_pool(repos: list[str], valid_people: set[str]) -> list[str]:
    ordered: list[str] = []
    seen = set()
    for repo in repos:
        for candidate in REPO_CANDIDATES.get(repo, []):
            if candidate in valid_people and candidate not in seen:
                ordered.append(candidate)
                seen.add(candidate)
    return ordered


def main() -> None:
    github_data = load_json(GITHUB_ACTIVITY)
    people_data = load_json(PERSON_PROFILES)

    valid_people = {person["name"] for person in people_data["people"] if person.get("jd_file")}

    mappings = []
    for ident in github_data.get("source_identities", []):
        login = ident.get("source_login")
        repos = ident.get("repos_contributed_to", [])
        mappings.append(
            {
                "source_login": login,
                "source_user_id": ident.get("source_user_id"),
                "source_display_name": ident.get("source_display_name"),
                "repos_contributed_to": repos,
                "commit_count": ident.get("commit_count", 0),
                "pull_request_count": ident.get("pull_request_count", 0),
                "is_bot": is_bot(login),
                "mapping_status": "exclude_bot" if is_bot(login) else "needs_assignment",
                "synthetic_employee_name": None,
                "mapping_type": None,
                "confidence": None,
                "suggested_candidates": [] if is_bot(login) else candidate_pool(repos, valid_people),
                "notes": "Fill synthetic_employee_name only for identities you want to include in the MVP graph.",
            }
        )

    output = {
        "meta": {
            "generated_from": [
                str(GITHUB_ACTIVITY.relative_to(ROOT)).replace("\\", "/"),
                str(PERSON_PROFILES.relative_to(ROOT)).replace("\\", "/"),
            ],
            "note": "Template only. Review and assign source identities to synthetic employees manually before applying the mapping."
        },
        "mappings": mappings,
    }

    OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    print(f"Mappings: {len(mappings)}")


if __name__ == "__main__":
    main()
