import json
import re
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CORE_GRAPH = ROOT / "graphs" / "core" / "knowledge_graph_core.json"
GITHUB_MAPPED = ROOT / "activity" / "github" / "data" / "github_activity_mapped.json"
JIRA_SYNTHETIC = ROOT / "activity" / "jira" / "data" / "jira_synthetic.json"
OUTPUT_JSON = ROOT / "graphs" / "school_mvp" / "knowledge_graph_school_mvp.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def add_node(store: dict[str, dict[str, Any]], node_type: str, key: str, props: dict[str, Any]) -> str:
    node_id = f"{node_type}:{slugify(key)}"
    if node_id not in store:
        store[node_id] = {"id": node_id, "label": node_type, **props}
    else:
        for prop_key, prop_value in props.items():
            if prop_value not in (None, "", []):
                store[node_id][prop_key] = prop_value
    return node_id


def add_rel(rels: list[dict[str, Any]], start: str, rel_type: str, end: str, props: dict[str, Any] | None = None) -> None:
    rel = {"start": start, "type": rel_type, "end": end}
    if props:
        rel.update(props)
    rels.append(rel)


def sample_commits(commits: list[dict[str, Any]], max_per_person_repo: int = 2) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for commit in commits:
        person = commit.get("synthetic_employee_name")
        if not person:
            continue
        grouped[(person, commit["repo"])].append(commit)

    selected: list[dict[str, Any]] = []
    for key in sorted(grouped):
        selected.extend(grouped[key][:max_per_person_repo])
    return selected


def sample_pull_requests(prs: list[dict[str, Any]], max_per_person_repo: int = 1) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for pr in prs:
        person = pr.get("synthetic_employee_name")
        if not person:
            continue
        grouped[(person, pr["repo"])].append(pr)

    selected: list[dict[str, Any]] = []
    for key in sorted(grouped):
        selected.extend(grouped[key][:max_per_person_repo])
    return selected


def ensure_skill(nodes: dict[str, dict[str, Any]], skill_name: str) -> str:
    return add_node(nodes, "Skill", skill_name, {"name": skill_name})


def ensure_topic(nodes: dict[str, dict[str, Any]], topic_name: str) -> str:
    return add_node(nodes, "Topic", topic_name, {"name": topic_name})


def ensure_system(nodes: dict[str, dict[str, Any]], system_name: str) -> str:
    return add_node(nodes, "System", system_name, {"name": system_name})


