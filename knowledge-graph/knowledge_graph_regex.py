from pathlib import Path
from docx import Document
import re
import json


from tkinter import Tk, filedialog


# =========================================================
# CONFIG
# =========================================================

# Folder where your DOCX files are stored

root = Tk()
root.withdraw()

BASE_DIR = filedialog.askdirectory(title="Vyber složku")

# =========================================================
# READ DOCX
# =========================================================

def read_docx(path):

    doc = Document(path)

    paragraphs = []

    for p in doc.paragraphs:

        text = p.text.strip()

        if text:
            paragraphs.append(text)

    return "\n".join(paragraphs)

# =========================================================
# SPLIT DOCUMENT INTO SECTIONS
# =========================================================

def split_sections(text):

    """
    Splits document into:
    A. Job Identity
    B. Role Summary
    C. Key Responsibilities
    ...
    """

    pattern = r"\n([A-L]\.\s.+?)\n"

    matches = list(re.finditer(pattern, text))

    sections = {}

    for i, match in enumerate(matches):

        section_name = match.group(1).strip()

        start = match.end()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        content = text[start:end].strip()

        sections[section_name] = content

    return sections

# =========================================================
# EXTRACT SINGLE FIELD
# =========================================================

def extract_field(text, field_name):

    """
    Example:
    Job Title: IT Director
    """

    pattern = rf"{re.escape(field_name)}.*?:\s*(.+)"

    match = re.search(pattern, text)

    if match:
        return match.group(1).strip()

    return None

# =========================================================
# EXTRACT BULLET POINTS
# =========================================================

def extract_bullets(text):

    bullets = []

    lines = text.split("\n")

    for line in lines:

        line = line.strip()

        if (
            line.startswith("·")
            or line.startswith("-")
            or line.startswith("•")
        ):

            clean_line = (
                line
                .replace("·", "")
                .replace("-", "")
                .replace("•", "")
                .strip()
            )

            bullets.append(clean_line)

    return bullets

# =========================================================
# EXTRACT SENTENCES
# =========================================================

def extract_sentences(text):

    lines = text.split("\n")

    cleaned = []

    for line in lines:

        line = line.strip()

        if line:
            cleaned.append(line)

    return cleaned

# =========================================================
# MAIN GRAPH EXTRACTION
# =========================================================

def build_graph(doc_path):

    print(f"\nProcessing: {doc_path.name}")

    text = read_docx(doc_path)

    sections = split_sections(text)

    # -----------------------------------------------------
    # SECTION REFERENCES
    # -----------------------------------------------------

    identity = sections.get("A. Job Identity", "")

    role_summary = sections.get(
        "B. Role Summary (Scope and Impact)",
        ""
    )

    responsibilities = sections.get(
        "C. Key Responsibilities",
        ""
    )

    org_scope = sections.get(
        "D. Organizational Scope",
        ""
    )

    reporting = sections.get(
        "E. Reporting Relationships",
        ""
    )

    contacts = sections.get(
        "F. Key Contacts and Communication",
        ""
    )

    innovation = sections.get(
        "G. Contribution to Innovation and Change",
        ""
    )

    qualifications = sections.get(
        "H. Qualifications",
        ""
    )

    technical = sections.get(
        "I. Technical & Business Knowledge",
        ""
    )

    competencies = sections.get(
        "J. Competencies & Personal Attributes",
        ""
    )

    problem_solving = sections.get(
        "K. Problem Solving & Decision Complexity",
        ""
    )

    environment = sections.get(
        "L. Environment & Risk",
        ""
    )

    # -----------------------------------------------------
    # BUILD GRAPH OBJECT
    # -----------------------------------------------------

    graph = {

        # =================================================
        # CORE ROLE DATA
        # =================================================

        "role": {
            "title": extract_field(identity, "Job Title"),
            "department": extract_field(identity, "Department/Function"),
            "location": extract_field(identity, "Location"),
            "reports_to": extract_field(identity, "Reports To"),
            "role_level": extract_field(identity, "Role Level"),
            "summary": role_summary
        },

        # =================================================
        # RESPONSIBILITIES
        # =================================================

        "responsibilities": extract_bullets(
            responsibilities
        ),

        # =================================================
        # ORGANIZATIONAL SCOPE
        # =================================================

        "organizational_scope": {
            "sphere_of_influence": extract_field(
                org_scope,
                "Sphere of Influence"
            ),

            "extent_of_impact": extract_field(
                org_scope,
                "Extent of Impact"
            ),

            "decision_autonomy": extract_field(
                org_scope,
                "Decision Autonomy"
            )
        },

        # =================================================
        # REPORTING RELATIONSHIPS
        # =================================================

        "relationships": {

            "solid_line_to": extract_field(
                reporting,
                "Solid Line To"
            ),

            "matrix_reporting": extract_field(
                reporting,
                "Matrix/Functional Reporting"
            ),

            "direct_reports": extract_field(
                reporting,
                "Direct Reports"
            ),

            "dotted_line_relationships": extract_field(
                reporting,
                "Dotted-line Relationships"
            )
        },

        # =================================================
        # CONTACTS
        # =================================================

        "stakeholders": extract_sentences(
            contacts
        ),

        # =================================================
        # INNOVATION
        # =================================================

        "innovation_and_change": extract_bullets(
            innovation
        ),

        # =================================================
        # QUALIFICATIONS
        # =================================================

        "qualifications": {
            "education": extract_field(
                qualifications,
                "Education"
            ),

            "experience": extract_field(
                qualifications,
                "Experience"
            ),

            "work_experience": extract_field(
                qualifications,
                "Work Experience"
            ),

            "languages": extract_field(
                qualifications,
                "Languages"
            ),

            "certifications": extract_field(
                qualifications,
                "Certifications"
            )
        },

        # =================================================
        # TECHNICAL KNOWLEDGE
        # =================================================

        "technical_knowledge": extract_sentences(
            technical
        ),

        # =================================================
        # COMPETENCIES
        # =================================================

        "competencies": extract_bullets(
            competencies
        ),

        # =================================================
        # PROBLEM SOLVING
        # =================================================

        "problem_solving": extract_sentences(
            problem_solving
        ),

        # =================================================
        # ENVIRONMENT
        # =================================================

        "environment": extract_sentences(
            environment
        )
    }

    return graph

# =========================================================
# LOAD ALL DOCX FILES
# =========================================================

files = list(
    Path(BASE_DIR).glob("*.docx")
)

print(f"\nFound {len(files)} DOCX files.")

# =========================================================
# PROCESS ALL FILES
# =========================================================

all_graphs = []

for file in files:

    try:

        graph = build_graph(file)

        all_graphs.append(graph)

    except Exception as e:

        print(f"\nERROR processing {file.name}")
        print(e)

# =========================================================
# SAVE TO JSON
# =========================================================

output_file = Path(BASE_DIR) / "knowledge_graph.json"

with open(output_file, "w", encoding="utf-8") as f:

    json.dump(
        all_graphs,
        f,
        indent=2,
        ensure_ascii=False
    )

print("\n===================================")
print("DONE")
print("===================================")

print(f"\nSaved to:\n{output_file}")

# =========================================================
# PRINT PREVIEW
# =========================================================

print("\n===================================")
print("GRAPH PREVIEW")
print("===================================")

print(
    json.dumps(
        all_graphs[:1],
        indent=2,
        ensure_ascii=False
    )
)