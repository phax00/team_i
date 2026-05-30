import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PERSON_PROFILES = ROOT / "people" / "data" / "Person_Profiles_Lean.json"
OUTPUT = ROOT / "activity" / "jira" / "data" / "jira_synthetic.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_index(people: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {person["name"]: person for person in people}


def issue(
    project_key: str,
    number: int,
    issue_type: str,
    summary: str,
    description: str,
    status: str,
    priority: str,
    assignee_name: str,
    reporter_name: str,
    created_at: datetime,
    updated_at: datetime,
    labels: list[str],
    components: list[str],
    project_name: str,
    site: str,
    country: str,
    linked_systems: list[str],
    acceptance_criteria: list[str],
    comments: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "project_key": project_key,
        "issue_key": f"{project_key}-{number}",
        "issue_type": issue_type,
        "summary": summary,
        "description": description,
        "status": status,
        "priority": priority,
        "assignee_name": assignee_name,
        "reporter_name": reporter_name,
        "created_at": iso(created_at),
        "updated_at": iso(updated_at),
        "labels": labels,
        "components": components,
        "project_name": project_name,
        "site": site,
        "country": country,
        "linked_systems": linked_systems,
        "acceptance_criteria": acceptance_criteria,
        "comments": comments,
    }


def c(author_name: str, created_at: datetime, body: str) -> dict[str, str]:
    return {
        "author_name": author_name,
        "created_at": iso(created_at),
        "body": body,
    }