def repo_skill_hints(repo: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    language = repo.get("language")
    if language:
        hints.append(language)

    topic_map = {
        "fastapi": "FastAPI",
        "python": "Python",
        "airflow": "Apache Airflow",
        "dbt": "dbt",
        "api": "API design",
        "analytics": "Analytics engineering",
        "orchestration": "Workflow orchestration",
        "data-pipeline": "Data pipelines",
    }
    for topic in repo.get("topics", []):
        normalized = topic.lower()
        if normalized in topic_map:
            hints.append(topic_map[normalized])
    return sorted(set(hints))


def main() -> None:
    core = load_json(CORE_GRAPH)
    github_data = load_json(GITHUB_MAPPED)
    jira_data = load_json(JIRA_SYNTHETIC)

    nodes = {node["id"]: deepcopy(node) for node in core["nodes"]}
    rels = [deepcopy(rel) for rel in core["relationships"]]

    person_id_by_name = {
        node["name"]: node["id"]
        for node in nodes.values()
        if node["label"] == "Person"
    }

    repository_ids: dict[str, str] = {}
    project_ids: dict[str, str] = {}

    for repo in github_data["repositories"]:
        repo_id = add_node(
            nodes,
            "Repository",
            repo["repo"],
            {
                "name": repo["repo"],
                "description": repo.get("description"),
                "language": repo.get("language"),
                "html_url": repo.get("html_url"),
                "topics": repo.get("topics", []),
                "stars": repo.get("stargazers_count"),
                "forks": repo.get("forks_count"),
                "activity_source": "github_public",
            },
        )
        repository_ids[repo["repo"]] = repo_id

        for skill_name in repo_skill_hints(repo):
            skill_id = ensure_skill(nodes, skill_name)
            add_rel(rels, repo_id, "USES_TECHNOLOGY", skill_id, {"source": "repo_metadata"})

        repo_contributors = {
            mapping["synthetic_employee_name"]
            for mapping in github_data.get("mappings_used", [])
            if mapping.get("mapping_status") == "assigned"
            and mapping.get("synthetic_employee_name")
            and repo["repo"] in mapping.get("repos_contributed_to", [])
        }
        for person_name in sorted(repo_contributors):
            person_id = person_id_by_name.get(person_name)
            if person_id:
                add_rel(rels, person_id, "CONTRIBUTED_TO_REPOSITORY", repo_id, {"source": "github_public"})

        for commit in sample_commits(repo.get("commits", [])):
            person_name = commit.get("synthetic_employee_name")
            person_id = person_id_by_name.get(person_name)
            if not person_id:
                continue

            commit_id = add_node(
                nodes,
                "Commit",
                commit["sha"],
                {
                    "name": f"{repo['name']} commit {commit['sha'][:7]}",
                    "message_headline": commit.get("message_headline"),
                    "authored_at": commit.get("authored_at"),
                    "html_url": commit.get("html_url"),
                    "total_changes": commit.get("total_changes"),
                    "changed_files": commit.get("changed_files"),
                    "activity_source": "github_public",
                },
            )
            add_rel(rels, person_id, "AUTHORED_COMMIT", commit_id, {"source": "github_public"})
            add_rel(rels, commit_id, "IN_REPOSITORY", repo_id, {"source": "github_public"})

            for skill_name in repo_skill_hints(repo):
                skill_id = ensure_skill(nodes, skill_name)
                add_rel(rels, commit_id, "EVIDENCES_SKILL", skill_id, {"source": "repo_metadata"})
                add_rel(rels, person_id, "HAS_SKILL", skill_id, {"source": "github_activity"})

        for pr in sample_pull_requests(repo.get("pull_requests", [])):
            person_name = pr.get("synthetic_employee_name")
            person_id = person_id_by_name.get(person_name)
            if not person_id:
                continue

            pr_id = add_node(
                nodes,
                "PullRequest",
                f"{repo['repo']}#{pr['number']}",
                {
                    "name": f"{repo['name']} PR #{pr['number']}",
                    "title": pr.get("title"),
                    "state": pr.get("state"),
                    "is_merged": pr.get("is_merged"),
                    "html_url": pr.get("html_url"),
                    "created_at": pr.get("created_at"),
                    "updated_at": pr.get("updated_at"),
                    "activity_source": "github_public",
                },
            )
            add_rel(rels, person_id, "OPENED_PULL_REQUEST", pr_id, {"source": "github_public"})
            add_rel(rels, pr_id, "IN_REPOSITORY", repo_id, {"source": "github_public"})

            for skill_name in repo_skill_hints(repo):
                skill_id = ensure_skill(nodes, skill_name)
                add_rel(rels, pr_id, "EVIDENCES_SKILL", skill_id, {"source": "repo_metadata"})

    for issue in jira_data["issues"]:
        issue_id = add_node(
            nodes,
            "JiraIssue",
            issue["issue_key"],
            {
                "name": issue["issue_key"],
                "summary": issue.get("summary"),
                "issue_type": issue.get("issue_type"),
                "status": issue.get("status"),
                "priority": issue.get("priority"),
                "project_key": issue.get("project_key"),
                "project_name": issue.get("project_name"),
                "site": issue.get("site"),
                "country": issue.get("country"),
                "activity_source": "jira_synthetic",
            },
        )

        project_name = issue.get("project_name") or issue.get("project_key")
        project_id = project_ids.get(project_name)
        if not project_id:
            project_id = add_node(
                nodes,
                "Project",
                project_name,
                {
                    "name": project_name,
                    "project_key": issue.get("project_key"),
                    "activity_source": "jira_synthetic",
                },
            )
            project_ids[project_name] = project_id
        add_rel(rels, issue_id, "BELONGS_TO_PROJECT", project_id, {"source": "jira_synthetic"})

        assignee_id = person_id_by_name.get(issue.get("assignee_name"))
        if assignee_id:
            add_rel(rels, assignee_id, "WORKED_ON_TICKET", issue_id, {"source": "jira_synthetic"})

        reporter_id = person_id_by_name.get(issue.get("reporter_name"))
        if reporter_id:
            add_rel(rels, reporter_id, "REPORTED_TICKET", issue_id, {"source": "jira_synthetic"})

        if issue.get("site"):
            site_id = add_node(nodes, "Site", issue["site"], {"name": issue["site"]})
            add_rel(rels, issue_id, "AT_SITE", site_id, {"source": "jira_synthetic"})

        if issue.get("country"):
            country_id = add_node(nodes, "Country", issue["country"], {"name": issue["country"]})
            add_rel(rels, issue_id, "LOCATED_IN", country_id, {"source": "jira_synthetic"})

        for system_name in issue.get("linked_systems", []):
            system_id = ensure_system(nodes, system_name)
            add_rel(rels, issue_id, "IMPACTS_SYSTEM", system_id, {"source": "jira_synthetic"})

        for label in issue.get("labels", []):
            topic_id = ensure_topic(nodes, label)
            add_rel(rels, issue_id, "TAGGED_WITH_TOPIC", topic_id, {"source": "jira_synthetic"})

        for component in issue.get("components", []):
            skill_id = ensure_skill(nodes, component)
            add_rel(rels, issue_id, "REQUIRES_SKILL", skill_id, {"source": "jira_synthetic"})

        for comment in issue.get("comments", []):
            commenter_id = person_id_by_name.get(comment.get("author_name"))
            if commenter_id:
                add_rel(rels, commenter_id, "COMMENTED_ON_TICKET", issue_id, {"source": "jira_synthetic"})

    unique_rels: list[dict[str, Any]] = []
    seen = set()
    for rel in rels:
        key = (
            rel["start"],
            rel["type"],
            rel["end"],
            tuple(sorted((k, json.dumps(v, ensure_ascii=False, sort_keys=True)) for k, v in rel.items() if k not in {"start", "type", "end"})),
        )
        if key not in seen:
            seen.add(key)
            unique_rels.append(rel)

    payload = {
        "meta": {
            "generated_from": [
                str(CORE_GRAPH.relative_to(ROOT)).replace("\\", "/"),
                str(GITHUB_MAPPED.relative_to(ROOT)).replace("\\", "/"),
                str(JIRA_SYNTHETIC.relative_to(ROOT)).replace("\\", "/"),
            ],
            "activity_sources_included": ["GitHub public activity", "Synthetic Jira"],
            "graph_scope": "Expanded enterprise knowledge graph with organizational context, job descriptions, skills, topics, systems, engineering activity, and project work evidence",
            "node_count": len(nodes),
            "relationship_count": len(unique_rels),
        },
        "nodes": sorted(nodes.values(), key=lambda item: (item["label"], item["id"])),
        "relationships": unique_rels,
    }
    save_json(OUTPUT_JSON, payload)
    print(f"Wrote {OUTPUT_JSON}")
    print(f"Nodes: {len(nodes)}")
    print(f"Relationships: {len(unique_rels)}")


if __name__ == "__main__":
    main()
