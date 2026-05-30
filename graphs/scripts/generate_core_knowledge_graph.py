import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
JD_CATALOG = ROOT / "job_descriptions" / "catalog" / "JD_Catalog.json"
PERSON_RESOLVED = ROOT / "people" / "data" / "Person_Profiles_Graph_Input.json"
OUTPUT_JSON = ROOT / "graphs" / "core" / "knowledge_graph_core.json"
OUTPUT_DIR = ROOT / "graphs" / "core" / "csv" / "knowledge_graph_core_csv"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


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


def add_node(store: dict[str, dict[str, Any]], node_type: str, key: str, props: dict[str, Any]) -> str:
    node_id = f"{node_type}:{slugify(key)}"
    if node_id not in store:
        store[node_id] = {"id": node_id, "label": node_type, **props}
    else:
        for k, v in props.items():
            if v not in (None, "", []):
                store[node_id][k] = v
    return node_id


def add_rel(rels: list[dict[str, Any]], start: str, rel_type: str, end: str, props: dict[str, Any] | None = None) -> None:
    rel = {"start": start, "type": rel_type, "end": end}
    if props:
        rel.update(props)
    rels.append(rel)


def split_country_from_location(location: str | None) -> tuple[str | None, str | None]:
    if not location:
        return None, None

    known_countries = [
        "Austria",
        "Slovakia",
        "Romania",
        "Netherlands",
        "Czech Republic",
        "Poland",
        "Germany",
    ]

    for country in known_countries:
        if country in location:
            site = location.replace(country, "").strip(" ,-/")
            return (site or None), country
    return location, None


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fieldnames})