def main() -> None:
    data = load_json(PERSON_PROFILES)
    idx = build_index(data["people"])
    base = datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc)

    issues = [
        issue(
            "ERP",
            101,
            "Story",
            "Improve IFS purchase order approval flow",
            "Redesign the approval routing for high-value purchase orders, reduce manual rework, and improve approval visibility for Procurement and Finance users.",
            "Done",
            "High",
            "Erik Sykora",
            "Tomas Benes",
            base,
            base + timedelta(days=6, hours=4),
            ["ifs", "procurement", "workflow"],
            ["ERP", "Procurement"],
            "ERP Process Modernization",
            "Banska Bystrica",
            "Slovakia",
            ["IFS ERP"],
            [
                "Approval routing follows threshold rules",
                "Workflow states are visible to requestors",
                "Exception handling is logged"
            ],
            [
                c("Nina Havel", base + timedelta(days=1, hours=2), "Please keep the approval states aligned with the current ERP release constraints."),
                c("Marek Sramek", base + timedelta(days=3, hours=1), "Finance needs clear reporting on pending approvals above threshold.")
            ],
        ),
        issue(
            "ERP",
            102,
            "Task",
            "Stabilize ERP user issue triage for receiving and inventory teams",
            "Create a lightweight triage process for recurring ERP issues from warehouse and inventory users, including categorization, ownership, and escalation logic.",
            "In Progress",
            "Medium",
            "Erik Sykora",
            "Nina Havel",
            base + timedelta(days=2),
            base + timedelta(days=9, hours=3),
            ["ifs", "support", "inventory"],
            ["ERP", "Support"],
            "ERP Process Modernization",
            "Banska Bystrica",
            "Slovakia",
            ["IFS ERP"],
            [
                "Issue categories are defined",
                "Escalation path is documented",
                "Top recurring issues have clear owners"
            ],
            [
                c("Roman Kolar", base + timedelta(days=4, hours=5), "Please capture whether master data quality is part of the issue root cause.")
            ],
        ),
        issue(
            "APP",
            201,
            "Epic",
            "Prepare smart factory application rollout for packaging area",
            "Coordinate the rollout of smart factory applications for packaging performance visibility, operator workflow support, and line-level event capture.",
            "In Progress",
            "High",
            "Nina Havel",
            "Filip Hruby",
            base + timedelta(days=5),
            base + timedelta(days=20, hours=6),
            ["smart-factory", "packaging", "rollout"],
            ["Industrial IT", "Packaging"],
            "Smart Factory Enablement",
            "Banska Bystrica",
            "Slovakia",
            ["MES", "SCADA", "ERP"],
            [
                "Packaging pilot scope is agreed",
                "Key user training plan is ready",
                "Data flow to reporting is validated"
            ],
            [
                c("Jozef Polak", base + timedelta(days=7, hours=2), "The packaging area must stay stable during the rollout window."),
                c("Lucia Benesova", base + timedelta(days=8, hours=1), "Please include operator usability feedback before go-live.")
            ],
        ),
        issue(
            "APP",
            202,
            "Story",
            "Define application ownership matrix for plant-facing systems",
            "Clarify ownership for plant-facing applications, including support responsibility, enhancement intake, and release communication across IT and operations.",
            "Done",
            "Medium",
            "Nina Havel",
            "Filip Hruby",
            base + timedelta(days=10),
            base + timedelta(days=16, hours=2),
            ["governance", "applications", "ownership"],
            ["Industrial IT", "Governance"],
            "Smart Factory Enablement",
            "Banska Bystrica",
            "Slovakia",
            ["MES", "ERP", "shopfloor apps"],
            [
                "Each application has a named owner",
                "Support routing is documented",
                "Enhancement requests follow one intake path"
            ],
            [
                c("Eva Kralikova", base + timedelta(days=11, hours=4), "Please make sure plant leadership knows where escalations belong.")
            ],
        ),
        issue(
            "DATA",
            301,
            "Task",
            "Build executive sales dashboard for weekly reviews",
            "Create a dashboard for weekly sales, margin, and promotion performance reviews across Czech Republic, Slovakia, and Poland.",
            "In Progress",
            "High",
            "Barbora Klinec",
            "Marek Sramek",
            base + timedelta(days=3),
            base + timedelta(days=18, hours=1),
            ["powerbi", "sales", "dashboard"],
            ["Analytics", "Finance"],
            "Commercial Reporting Enablement",
            "Bratislava",
            "Slovakia",
            ["Power BI", "ERP"],
            [
                "Market drilldown is included",
                "Margin logic is aligned with Finance",
                "Dashboard refresh is automated"
            ],
            [
                c("David Mraz", base + timedelta(days=6, hours=2), "We should reuse the existing sales fact table instead of duplicating KPI logic."),
                c("Klara Novak", base + timedelta(days=12, hours=3), "Please add promotion performance by key customer group.")
            ],
        ),
        issue(
            "DATA",
            302,
            "Story",
            "Automate finance reporting data quality checks",
            "Add automated validation checks for finance reporting tables to reduce reconciliation effort and catch schema issues earlier in the pipeline.",
            "To Do",
            "High",
            "David Mraz",
            "Marek Sramek",
            base + timedelta(days=12),
            base + timedelta(days=12),
            ["etl", "finance", "data-quality"],
            ["Analytics", "Finance"],
            "Commercial Reporting Enablement",
            "Bratislava",
            "Slovakia",
            ["SQL Server", "BI data pipelines"],
            [
                "Validation checks cover key finance tables",
                "Failures are visible to the BI team",
                "Finance can review validation outcomes"
            ],
            [
                c("Barbora Klinec", base + timedelta(days=13, hours=1), "Let's align the validation rules with the KPI layer, not only the raw tables.")
            ],
        ),
        issue(
            "MDM",
            401,
            "Story",
            "Clean up supplier master ownership and approval flow",
            "Redesign supplier master data ownership and approval checkpoints so Procurement and Finance can resolve onboarding and change requests faster.",
            "In Progress",
            "High",
            "Roman Kolar",
            "Tomas Benes",
            base + timedelta(days=4),
            base + timedelta(days=17, hours=5),
            ["master-data", "supplier", "governance"],
            ["Data Governance", "Procurement"],
            "Master Data Reliability",
            "Bratislava",
            "Slovakia",
            ["ERP", "MDM workflows"],
            [
                "Supplier ownership model is agreed",
                "Approval checkpoints are documented",
                "Priority change requests can be tracked"
            ],
            [
                c("Erik Sykora", base + timedelta(days=7, hours=4), "Please note which issues are ERP configuration versus pure ownership ambiguity."),
                c("Marek Sramek", base + timedelta(days=9, hours=2), "Finance needs clarity on payment-critical supplier attributes.")
            ],
        ),
        issue(
            "MDM",
            402,
            "Task",
            "Review item master quality for planning-critical SKUs",
            "Analyze recurring planning disruptions caused by incomplete or inconsistent item master data and define the first remediation wave.",
            "Done",
            "Medium",
            "Roman Kolar",
            "Veronika Duda",
            base + timedelta(days=7),
            base + timedelta(days=13, hours=6),
            ["master-data", "planning", "item-master"],
            ["Data Governance", "Supply Chain"],
            "Master Data Reliability",
            "Bratislava",
            "Slovakia",
            ["ERP", "planning tools"],
            [
                "Priority SKU list is reviewed",
                "Critical gaps are categorized",
                "Remediation ownership is assigned"
            ],
            [
                c("Martin Pospisil", base + timedelta(days=10, hours=3), "Please prioritize items that drive the largest schedule instability.")
            ],
        ),
        issue(
            "ENG",
            501,
            "Bug",
            "Reduce recurring line stoppages on tofu packaging line",
            "Investigate repeated stoppages on the packaging line, identify the root cause, and implement technical changes to improve uptime.",
            "To Do",
            "Highest",
            "Lucia Benesova",
            "Michal Hronec",
            base + timedelta(days=1),
            base + timedelta(days=1),
            ["packaging", "uptime", "root-cause"],
            ["Engineering", "Production"],
            "Packaging Stability Improvement",
            "Banska Bystrica",
            "Slovakia",
            ["maintenance planning", "engineering documentation"],
            [
                "Root cause is documented",
                "Countermeasure is implemented",
                "Downtime recurrence decreases over the next two weeks"
            ],
            [
                c("Andrej Varga", base + timedelta(days=2, hours=1), "We should compare events before and after the last changeover adjustment.")
            ],
        ),
        issue(
            "ENG",
            502,
            "Story",
            "Standardize engineering change handover after line modifications",
            "Create a cleaner handover process after engineering changes so Production, Quality, and Maintenance have the right documentation and follow-up actions.",
            "In Progress",
            "Medium",
            "Lucia Benesova",
            "Michal Hronec",
            base + timedelta(days=9),
            base + timedelta(days=21, hours=2),
            ["engineering-change", "handover", "documentation"],
            ["Engineering", "Governance"],
            "Packaging Stability Improvement",
            "Banska Bystrica",
            "Slovakia",
            ["engineering documentation"],
            [
                "Handover checklist is defined",
                "Required documentation is standardized",
                "Quality and Production sign-off is included"
            ],
            [
                c("Katarina Urban", base + timedelta(days=12, hours=2), "Please include a quality verification step for process-affecting changes."),
                c("Jozef Polak", base + timedelta(days=14, hours=4), "The handover cannot slow down urgent plant modifications too much.")
            ],
        ),
        issue(
            "ENG",
            503,
            "Task",
            "Validate process settings for new packaging material trial",
            "Support the packaging trial by validating line settings, documenting observed issues, and recommending adjustments before the next run.",
            "Done",
            "Medium",
            "Andrej Varga",
            "Lucia Benesova",
            base + timedelta(days=15),
            base + timedelta(days=19, hours=5),
            ["trial", "validation", "packaging"],
            ["Engineering", "Production"],
            "Packaging Stability Improvement",
            "Banska Bystrica",
            "Slovakia",
            ["process tracking", "automation interfaces"],
            [
                "Trial settings are documented",
                "Observed issues are categorized",
                "Recommended next-step adjustments are defined"
            ],
            [
                c("Michal Hronec", base + timedelta(days=16, hours=3), "Please compare the trial output to baseline stability, not only output speed.")
            ],
        ),
        issue(
            "SCM",
            601,
            "Story",
            "Stabilize weekly production planning freeze window",
            "Introduce a more disciplined weekly planning freeze window to reduce late production changes and improve execution stability across planning and plant teams.",
            "In Progress",
            "High",
            "Veronika Duda",
            "Martin Pospisil",
            base + timedelta(days=6),
            base + timedelta(days=18, hours=6),
            ["planning", "freeze-window", "schedule"],
            ["Supply Chain", "Production Planning"],
            "Planning Maturity Improvement",
            "Banska Bystrica",
            "Slovakia",
            ["planning tools", "ERP"],
            [
                "Freeze window policy is defined",
                "Escalation path for urgent changes is documented",
                "Schedule adherence impact can be tracked"
            ],
            [
                c("Jozef Polak", base + timedelta(days=8, hours=3), "We need a practical exception path for true production emergencies."),
                c("Klara Novak", base + timedelta(days=10, hours=1), "Commercial needs clarity on which late requests can still be accepted.")
            ],
        ),
        issue(
            "SCM",
            602,
            "Task",
            "Review service-risk items before Poland promotion wave",
            "Coordinate a pre-promotion planning review for items with elevated supply risk ahead of the Poland modern trade promotional period.",
            "To Do",
            "High",
            "Veronika Duda",
            "Marta Zielinska",
            base + timedelta(days=18),
            base + timedelta(days=18),
            ["promotion", "planning", "service-risk"],
            ["Supply Chain", "Commercial"],
            "Planning Maturity Improvement",
            "Banska Bystrica",
            "Slovakia",
            ["planning tools", "ERP"],
            [
                "Risk item list is agreed",
                "Escalation owners are defined",
                "Commercial receives a clear risk summary"
            ],
            [
                c("Martin Pospisil", base + timedelta(days=19, hours=2), "Please focus on items with both constrained capacity and high promotional sensitivity.")
            ],
        ),
        issue(
            "RND",
            701,
            "Story",
            "Improve launch readiness review for new product introduction",
            "Strengthen the launch readiness review process so R&D, Quality, Operations, and Marketing align earlier on technical, packaging, and execution constraints.",
            "In Progress",
            "Medium",
            "Saskia de Vries",
            "Julia Hartmann",
            base + timedelta(days=11),
            base + timedelta(days=24, hours=4),
            ["launch", "innovation", "readiness"],
            ["R&D", "Marketing"],
            "Innovation Delivery Discipline",
            "Landgraaf",
            "Netherlands",
            ["innovation portfolio tracking", "product lifecycle files"],
            [
                "Review inputs are standardized",
                "Cross-functional sign-off criteria are documented",
                "Launch blockers are escalated earlier"
            ],
            [
                c("Katarina Urban", base + timedelta(days=13, hours=5), "Quality needs visibility before final launch packaging decisions are locked."),
                c("Eva Kralikova", base + timedelta(days=15, hours=2), "Operations should only join the review when actionable decisions are needed.")
            ],
        ),
        issue(
            "MKT",
            801,
            "Task",
            "Localize central campaign assets for Romania summer activation",
            "Adapt central brand assets and campaign messaging for the Romania summer retail activation and align execution timing with local commercial needs.",
            "Done",
            "Medium",
            "Andreea Popescu",
            "Julia Hartmann",
            base + timedelta(days=14),
            base + timedelta(days=20, hours=3),
            ["campaign", "localization", "romania"],
            ["Marketing", "Commercial"],
            "Local Market Activation",
            "Bucharest",
            "Romania",
            ["campaign calendars", "asset libraries"],
            [
                "Core assets are localized",
                "Retail timing is aligned with local teams",
                "Market-specific messaging is approved"
            ],
            [
                c("Radu Ionescu", base + timedelta(days=16, hours=1), "Please keep the messaging useful for retail activation, not just brand consistency."),
                c("Klara Novak", base + timedelta(days=17, hours=2), "A short summary of retail-facing differences would help other markets too.")
            ],
        ),
        issue(
            "SALES",
            901,
            "Story",
            "Prepare account growth plan for Czech key retail customer",
            "Build a customer growth plan combining pricing, assortment, promotion timing, and service risk assumptions for a major Czech retail account.",
            "In Progress",
            "Medium",
            "Klara Novak",
            "Daniel Richter",
            base + timedelta(days=17),
            base + timedelta(days=25, hours=5),
            ["account-plan", "czech-market", "retail"],
            ["Commercial", "Sales"],
            "Account Planning Excellence",
            "Brno",
            "Czech Republic",
            ["CRM", "sales dashboards"],
            [
                "Growth assumptions are documented",
                "Promotion timing is aligned",
                "Service risks are visible to the customer team"
            ],
            [
                c("Veronika Duda", base + timedelta(days=19, hours=1), "We need better visibility on customer requests that break the planning freeze window."),
                c("Julia Hartmann", base + timedelta(days=21, hours=4), "Please connect this with the next central campaign timing.")
            ],
        ),
    ]

    payload = {
        "meta": {
            "generated_at": iso(datetime.now(timezone.utc)),
            "source": "synthetic_jira",
            "project_keys": sorted({item["project_key"] for item in issues}),
            "linked_to_person_profiles": str(PERSON_PROFILES.relative_to(ROOT)).replace("\\", "/"),
            "note": "Synthetic Jira data for school MVP only. Designed to align with JD-backed employees and topics."
        },
        "issues": issues,
    }

    save_json(OUTPUT, payload)
    print(f"Wrote {OUTPUT}")
    print(f"Issues: {len(issues)}")


if __name__ == "__main__":
    main()
