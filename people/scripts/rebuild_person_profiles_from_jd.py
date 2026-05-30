import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VERBOSE = ROOT / "people" / "data" / "Person_Profiles_Master.json"
DEFAULT_JD_CATALOG = ROOT / "job_descriptions" / "catalog" / "JD_Catalog.json"
DEFAULT_LEAN = ROOT / "people" / "data" / "Person_Profiles_Lean.json"
DEFAULT_RESOLVED = ROOT / "people" / "data" / "Person_Profiles_Graph_Input.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def jd_index(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in catalog["job_descriptions"]:
        out[item["relative_path"]] = item
    return out


def normalize_jd_reference(jd_file: str | None) -> str | None:
    if not jd_file:
        return jd_file

    replacements = {
        "Job Descriptions/": "job_descriptions/source_docs/Job Descriptions/",
        "Generated Job Descriptions Final/": "job_descriptions/generated_final/Generated Job Descriptions Final/",
        "Generated Job Descriptions/": "job_descriptions/generated_drafts/Generated Job Descriptions/",
    }
    for old_prefix, new_prefix in replacements.items():
        if jd_file.startswith(old_prefix):
            return jd_file.replace(old_prefix, new_prefix, 1)
    return jd_file


def extract_jd_identity(jd_item: dict[str, Any]) -> dict[str, Any]:
    identity = jd_item.get("identity", {})
    reporting = jd_item.get("reporting_relationships", {})
    technical = jd_item.get("technical_and_business_knowledge", {})
    return {
        "role_from_jd": identity.get("Job Title"),
        "department_from_jd": identity.get("Department/Function"),
        "location_from_jd": identity.get("Location (Site/Region/Group)") or identity.get("Location"),
        "reports_to_from_jd": identity.get("Reports To (Role)") or identity.get("Reports To"),
        "direct_reports_from_jd": identity.get("Direct Reports") or reporting.get("Direct Reports (Number, Job Titles)") or reporting.get("Direct Reports"),
        "role_level_from_jd": identity.get("Role Level"),
        "technical_skills_baseline_from_jd": technical.get("technical_skills", []),
        "business_knowledge_baseline_from_jd": technical.get("business_knowledge_required", ""),
    }


def person_specific_view(person: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": person["name"],
        "profile_type": person["profile_type"],
        "jd_file": normalize_jd_reference(person.get("jd_file")),
        "manager_name": person.get("manager_name"),
        "team": person.get("team"),
        "primary_topics": person.get("primary_topics", []),
        "skills_person_specific": person.get("skills_explicit", []),
        "systems_known": person.get("systems_known", []),
        "languages": person.get("languages", []),
    }


def org_support_view(person: dict[str, Any]) -> dict[str, Any]:
    payload = person_specific_view(person)
    payload.update(
        {
            "role": person.get("role"),
            "site": person.get("site"),
            "country": person.get("country"),
        }
    )
    return payload


def build_lean(verbose_data: dict[str, Any]) -> dict[str, Any]:
    people = []
    for person in verbose_data["people"]:
        if person.get("jd_file"):
            people.append(person_specific_view(person))
        else:
            people.append(org_support_view(person))

    return {
        "meta": {
            "purpose": "Lean person profiles linked to the finalized job description document set.",
            "source_jd_folder": "job_descriptions/generated_final/Generated Job Descriptions Final",
            "modeling_rule": "JD-backed profiles keep only person-specific fields. Role, location, reporting baseline, and core skill baseline should be resolved from the linked JD catalog.",
            "source_precedence": verbose_data["meta"]["source_precedence"],
            "person_specific_fields_for_jd_backed_profiles": [
                "name",
                "profile_type",
                "jd_file",
                "manager_name",
                "team",
                "primary_topics",
                "skills_person_specific",
                "systems_known",
                "languages",
            ],
            "org_support_profile_fields": [
                "name",
                "profile_type",
                "jd_file",
                "role",
                "site",
                "country",
                "manager_name",
                "team",
                "primary_topics",
                "skills_person_specific",
                "systems_known",
                "languages",
            ],
            "dataset_summary": {
                "total_people": len(people),
                "jd_backed_people": sum(1 for p in people if p["jd_file"]),
                "org_support_people": sum(1 for p in people if not p["jd_file"]),
                "shared_jd_examples": [
                    "Project and Process Engineer.docx",
                    "Business Intelligence Developer.docx",
                ],
            },
        },
        "people": people,
    }


def build_resolved(lean_data: dict[str, Any], catalog_idx: dict[str, dict[str, Any]]) -> dict[str, Any]:
    resolved_people = []
    for person in lean_data["people"]:
        if not person.get("jd_file"):
            resolved_people.append(person)
            continue

        jd_file = normalize_jd_reference(person["jd_file"])
        if jd_file not in catalog_idx:
            raise KeyError(f"JD file not found in catalog: {jd_file}")

        jd_item = catalog_idx[jd_file]
        merged = dict(person)
        merged.update(extract_jd_identity(jd_item))
        merged["jd_role_summary"] = jd_item.get("role_summary", "")
        merged["jd_key_responsibilities"] = jd_item.get("key_responsibilities", [])
        merged["jd_relative_path"] = jd_item.get("relative_path")
        resolved_people.append(merged)

    return {
        "meta": {
            "purpose": "Graph input person profiles where JD-backed fields are materialized from JD_Catalog.json.",
            "resolution_rule": "Role, location, reporting baseline, and technical baseline are copied from the linked JD document.",
            "source_files": {
                "lean_profiles": str(DEFAULT_LEAN.relative_to(ROOT)).replace("\\", "/"),
                "jd_catalog": str(DEFAULT_JD_CATALOG.relative_to(ROOT)).replace("\\", "/"),
            },
            "dataset_summary": {
                "total_people": len(resolved_people),
                "resolved_from_jd": sum(1 for p in resolved_people if p.get("jd_file")),
                "org_support_people": sum(1 for p in resolved_people if not p.get("jd_file")),
            },
        },
        "people": resolved_people,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild lean and resolved person profiles from verbose backup + JD catalog.")
    parser.add_argument("--verbose-input", type=Path, default=DEFAULT_VERBOSE)
    parser.add_argument("--jd-catalog", type=Path, default=DEFAULT_JD_CATALOG)
    parser.add_argument("--lean-output", type=Path, default=DEFAULT_LEAN)
    parser.add_argument("--resolved-output", type=Path, default=DEFAULT_RESOLVED)
    args = parser.parse_args()

    verbose_data = load_json(args.verbose_input)
    catalog = load_json(args.jd_catalog)
    catalog_idx = jd_index(catalog)

    lean = build_lean(verbose_data)
    resolved = build_resolved(lean, catalog_idx)

    save_json(args.lean_output, lean)
    save_json(args.resolved_output, resolved)

    print(f"Wrote lean profiles: {args.lean_output}")
    print(f"Wrote resolved profiles: {args.resolved_output}")
    print(f"People: {len(lean['people'])}")


if __name__ == "__main__":
    main()
