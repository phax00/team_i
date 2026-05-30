import json
from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parents[2]
INPUT_SETS = [
    ROOT / "job_descriptions" / "source_docs" / "Job Descriptions",
    ROOT / "job_descriptions" / "generated_final" / "Generated Job Descriptions Final",
]
OUTPUT_FILE = ROOT / "job_descriptions" / "catalog" / "JD_Catalog.json"


SECTION_KEYS = [
    "A. Job Identity",
    "B. Role Summary (Scope and Impact)",
    "C. Key Responsibilities",
    "D. Organizational Scope",
    "E. Reporting Relationships",
    "F. Key Contacts and Communication",
    "G. Contribution to Innovation and Change - Examples",
    "G. Contribution to Innovation and Change — Examples",
    "H. Qualifications",
    "I. Technical & Business Knowledge",
    "J. Competencies & Personal Attributes",
    "K. Problem Solving & Decision Complexity - Examples",
    "K. Problem Solving & Decision Complexity — Examples",
    "L. Environment & Risk",
]


def clean_lines(doc_path: Path) -> list[str]:
    doc = Document(doc_path)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


def split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = None
    for line in lines:
        if line in SECTION_KEYS:
            current = line
            sections[current] = []
            continue
        if current:
            sections[current].append(line)
    return sections


def parse_label_value(line: str) -> tuple[str, str] | None:
    if ":" not in line:
        return None
    label, value = line.split(":", 1)
    return label.strip(), value.strip()


def collect_label_block(lines: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in lines:
        parsed = parse_label_value(line)
        if parsed:
            label, value = parsed
            out[label] = value
    return out


def parse_identity(section_lines: list[str]) -> dict[str, str]:
    return collect_label_block(section_lines)


def parse_role_summary(section_lines: list[str]) -> str:
    return " ".join(section_lines).strip()


def parse_key_responsibilities(section_lines: list[str]) -> list[dict[str, str]]:
    items = []
    for line in section_lines:
        parsed = parse_label_value(line)
        if parsed:
            label, value = parsed
            items.append({"title": label, "description": value})
        else:
            items.append({"title": "", "description": line})
    return items


def parse_technical(section_lines: list[str]) -> dict[str, object]:
    technical_skills: list[str] = []
    business_knowledge = ""
    collecting_skills = False
    for line in section_lines:
        if line == "Technical Skills:":
            collecting_skills = True
            continue
        parsed = parse_label_value(line)
        if parsed and parsed[0] == "Business Knowledge Required":
            business_knowledge = parsed[1]
            collecting_skills = False
            continue
        if collecting_skills:
            technical_skills.append(line)
    return {
        "technical_skills": technical_skills,
        "business_knowledge_required": business_knowledge,
    }


def parse_doc(doc_path: Path) -> dict[str, object]:
    lines = clean_lines(doc_path)
    sections = split_sections(lines)

    if "A. Job Identity" not in sections:
        raise ValueError("Document does not match JD structure")

    tech_section = sections.get("I. Technical & Business Knowledge", [])
    role_summary_section = sections.get("B. Role Summary (Scope and Impact)", [])
    key_resp_section = sections.get("C. Key Responsibilities", [])
    identity_section = sections.get("A. Job Identity", [])
    org_scope_section = sections.get("D. Organizational Scope", [])
    reporting_section = sections.get("E. Reporting Relationships", [])

    catalog_item = {
        "file_name": doc_path.name,
        "relative_path": str(doc_path.relative_to(ROOT)).replace("\\", "/"),
        "identity": parse_identity(identity_section),
        "role_summary": parse_role_summary(role_summary_section),
        "key_responsibilities": parse_key_responsibilities(key_resp_section),
        "organizational_scope": collect_label_block(org_scope_section),
        "reporting_relationships": collect_label_block(reporting_section),
        "technical_and_business_knowledge": parse_technical(tech_section),
    }
    return catalog_item


def main() -> None:
    catalog: list[dict[str, object]] = []
    for folder in INPUT_SETS:
        if not folder.exists():
            continue
        for doc_path in sorted(folder.glob("*.docx")):
            try:
                catalog.append(parse_doc(doc_path))
            except ValueError:
                continue

    output = {
        "meta": {
            "source_folders": [str(p.relative_to(ROOT)).replace("\\", "/") for p in INPUT_SETS if p.exists()],
            "document_count": len(catalog),
            "note": "This catalog is extracted directly from the Word job descriptions and should be treated as the baseline role/JD source of truth."
        },
        "job_descriptions": catalog,
    }
    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE}")
    print(f"Documents: {len(catalog)}")


if __name__ == "__main__":
    main()
