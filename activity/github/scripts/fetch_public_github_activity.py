import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "activity" / "github" / "config" / "github_repos_config.json"
DEFAULT_OUTPUT = ROOT / "activity" / "github" / "data" / "github_activity.json"
GITHUB_API = "https://api.github.com"
DEFAULT_ENV_FILE = ROOT / ".env"


def load_dotenv_file(env_path: Path = DEFAULT_ENV_FILE) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "enterprise-knowledge-graph-mvp",
    }
    token = os.getenv("GITHUB_TOKEN") or os.getenv("github_token") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_get(path: str, params: dict[str, Any] | None = None, pause_s: float = 0.2) -> Any:
    if params:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{GITHUB_API}{path}?{query}"
    else:
        url = f"{GITHUB_API}{path}"

    req = urllib.request.Request(url, headers=build_headers(), method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            time.sleep(pause_s)
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API error {e.code} for {url}\n{body}") from e


def commit_headline(message: str) -> str:
    return message.splitlines()[0].strip() if message else ""


def normalize_commit(repo: str, item: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    commit_info = detail.get("commit", {})
    author = detail.get("author") or {}
    stats = detail.get("stats") or {}
    files = detail.get("files") or []

    return {
        "repo": repo,
        "sha": detail.get("sha"),
        "html_url": detail.get("html_url"),
        "api_url": detail.get("url"),
        "message": commit_info.get("message", ""),
        "message_headline": commit_headline(commit_info.get("message", "")),
        "author_login": author.get("login"),
        "author_user_id": author.get("id"),
        "commit_author_name": (commit_info.get("author") or {}).get("name"),
        "commit_author_email": (commit_info.get("author") or {}).get("email"),
        "authored_at": (commit_info.get("author") or {}).get("date"),
        "additions": stats.get("additions"),
        "deletions": stats.get("deletions"),
        "total_changes": stats.get("total"),
        "changed_files": len(files),
        "files": [
            {
                "filename": f.get("filename"),
                "status": f.get("status"),
                "additions": f.get("additions"),
                "deletions": f.get("deletions"),
                "changes": f.get("changes"),
            }
            for f in files
        ],
    }


def normalize_pr(repo: str, pr: dict[str, Any], pr_commits: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "repo": repo,
        "number": pr.get("number"),
        "title": pr.get("title"),
        "state": pr.get("state"),
        "is_merged": pr.get("merged_at") is not None,
        "html_url": pr.get("html_url"),
        "user_login": (pr.get("user") or {}).get("login"),
        "user_id": (pr.get("user") or {}).get("id"),
        "created_at": pr.get("created_at"),
        "updated_at": pr.get("updated_at"),
        "closed_at": pr.get("closed_at"),
        "merged_at": pr.get("merged_at"),
        "body": pr.get("body") or "",
        "labels": [label.get("name") for label in pr.get("labels", []) if label.get("name")],
        "requested_reviewers": [
            reviewer.get("login")
            for reviewer in pr.get("requested_reviewers", [])
            if reviewer.get("login")
        ],
        "linked_commit_shas": [c.get("sha") for c in pr_commits if c.get("sha")],
    }


def fetch_repo_bundle(
    repo: str,
    contributors_limit: int,
    commits_limit: int,
    prs_limit: int,
    pr_commits_limit: int,
    since: str | None,
) -> dict[str, Any]:
    owner, name = repo.split("/", 1)

    repo_meta = github_get(f"/repos/{owner}/{name}")
    contributors = github_get(
        f"/repos/{owner}/{name}/contributors",
        {"per_page": contributors_limit},
    )
    commits = github_get(
        f"/repos/{owner}/{name}/commits",
        {"per_page": commits_limit, "since": since},
    )
    pulls = github_get(
        f"/repos/{owner}/{name}/pulls",
        {"state": "all", "sort": "updated", "direction": "desc", "per_page": prs_limit},
    )

    commit_items = []
    for commit in commits:
        sha = commit.get("sha")
        if not sha:
            continue
        detail = github_get(f"/repos/{owner}/{name}/commits/{sha}")
        commit_items.append(normalize_commit(repo, commit, detail))

    pr_items = []
    for pr in pulls:
        pr_number = pr.get("number")
        if pr_number is None:
            continue
        pr_commits = github_get(
            f"/repos/{owner}/{name}/pulls/{pr_number}/commits",
            {"per_page": pr_commits_limit},
        )
        pr_items.append(normalize_pr(repo, pr, pr_commits))

    return {
        "repo": repo,
        "repo_id": repo_meta.get("id"),
        "name": repo_meta.get("name"),
        "owner": (repo_meta.get("owner") or {}).get("login"),
        "description": repo_meta.get("description"),
        "html_url": repo_meta.get("html_url"),
        "language": repo_meta.get("language"),
        "topics": repo_meta.get("topics", []),
        "stargazers_count": repo_meta.get("stargazers_count"),
        "forks_count": repo_meta.get("forks_count"),
        "contributors": [
            {
                "source_login": c.get("login"),
                "source_user_id": c.get("id"),
                "html_url": c.get("html_url"),
                "contributions": c.get("contributions"),
            }
            for c in contributors
        ],
        "commits": commit_items,
        "pull_requests": pr_items,
    }


def source_identity_rollup(repositories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rollup: dict[tuple[Any, Any], dict[str, Any]] = defaultdict(
        lambda: {
            "source_login": None,
            "source_user_id": None,
            "source_display_name": None,
            "repos_contributed_to": set(),
            "commit_count": 0,
            "pull_request_count": 0,
        }
    )

    for repo_item in repositories:
        repo_name = repo_item["repo"]

        for commit in repo_item["commits"]:
            key = (commit.get("author_login"), commit.get("author_user_id"))
            bucket = rollup[key]
            bucket["source_login"] = commit.get("author_login")
            bucket["source_user_id"] = commit.get("author_user_id")
            bucket["source_display_name"] = commit.get("commit_author_name")
            bucket["repos_contributed_to"].add(repo_name)
            bucket["commit_count"] += 1

        for pr in repo_item["pull_requests"]:
            key = (pr.get("user_login"), pr.get("user_id"))
            bucket = rollup[key]
            bucket["source_login"] = pr.get("user_login")
            bucket["source_user_id"] = pr.get("user_id")
            if not bucket["source_display_name"]:
                bucket["source_display_name"] = pr.get("user_login")
            bucket["repos_contributed_to"].add(repo_name)
            bucket["pull_request_count"] += 1

    out = []
    for bucket in rollup.values():
        bucket["repos_contributed_to"] = sorted(bucket["repos_contributed_to"])
        out.append(bucket)

    out.sort(key=lambda x: (-(x["commit_count"] + x["pull_request_count"]), str(x["source_login"])))
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch normalized public GitHub activity for MVP enrichment.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to JSON config with repos and limits.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path.")
    parser.add_argument("--repos", nargs="*", help="Optional repo overrides in owner/name format.")
    parser.add_argument("--since", default=None, help="Optional ISO datetime filter for commits, e.g. 2025-01-01T00:00:00Z")
    parser.add_argument("--contributors-per-repo", type=int, default=None)
    parser.add_argument("--commits-per-repo", type=int, default=None)
    parser.add_argument("--pull-requests-per-repo", type=int, default=None)
    parser.add_argument("--pr-commits-per-pr", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    load_dotenv_file()
    args = parse_args()
    config = load_json(args.config) if args.config.exists() else {}

    repos = args.repos or config.get("repos") or []
    if not repos:
        raise SystemExit("No repositories provided. Use --repos or github_repos_config.json.")

    limits = config.get("limits", {})
    contributors_limit = args.contributors_per_repo or limits.get("contributors_per_repo", 20)
    commits_limit = args.commits_per_repo or limits.get("commits_per_repo", 30)
    prs_limit = args.pull_requests_per_repo or limits.get("pull_requests_per_repo", 15)
    pr_commits_limit = args.pr_commits_per_pr or limits.get("pr_commits_per_pr", 10)
    since = args.since if args.since is not None else config.get("since")

    repositories = []
    for repo in repos:
        print(f"Fetching {repo}...", file=sys.stderr)
        repositories.append(
            fetch_repo_bundle(
                repo=repo,
                contributors_limit=contributors_limit,
                commits_limit=commits_limit,
                prs_limit=prs_limit,
                pr_commits_limit=pr_commits_limit,
                since=since,
            )
        )

    payload = {
        "meta": {
            "generated_at": now_utc(),
            "source": "github_rest_api",
            "authenticated": bool(os.getenv("GITHUB_TOKEN") or os.getenv("github_token") or os.getenv("GH_TOKEN")),
            "repos_requested": repos,
            "limits": {
                "contributors_per_repo": contributors_limit,
                "commits_per_repo": commits_limit,
                "pull_requests_per_repo": prs_limit,
                "pr_commits_per_pr": pr_commits_limit,
            },
            "since": since,
            "note": "Public GitHub activity only. Use a separate mapping step to assign source identities to synthetic employees."
        },
        "repositories": repositories,
        "source_identities": source_identity_rollup(repositories),
    }

    save_json(args.out, payload)
    print(f"Wrote {args.out}")
    print(f"Repositories: {len(repositories)}")
    print(f"Source identities: {len(payload['source_identities'])}")


if __name__ == "__main__":
    main()