def main() -> None:
    jd_catalog = load_json(JD_CATALOG)
    people_data = load_json(PERSON_RESOLVED)

    jd_by_path = {item["relative_path"]: item for item in jd_catalog["job_descriptions"]}

    nodes: dict[str, dict[str, Any]] = {}
    rels: list[dict[str, Any]] = []

    person_lookup: dict[str, str] = {}
    role_lookup: dict[str, str] = {}
    team_lookup: dict[str, str] = {}
    country_lookup: dict[str, str] = {}
    site_lookup: dict[str, str] = {}
    skill_lookup: dict[str, str] = {}
    topic_lookup: dict[str, str] = {}
    system_lookup: dict[str, str] = {}
    jd_lookup: dict[str, str] = {}
    dept_lookup: dict[str, str] = {}

    # JD nodes + role/department/required skill baseline
    for jd in jd_catalog["job_descriptions"]:
        rel_path = jd["relative_path"]
        identity = jd.get("identity", {})
        role_name = identity.get("Job Title") or jd["file_name"].replace(".docx", "")
        dept_name = identity.get("Department/Function")
        location = identity.get("Location (Site/Region/Group)") or identity.get("Location")
        reports_to = identity.get("Reports To (Role)") or identity.get("Reports To")
        role_level = identity.get("Role Level")

        jd_id = add_node(
            nodes,
            "JobDescription",
            rel_path,
            {
                "name": jd["file_name"].replace(".docx", ""),
                "relative_path": rel_path,
                "role_name": role_name,
                "department": dept_name,
                "location_context": location,
                "reports_to_context": reports_to,
                "role_level": role_level,
                "role_summary": jd.get("role_summary", ""),
            },
        )
        jd_lookup[rel_path] = jd_id

        role_id = add_node(nodes, "Role", role_name, {"name": role_name})
        role_lookup[role_name] = role_id
        add_rel(rels, role_id, "DESCRIBED_BY", jd_id)

        if dept_name:
            dept_id = add_node(nodes, "Department", dept_name, {"name": dept_name})
            dept_lookup[dept_name] = dept_id
            add_rel(rels, role_id, "BELONGS_TO_DEPARTMENT", dept_id)
            add_rel(rels, jd_id, "SCOPES_TO_DEPARTMENT", dept_id)

        site_name, country_name = split_country_from_location(location)
        if country_name:
            country_id = add_node(nodes, "Country", country_name, {"name": country_name})
            country_lookup[country_name] = country_id
            if site_name:
                site_id = add_node(nodes, "Site", site_name, {"name": site_name})
                site_lookup[site_name] = site_id
                add_rel(rels, site_id, "IN_COUNTRY", country_id)
                add_rel(rels, jd_id, "APPLIES_TO_SITE", site_id)
            add_rel(rels, jd_id, "APPLIES_TO_COUNTRY", country_id)

        for skill in jd.get("technical_and_business_knowledge", {}).get("technical_skills", []):
            skill_name = skill.strip()
            if not skill_name:
                continue
            skill_id = add_node(nodes, "Skill", skill_name, {"name": skill_name})
            skill_lookup[skill_name] = skill_id
            add_rel(rels, jd_id, "REQUIRES_SKILL", skill_id, {"source": "jd_baseline"})

    # Person nodes + person-specific relations
    for person in people_data["people"]:
        name = person["name"]
        person_id = add_node(
            nodes,
            "Person",
            name,
            {
                "name": name,
                "profile_type": person.get("profile_type"),
                "seniority": person.get("seniority"),
            },
        )
        person_lookup[name] = person_id

        jd_file = normalize_jd_reference(person.get("jd_file"))
        role_name = person.get("role") or person.get("role_from_jd")
        site_name = person.get("site")
        country_name = person.get("country")
        team_name = person.get("team")

        if jd_file:
            jd_id = jd_lookup.get(jd_file)
            if jd_id:
                add_rel(rels, person_id, "LINKED_TO_JD", jd_id)
                jd_role_name = person.get("role_from_jd") or jd_by_path.get(jd_file, {}).get("identity", {}).get("Job Title")
                if jd_role_name:
                    role_name = jd_role_name

                jd_location = person.get("location_from_jd") or jd_by_path.get(jd_file, {}).get("identity", {}).get("Location (Site/Region/Group)") or jd_by_path.get(jd_file, {}).get("identity", {}).get("Location")
                if not site_name or not country_name:
                    derived_site, derived_country = split_country_from_location(jd_location)
                    site_name = site_name or derived_site
                    country_name = country_name or derived_country

        if role_name:
            role_id = role_lookup.get(role_name) or add_node(nodes, "Role", role_name, {"name": role_name})
            role_lookup[role_name] = role_id
            add_rel(rels, person_id, "HAS_ROLE", role_id)

        if team_name:
            team_id = team_lookup.get(team_name) or add_node(nodes, "Team", team_name, {"name": team_name})
            team_lookup[team_name] = team_id
            add_rel(rels, person_id, "MEMBER_OF", team_id)

        if site_name:
            site_id = site_lookup.get(site_name) or add_node(nodes, "Site", site_name, {"name": site_name})
            site_lookup[site_name] = site_id
            add_rel(rels, person_id, "AT_SITE", site_id)

        if country_name:
            country_id = country_lookup.get(country_name) or add_node(nodes, "Country", country_name, {"name": country_name})
            country_lookup[country_name] = country_id
            add_rel(rels, person_id, "LOCATED_IN", country_id)
            if site_name:
                site_id = site_lookup[site_name]
                add_rel(rels, site_id, "IN_COUNTRY", country_id)

        for topic in person.get("primary_topics", []):
            topic_id = topic_lookup.get(topic) or add_node(nodes, "Topic", topic, {"name": topic})
            topic_lookup[topic] = topic_id
            add_rel(rels, person_id, "OWNS_TOPIC", topic_id)

        for skill in person.get("skills_person_specific", person.get("skills_explicit", [])):
            skill_id = skill_lookup.get(skill) or add_node(nodes, "Skill", skill, {"name": skill})
            skill_lookup[skill] = skill_id
            add_rel(rels, person_id, "HAS_SKILL", skill_id, {"source": "person_specific"})

        for system in person.get("systems_known", []):
            system_id = system_lookup.get(system) or add_node(nodes, "System", system, {"name": system})
            system_lookup[system] = system_id
            add_rel(rels, person_id, "KNOWS_SYSTEM", system_id)

    # Reporting lines second pass
    for person in people_data["people"]:
        manager_name = person.get("manager_name")
        if manager_name and person["name"] in person_lookup and manager_name in person_lookup:
            add_rel(rels, person_lookup[person["name"]], "REPORTS_TO", person_lookup[manager_name])

    # Deduplicate relationships
    unique_rels = []
    seen = set()
    for rel in rels:
        key = (
            rel["start"],
            rel["type"],
            rel["end"],
            tuple(sorted((k, str(v)) for k, v in rel.items() if k not in {"start", "type", "end"})),
        )
        if key not in seen:
            seen.add(key)
            unique_rels.append(rel)

    payload = {
        "meta": {
            "generated_from": [
                str(JD_CATALOG.relative_to(ROOT)).replace("\\", "/"),
                str(PERSON_RESOLVED.relative_to(ROOT)).replace("\\", "/"),
            ],
            "activity_sources_included": [],
            "graph_scope": "Enterprise knowledge graph for organizational structure, job descriptions, skills, topics, systems, and reporting relationships",
            "node_count": len(nodes),
            "relationship_count": len(unique_rels),
        },
        "nodes": sorted(nodes.values(), key=lambda x: (x["label"], x["id"])),
        "relationships": unique_rels,
    }
    save_json(OUTPUT_JSON, payload)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    grouped_nodes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in payload["nodes"]:
        grouped_nodes[node["label"]].append(node)

    for label, rows in grouped_nodes.items():
        fieldnames = sorted({key for row in rows for key in row.keys()})
        write_csv(OUTPUT_DIR / f"nodes_{label.lower()}.csv", rows, fieldnames)

    rel_fieldnames = sorted({key for row in unique_rels for key in row.keys()})
    write_csv(OUTPUT_DIR / "relationships.csv", unique_rels, rel_fieldnames)

    print(f"Wrote {OUTPUT_JSON}")
    print(f"Node types: {', '.join(sorted(grouped_nodes.keys()))}")
    print(f"Nodes: {len(nodes)}")
    print(f"Relationships: {len(unique_rels)}")


if __name__ == "__main__":
    main()
