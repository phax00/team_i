import base64
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from difflib import SequenceMatcher, get_close_matches
from collections import defaultdict
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "docs" / "data"
CHAT_DIR = ROOT / "chat"
SKILLWIKI_LOGO_ICON_FILE = ROOT / "skillwiki_logo_icon.png"
SKILLWIKI_LOGO_FILE = ROOT / "skillwiki_logo.jpeg"
GRAPH_OPTIONS = {
    "Basic Graph": DATA_DIR / "knowledge_graph_core_normalized.json",
    "Detailed Graph": DATA_DIR / "knowledge_graph_school_mvp_normalized.json",
}
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_MODEL_TIMEOUT_SECONDS = 60
SKILLWIKI_LOGO_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" aria-hidden="true" focusable="false">
  <g fill="none" stroke="#8B3DFF" stroke-linecap="round" stroke-width="6.5">
    <path d="M64 66 C53 58 43 54 32 49"/>
    <path d="M64 66 C49 67 39 66 26 70"/>
    <path d="M64 66 C50 74 42 82 34 93"/>
    <path d="M64 66 C59 82 57 94 58 108"/>
    <path d="M64 66 C73 80 80 90 90 100"/>
    <path d="M64 66 C79 72 90 74 104 74"/>
    <path d="M64 66 C78 58 87 51 95 40"/>
    <path d="M64 66 C67 49 67 37 65 23"/>
    <path d="M64 66 C56 52 49 43 37 35"/>
    <path d="M64 66 C78 65 89 62 101 56"/>

    <path d="M44 55 C39 49 35 44 29 39"/>
    <path d="M44 55 C46 48 45 43 43 35"/>
    <path d="M44 55 C52 53 58 50 64 45"/>

    <path d="M36 73 C30 79 26 86 23 95"/>
    <path d="M36 73 C29 72 22 73 15 76"/>
    <path d="M36 73 C39 83 40 92 39 102"/>

    <path d="M79 48 C86 44 92 40 98 34"/>
    <path d="M79 48 C80 39 82 31 87 24"/>
    <path d="M79 48 C88 50 96 50 106 47"/>

    <path d="M85 78 C92 80 99 79 108 76"/>
    <path d="M85 78 C89 86 94 92 101 97"/>
    <path d="M85 78 C82 87 82 95 85 105"/>

    <path d="M58 87 C51 89 44 93 38 99"/>
    <path d="M58 87 C58 95 56 103 51 110"/>
    <path d="M58 87 C64 92 69 97 73 104"/>
  </g>
  <g fill="#A855F7">
    <circle cx="64" cy="66" r="7.2"/>
    <circle cx="32" cy="49" r="4.6"/>
    <circle cx="26" cy="70" r="4.6"/>
    <circle cx="34" cy="93" r="4.6"/>
    <circle cx="58" cy="108" r="4.6"/>
    <circle cx="90" cy="100" r="4.6"/>
    <circle cx="104" cy="74" r="4.6"/>
    <circle cx="95" cy="40" r="4.6"/>
    <circle cx="65" cy="23" r="4.6"/>
    <circle cx="37" cy="35" r="4.6"/>
    <circle cx="101" cy="56" r="4.6"/>

    <circle cx="29" cy="39" r="4.1"/>
    <circle cx="43" cy="35" r="4.1"/>
    <circle cx="64" cy="45" r="4.1"/>
    <circle cx="23" cy="95" r="4.1"/>
    <circle cx="15" cy="76" r="4.1"/>
    <circle cx="39" cy="102" r="4.1"/>
    <circle cx="98" cy="34" r="4.1"/>
    <circle cx="87" cy="24" r="4.1"/>
    <circle cx="106" cy="47" r="4.1"/>
    <circle cx="108" cy="76" r="4.1"/>
    <circle cx="101" cy="97" r="4.1"/>
    <circle cx="85" cy="105" r="4.1"/>
    <circle cx="38" cy="99" r="4.1"/>
    <circle cx="51" cy="110" r="4.1"/>
    <circle cx="73" cy="104" r="4.1"/>
  </g>
</svg>
""".strip()
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "or",
    "please",
    "show",
    "tell",
    "the",
    "to",
    "we",
    "what",
    "who",
}
QUERY_STRUCTURE_VOCAB = {
    "who",
    "what",
    "where",
    "when",
    "why",
    "how",
    "works",
    "work",
    "with",
    "yes",
    "they",
    "him",
    "her",
    "them",
    "their",
    "these",
    "those",
    "this",
    "that",
    "one",
    "under",
    "for",
    "through",
    "via",
    "reports",
    "report",
    "reporting",
    "manager",
    "boss",
    "supervisor",
    "team",
    "people",
    "person",
    "role",
    "roles",
    "skill",
    "skills",
    "system",
    "systems",
    "topic",
    "topics",
    "department",
    "departments",
    "location",
    "locations",
    "country",
    "countries",
    "site",
    "sites",
    "related",
    "relationship",
    "between",
    "connected",
    "somehow",
    "does",
    "is",
    "are",
    "in",
    "the",
    "any",
    "other",
    "else",
}


load_dotenv(ROOT / ".env")


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --primary: #7B3AED;
            --primary-dark: #6026C9;
            --primary-soft: #F4EEFF;
            --surface: #FFFFFF;
            --surface-soft: #FAF7FF;
            --text: #121212;
            --muted: #5B5670;
            --border: #E6DDF8;
            --shadow: 0 20px 50px rgba(123, 58, 237, 0.08);
        }

        .stApp {
            background:
                radial-gradient(circle at top right, rgba(123, 58, 237, 0.10), transparent 28%),
                linear-gradient(180deg, #FCFAFF 0%, #F8F5FF 100%);
            color: var(--text);
        }

        .block-container {
            padding-top: 3rem;
            padding-bottom: 2rem;
            max-width: 1380px;
        }

        section[data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.78);
            border-right: 1px solid var(--border);
            backdrop-filter: blur(12px);
        }

        section[data-testid="stSidebar"] .block-container {
            padding-top: 1.4rem;
        }

        .hero-card {
            background: linear-gradient(135deg, #FFFFFF 0%, #F5EFFF 100%);
            border: 1px solid var(--border);
            border-radius: 28px;
            padding: 1.6rem 1.6rem 1.3rem 1.6rem;
            box-shadow: var(--shadow);
            margin-bottom: 1rem;
        }

        .hero-eyebrow {
            color: var(--primary);
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.72rem;
            font-weight: 700;
            margin-bottom: 0.6rem;
        }

        .hero-title {
            font-size: 2.2rem;
            line-height: 1.05;
            font-weight: 800;
            color: var(--text);
            margin: 0 0 0.55rem 0;
        }

        .skillwiki-brand {
            display: flex;
            align-items: center;
            gap: 0.72rem;
            width: max-content;
            max-width: 100%;
            overflow: visible;
        }

        .skillwiki-brand--sidebar {
            margin-bottom: 0.9rem;
        }

        .skillwiki-brand--compact {
            gap: 0.55rem;
        }

        .skillwiki-icon {
            width: 2.35rem;
            height: 2.35rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 auto;
        }

        .skillwiki-icon svg {
            width: 100%;
            height: 100%;
            display: block;
        }

        .skillwiki-icon img {
            width: 100%;
            height: 100%;
            display: block;
            object-fit: contain;
        }

        .skillwiki-logo {
            font-size: 2.25rem;
            line-height: 1.15;
            font-weight: 900;
            letter-spacing: -0.04em;
            margin: 0;
            color: #141414;
            display: inline-block;
            padding-top: 0.03rem;
            padding-bottom: 0.03rem;
        }

        .skillwiki-logo span,
        .skillwiki-wordmark span {
            color: var(--primary);
        }

        .skillwiki-wordmark {
            font-size: 1.18rem;
            line-height: 1.15;
            font-weight: 900;
            letter-spacing: -0.04em;
            color: #141414;
            display: inline-block;
            padding-top: 0.03rem;
            padding-bottom: 0.03rem;
        }

        .skillwiki-brand--compact .skillwiki-icon {
            width: 1.95rem;
            height: 1.95rem;
        }

        .skillwiki-brand--compact .skillwiki-wordmark {
            font-size: 1rem;
        }

        .hero-subtitle {
            color: var(--muted);
            font-size: 1rem;
            line-height: 1.5;
            max-width: 64rem;
            margin-bottom: 1rem;
        }

        .stat-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.8rem;
            margin-top: 1rem;
        }

        .stat-card {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 0.9rem 1rem;
        }

        .stat-label {
            color: var(--muted);
            font-size: 0.78rem;
            margin-bottom: 0.28rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 700;
        }

        .stat-value {
            color: var(--text);
            font-size: 1.1rem;
            font-weight: 800;
        }

        .section-card {
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid var(--border);
            border-radius: 24px;
            box-shadow: var(--shadow);
            overflow: hidden;
        }

        .section-header {
            padding: 1rem 1.15rem 0.7rem 1.15rem;
            border-bottom: 1px solid #F0E8FF;
            background: linear-gradient(180deg, rgba(123,58,237,0.06), rgba(123,58,237,0.02));
        }

        .section-title {
            font-size: 1.05rem;
            font-weight: 800;
            color: var(--text);
            margin-bottom: 0.22rem;
        }

        .section-title-brand {
            display: inline-flex;
            align-items: center;
            gap: 0.6rem;
        }

        .section-subtitle {
            color: var(--muted);
            font-size: 0.9rem;
        }

        .section-body {
            padding: 1rem 1.15rem 1.15rem 1.15rem;
        }

        .chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-top: 0.7rem;
        }

        .chip {
            background: #F6F1FF;
            border: 1px solid #E7D9FF;
            color: var(--primary-dark);
            border-radius: 999px;
            padding: 0.4rem 0.7rem;
            font-size: 0.84rem;
            font-weight: 600;
        }

        .evidence-card {
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 0.95rem;
            margin-bottom: 0.75rem;
        }

        .evidence-kicker {
            color: var(--primary);
            font-size: 0.72rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.35rem;
        }

        .evidence-title {
            font-size: 1rem;
            font-weight: 800;
            color: var(--text);
            margin-bottom: 0.45rem;
        }

        .evidence-body {
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.45;
        }

        .stChatMessage {
            background: rgba(255, 255, 255, 0.86);
            border: 1px solid var(--border);
            border-radius: 20px;
        }

        .stChatMessage [data-testid="stMarkdownContainer"] p {
            line-height: 1.55;
        }

        .stButton > button,
        .stDownloadButton > button,
        .stFormSubmitButton > button {
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 14px;
            font-weight: 700;
            padding: 0.62rem 1rem;
            box-shadow: 0 10px 24px rgba(123, 58, 237, 0.22);
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        .stFormSubmitButton > button:hover {
            background: var(--primary-dark);
        }

        .stTextInput input,
        .stSelectbox div[data-baseweb="select"] > div,
        .stTextArea textarea {
            border-radius: 14px !important;
            border-color: var(--border) !important;
            background: #FFFFFF !important;
        }

        .backend-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.45rem 0.75rem;
            border-radius: 999px;
            background: #F6F1FF;
            border: 1px solid #E7D9FF;
            color: #5B21B6;
            font-size: 0.84rem;
            font-weight: 700;
            margin-right: 0.45rem;
            margin-top: 0.35rem;
        }

        .sidebar-note {
            background: #F7F2FF;
            border: 1px solid #E8DDFD;
            border-radius: 18px;
            padding: 0.9rem 1rem;
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.45;
            margin-top: 0.8rem;
        }

        @media (max-width: 1100px) {
            .stat-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_graph(graph_path: str) -> dict[str, Any]:
    return json.loads(Path(graph_path).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_query_normalization() -> dict[str, Any]:
    path = CHAT_DIR / "query_normalization.json"
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def build_indexes(graph_path: str) -> dict[str, Any]:
    payload = load_graph(graph_path)
    nodes = payload.get("nodes", [])
    relationships = payload.get("relationships", [])
    nodes_by_id = {node["id"]: node for node in nodes}
    adjacency: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for rel in relationships:
        adjacency[rel["start"]].append(rel)
        adjacency[rel["end"]].append(
            {
                "start": rel["end"],
                "type": f"INVERSE_{rel['type']}",
                "end": rel["start"],
            }
        )

    searchable = {}
    for node in nodes:
        values: list[str] = []
        for key, value in node.items():
            if isinstance(value, list):
                values.extend(str(item) for item in value)
            else:
                values.append(str(value))
        searchable[node["id"]] = " ".join(values).lower()

    return {
        "payload": payload,
        "nodes_by_id": nodes_by_id,
        "adjacency": dict(adjacency),
        "searchable": searchable,
    }


def tokenize(text: str) -> list[str]:
    tokens = [token.casefold() for token in re.findall(r"\w+", strip_diacritics(text), flags=re.UNICODE)]
    return [token for token in tokens if token not in STOPWORDS and len(token) > 1]


def strip_diacritics(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def correct_query_structure_typos(text: str) -> str:
    vocab = QUERY_STRUCTURE_VOCAB
    explicit_typos = {
        "thez": "they",
        "tehy": "they",
        "thye": "they",
        "tyhe": "they",
        "htey": "they",
        "theyr": "their",
        "thier": "their",
    }
    parts = re.split(r"(\W+)", text.casefold())
    corrected: list[str] = []

    for part in parts:
        if not re.fullmatch(r"\w+", part):
            corrected.append(part)
            continue
        if part in explicit_typos:
            corrected.append(explicit_typos[part])
            continue
        if len(part) < 3 or part in vocab:
            corrected.append(part)
            continue
        matches = get_close_matches(part, sorted(vocab), n=1, cutoff=0.72)
        corrected.append(matches[0] if matches else part)
    return "".join(corrected)


def expand_query(text: str) -> str:
    expanded = correct_query_structure_typos(text)
    alias_map = load_query_normalization().get("aliases", {})
    for alias, canonical in alias_map.items():
        expanded = re.sub(rf"\b{re.escape(alias)}\b", canonical, expanded)
    return expanded


def score_node(node: dict[str, Any], blob: str, query: str, tokens: list[str]) -> float:
    score = 0.0
    node_name = strip_diacritics(str(node.get("name", "")).casefold())
    query_lower = strip_diacritics(query.casefold())
    blob_lower = strip_diacritics(blob.casefold())

    if node_name == query_lower:
        score += 10
    if query_lower and query_lower in blob_lower:
        score += 4
    for token in tokens:
        if token in node_name:
            score += 2.2
        elif token in blob_lower:
            score += 1.0

    label = node.get("label", "")
    bonuses = {
        "skill": "Skill",
        "role": "Role",
        "person": "Person",
        "system": "System",
        "team": "Team",
        "topic": "Topic",
    }
    for hint, expected_label in bonuses.items():
        if hint in query_lower and label == expected_label:
            score += 1.7
    return score


def find_relevant_nodes(indexes: dict[str, Any], query: str, limit: int = 6) -> list[dict[str, Any]]:
    expanded_query = expand_query(query)
    tokens = tokenize(expanded_query)
    scored: list[tuple[float, dict[str, Any]]] = []

    for node_id, blob in indexes["searchable"].items():
        node = indexes["nodes_by_id"][node_id]
        score = score_node(node, blob, expanded_query, tokens)
        if score > 0:
            scored.append((score, node))

    scored.sort(key=lambda item: (item[0], item[1].get("name", "")), reverse=True)

    results = []
    seen = set()
    for score, node in scored:
        if node["id"] in seen:
            continue
        seen.add(node["id"])
        node_copy = dict(node)
        node_copy["_score"] = round(score, 2)
        results.append(node_copy)
        if len(results) >= limit:
            break
    return results


def format_human_list(items: list[str]) -> str:
    unique_items = []
    seen = set()
    for item in items:
        if item and item not in seen:
            seen.add(item)
            unique_items.append(item)
    if not unique_items:
        return ""
    if len(unique_items) == 1:
        return unique_items[0]
    if len(unique_items) == 2:
        return f"{unique_items[0]} and {unique_items[1]}"
    return f"{', '.join(unique_items[:-1])} and {unique_items[-1]}"


def skillwiki_logo_src() -> str:
    if SKILLWIKI_LOGO_ICON_FILE.exists():
        return "data:image/png;base64," + base64.b64encode(SKILLWIKI_LOGO_ICON_FILE.read_bytes()).decode("ascii")
    if SKILLWIKI_LOGO_FILE.exists():
        return "data:image/jpeg;base64," + base64.b64encode(SKILLWIKI_LOGO_FILE.read_bytes()).decode("ascii")
    return "data:image/svg+xml;base64," + base64.b64encode(SKILLWIKI_LOGO_SVG.encode("utf-8")).decode("ascii")


def skillwiki_brand_html(compact: bool = False, include_logo_text_class: bool = False) -> str:
    brand_class = "skillwiki-brand skillwiki-brand--compact" if compact else "skillwiki-brand"
    wordmark_class = "skillwiki-logo" if include_logo_text_class else "skillwiki-wordmark"
    logo_src = skillwiki_logo_src()
    return (
        f'<div class="{brand_class}">'
        f'<span class="skillwiki-icon"><img src="{logo_src}" alt="SkillWiki logo"/></span>'
        f'<span class="{wordmark_class}">Skill<span>Wiki</span></span>'
        "</div>"
    )


def format_role_names(role_names: list[str]) -> str:
    cleaned = [re.sub(r"\s*/\s*", " / ", str(role)).strip() for role in role_names if role]
    return format_human_list(cleaned)


def display_query_term(text: str) -> str:
    expanded = normalize_target_phrase(text)
    words = []
    for word in expanded.split():
        if word.isalpha() and len(word) <= 4:
            words.append(word.upper())
        else:
            words.append(word.title())
    return " ".join(words)


def normalize_target_phrase(text: str) -> str:
    cleaned = text.strip(" ?.")
    cleaned = re.sub(r"^(the|a|an)\s+", "", cleaned, flags=re.IGNORECASE)
    return expand_query(cleaned).strip()


def name_match_score(name: str, normalized_query: str, tokens: list[str]) -> float:
    candidate = strip_diacritics(name.casefold())
    if not candidate or not normalized_query:
        return 0.0

    score = 0.0
    normalized_query = strip_diacritics(normalized_query.casefold())
    candidate_tokens = [token.casefold() for token in re.findall(r"\w+", candidate, flags=re.UNICODE)]
    if candidate == normalized_query:
        score += 100
    elif normalized_query in candidate:
        score += 70
    elif candidate in normalized_query:
        score += 55
    else:
        phrase_ratio = SequenceMatcher(None, candidate, normalized_query).ratio()
        if phrase_ratio >= 0.92:
            score += 60
        elif phrase_ratio >= 0.86:
            score += 36

    token_hits = 0
    fuzzy_token_hits = 0
    for token in tokens:
        if token in candidate:
            token_hits += 1
            score += 12
            continue
        best_ratio = 0.0
        for candidate_token in candidate_tokens:
            ratio = SequenceMatcher(None, token, candidate_token).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
        if best_ratio >= 0.9:
            fuzzy_token_hits += 1
            score += 11
        elif best_ratio >= 0.8:
            fuzzy_token_hits += 1
            score += 6

    if tokens and token_hits == len(tokens):
        score += 26
    elif tokens and token_hits + fuzzy_token_hits == len(tokens):
        score += 18
    elif token_hits or fuzzy_token_hits:
        score += (token_hits + fuzzy_token_hits) * 3
    return score


def find_named_nodes(
    indexes: dict[str, Any],
    query: str,
    labels: set[str],
    limit: int = 6,
    min_score: float = 0.1,
) -> list[dict[str, Any]]:
    normalized_query = normalize_target_phrase(query)
    tokens = tokenize(normalized_query)
    matches: list[tuple[float, dict[str, Any]]] = []

    for node in indexes["nodes_by_id"].values():
        if node.get("label") not in labels:
            continue
        score = name_match_score(str(node.get("name", "")), normalized_query, tokens)
        if score >= min_score:
            node_copy = dict(node)
            node_copy["_score"] = round(score, 2)
            matches.append((score, node_copy))

    matches.sort(key=lambda item: (item[0], item[1].get("name", "")), reverse=True)
    return [node for _, node in matches[:limit]]


def related_people_for_node(indexes: dict[str, Any], node: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    adjacency = indexes["adjacency"]
    nodes_by_id = indexes["nodes_by_id"]
    relation_map = {
        "Role": "INVERSE_HAS_ROLE",
        "System": "INVERSE_KNOWS_SYSTEM",
        "Skill": "INVERSE_HAS_SKILL",
        "Topic": "INVERSE_OWNS_TOPIC",
        "JobDescription": "INVERSE_LINKED_TO_JD",
    }
    expected_rel = relation_map.get(str(node.get("label")))
    if not expected_rel:
        return [], []

    names: list[str] = []
    people_nodes: list[dict[str, Any]] = []
    for rel in adjacency.get(node["id"], []):
        if rel["type"] != expected_rel:
            continue
        person_node = nodes_by_id.get(rel["end"])
        if person_node and person_node.get("label") == "Person":
            names.append(person_node["name"])
            people_nodes.append(person_node)
    return names, people_nodes


def resolve_best_entity(
    indexes: dict[str, Any],
    phrase: str,
    labels: set[str] | None = None,
    min_score: float = 30,
) -> dict[str, Any] | None:
    candidate_labels = labels or {"Person", "Role", "JobDescription", "Department", "Team", "Country", "Site", "Skill", "Topic", "System"}
    matches = find_named_nodes(indexes, phrase, candidate_labels, limit=5, min_score=min_score)
    return matches[0] if matches else None


def describe_relationship_step(start_node: dict[str, Any], rel_type: str, end_node: dict[str, Any]) -> str:
    start_name = str(start_node.get("name", start_node.get("id", "start")))
    end_name = str(end_node.get("name", end_node.get("id", "end")))
    templates = {
        "REPORTS_TO": f"{start_name} reports to {end_name}",
        "INVERSE_REPORTS_TO": f"{end_name} reports to {start_name}",
        "HAS_ROLE": f"{start_name} holds the role {end_name}",
        "INVERSE_HAS_ROLE": f"{end_name} holds the role {start_name}",
        "BELONGS_TO_DEPARTMENT": f"{start_name} belongs to the department {end_name}",
        "INVERSE_BELONGS_TO_DEPARTMENT": f"{end_name} belongs to the department {start_name}",
        "MEMBER_OF": f"{start_name} is a member of {end_name}",
        "INVERSE_MEMBER_OF": f"{end_name} is a member of {start_name}",
        "LOCATED_IN": f"{start_name} is located in {end_name}",
        "INVERSE_LOCATED_IN": f"{end_name} is located in {start_name}",
        "AT_SITE": f"{start_name} is at the site {end_name}",
        "INVERSE_AT_SITE": f"{end_name} is at the site {start_name}",
        "HAS_SKILL": f"{start_name} has the skill {end_name}",
        "INVERSE_HAS_SKILL": f"{end_name} has the skill {start_name}",
        "KNOWS_SYSTEM": f"{start_name} knows the system {end_name}",
        "INVERSE_KNOWS_SYSTEM": f"{end_name} knows the system {start_name}",
        "OWNS_TOPIC": f"{start_name} owns the topic {end_name}",
        "INVERSE_OWNS_TOPIC": f"{end_name} owns the topic {start_name}",
        "LINKED_TO_JD": f"{start_name} is linked to the job description {end_name}",
        "INVERSE_LINKED_TO_JD": f"{end_name} is linked to the job description {start_name}",
        "DESCRIBED_BY": f"{start_name} is described by {end_name}",
        "INVERSE_DESCRIBED_BY": f"{end_name} is described by {start_name}",
        "REQUIRES_SKILL": f"{start_name} requires the skill {end_name}",
        "INVERSE_REQUIRES_SKILL": f"{end_name} requires the skill {start_name}",
        "APPLIES_TO_COUNTRY": f"{start_name} applies to the country {end_name}",
        "INVERSE_APPLIES_TO_COUNTRY": f"{end_name} applies to the country {start_name}",
    }
    return templates.get(rel_type, f"{start_name} --{readable_relation_type(rel_type)}--> {end_name}")


def find_shortest_relationship_path(
    indexes: dict[str, Any],
    start_id: str,
    end_id: str,
    max_depth: int = 3,
) -> list[dict[str, Any]] | None:
    adjacency = indexes["adjacency"]
    queue: list[tuple[str, list[dict[str, Any]]]] = [(start_id, [])]
    visited: set[tuple[str, int]] = {(start_id, 0)}

    while queue:
        current_id, path = queue.pop(0)
        if current_id == end_id and path:
            return path
        if len(path) >= max_depth:
            continue
        for rel in adjacency.get(current_id, []):
            next_id = rel["end"]
            state = (next_id, len(path) + 1)
            if state in visited:
                continue
            visited.add(state)
            next_path = path + [rel]
            if next_id == end_id:
                return next_path
            queue.append((next_id, next_path))
    return None


def is_more_results_question(question: str) -> bool:
    normalized = expand_query(question)
    patterns = [
        r"^\s*is\s+there\s+any\s+other\??\s*$",
        r"^\s*anyone\s+else\??\s*$",
        r"^\s*who\s+else\??\s*$",
        r"^\s*any\s+other\??\s*$",
        r"^\s*what\s+about\s+others\??\s*$",
    ]
    return any(re.search(pattern, normalized) for pattern in patterns)


def is_why_question(question: str) -> bool:
    normalized = expand_query(question)
    patterns = [
        r"^\s*why\??\s*$",
        r"^\s*why\s+them\??\s*$",
        r"^\s*why\s+him\??\s*$",
        r"^\s*why\s+her\??\s*$",
        r"^\s*why\s+those\??\s*$",
        r"^\s*how\s+so\??\s*$",
    ]
    return any(re.search(pattern, normalized) for pattern in patterns)


def role_names_in_graph(indexes: dict[str, Any]) -> list[str]:
    return sorted(
        str(node.get("name"))
        for node in indexes["nodes_by_id"].values()
        if node.get("label") == "Role" and node.get("name")
    )


def suggest_similar_roles_with_model(
    target_phrase: str,
    indexes: dict[str, Any],
    gemini_model_name: str,
    ollama_model_name: str,
    ollama_host: str,
) -> list[str]:
    role_names = role_names_in_graph(indexes)
    if not role_names:
        return []

    prompt = f"""
You help map a user title to the closest existing role names in an enterprise role catalog.
Choose up to 3 closest roles for this missing title:
{display_query_term(target_phrase)}

Only use exact role names from this list. If nothing is reasonably close, return NONE.
Return only the selected role names, one per line, with no bullets and no explanation.

Available roles:
{chr(10).join(role_names)}
"""

    outputs: list[str] = []
    ollama_available = bool(ollama_host) and is_ollama_available(ollama_host)
    runtime_mode = detect_runtime_mode(ollama_available)
    gemini_ready = bool(gemini_model_name) and bool(get_api_key()) and not bool(st.session_state.get("gemini_model_disabled", False))
    use_model = bool(ollama_model_name) or gemini_ready
    chain = provider_chain(runtime_mode, use_model, ollama_available, gemini_ready)

    for backend in chain:
        try:
            if backend == "ollama":
                if not ollama_available:
                    continue
                note_internal_model_use("Ollama", "similar role suggestion")
                response = call_ollama(prompt, ollama_model_name, ollama_host)
            elif backend == "gemini":
                if not gemini_ready:
                    continue
                note_internal_model_use("Gemini", "similar role suggestion")
                response = call_gemini(prompt, gemini_model_name)
            else:
                continue
        except Exception as error:
            if is_timeout_error(error):
                note_internal_model_use(backend, "timed out")
            if backend == "gemini" and is_gemini_quota_error(error):
                mark_gemini_unavailable("Gemini is temporarily unavailable because the API quota or rate limit was reached.")
            continue

        outputs = [line.strip() for line in response.splitlines() if line.strip()]
        if outputs:
            break

    if not outputs:
        return []

    if any(line.casefold() == "none" for line in outputs):
        return []

    canonical_map = {role.casefold(): role for role in role_names}
    suggestions: list[str] = []
    seen = set()
    for line in outputs:
        canonical = canonical_map.get(line.casefold())
        if canonical and canonical not in seen:
            seen.add(canonical)
            suggestions.append(canonical)
            if len(suggestions) >= 3:
                break
    return suggestions


def build_closest_match_suggestion(
    target_phrase: str,
    indexes: dict[str, Any],
    labels: set[str],
    intro: str,
    gemini_model_name: str = "",
    ollama_model_name: str = "",
    ollama_host: str = "",
) -> tuple[str, dict[str, Any], str] | None:
    config = load_query_normalization()
    if "Role" in labels:
        configured_roles: list[str] = []
        if gemini_model_name or ollama_model_name:
            configured_roles = suggest_similar_roles_with_model(
                target_phrase,
                indexes,
                gemini_model_name,
                ollama_model_name,
                ollama_host,
            )
        if not configured_roles:
            configured_roles = config.get("similar_roles", {}).get(normalize_target_phrase(target_phrase), [])
        if configured_roles:
            top_nodes: list[dict[str, Any]] = []
            relationships: list[dict[str, Any]] = []
            answer_lines = [intro]
            for role_name in configured_roles:
                matched_roles = find_named_nodes(indexes, role_name, {"Role"}, limit=1, min_score=1)
                if not matched_roles:
                    continue
                best_role = matched_roles[0]
                top_nodes.append(best_role)
                people_names, people_nodes = related_people_for_node(indexes, best_role)
                top_nodes.extend(dict(node, _score=best_role["_score"]) for node in people_nodes)
                for person_node in people_nodes:
                    relationships.append({"start": person_node["id"], "type": "HAS_ROLE", "end": best_role["id"]})
                if people_names:
                    answer_lines.append(
                        f"A close related role in this graph is `{best_role['name']}`, which is currently held by {format_human_list(people_names)}."
                    )
                else:
                    answer_lines.append(f"A close related role in this graph is `{best_role['name']}`.")
            if len(answer_lines) > 1:
                seen = {}
                for node in top_nodes:
                    seen[node["id"]] = node
                evidence = {
                    "top_nodes": list(seen.values()),
                    "related_nodes": list(seen.values()),
                    "relationships": relationships[:18],
                }
                return "\n".join(answer_lines), evidence, "Graph Search"

    suggestions = find_named_nodes(indexes, target_phrase, labels, limit=3)
    if not suggestions:
        empty_evidence = {"top_nodes": [], "related_nodes": [], "relationships": []}
        return f"{intro}\nI also could not find a reliable close alternative in the current graph.", empty_evidence, "Graph Search"

    best = suggestions[0]
    top_nodes = [best]
    relationships: list[dict[str, Any]] = []
    label = str(best.get("label"))
    answer_lines = [intro]

    if label == "Person":
        role_names = []
        for rel in indexes["adjacency"].get(best["id"], []):
            if rel["type"] == "HAS_ROLE":
                role_node = indexes["nodes_by_id"].get(rel["end"])
                if role_node:
                    role_names.append(role_node["name"])
                    top_nodes.append(dict(role_node, _score=best["_score"]))
                    relationships.append({"start": best["id"], "type": "HAS_ROLE", "end": rel["end"]})
        if role_names:
            answer_lines.append(
                f"A close match in this graph is `{best['name']}`, who holds the {format_role_names(role_names)} role."
            )
        else:
            answer_lines.append(f"A close match in this graph is `{best['name']}`.")

    elif label in {"Role", "System", "Skill", "JobDescription"}:
        people_names, people_nodes = related_people_for_node(indexes, best)
        top_nodes.extend(dict(node, _score=best["_score"]) for node in people_nodes)
        relation_type = {
            "Role": "HAS_ROLE",
            "System": "KNOWS_SYSTEM",
            "Skill": "HAS_SKILL",
            "JobDescription": "LINKED_TO_JD",
        }.get(label)
        if relation_type:
            for person_node in people_nodes:
                relationships.append({"start": person_node["id"], "type": relation_type, "end": best["id"]})
        if people_names:
            answer_lines.append(
                f"A close related {label.lower()} in this graph is `{best['name']}`, which is linked to {format_human_list(people_names)}."
            )
        else:
            answer_lines.append(f"A close related {label.lower()} in this graph is `{best['name']}`.")

    else:
        answer_lines.append(f"A close match in this graph is `{best['name']}`.")

    seen = {}
    for node in top_nodes:
        seen[node["id"]] = node
    evidence = {
        "top_nodes": list(seen.values()),
        "related_nodes": list(seen.values()),
        "relationships": relationships[:18],
    }
    return "\n".join(answer_lines), evidence, "Graph Search"


def find_person_ids_for_target(indexes: dict[str, Any], query: str, require_strong_match: bool = False) -> list[str]:
    expanded_query = normalize_target_phrase(query)
    top_nodes = find_relevant_nodes(indexes, expanded_query, limit=8)
    adjacency = indexes["adjacency"]
    person_ids: list[str] = []
    strong_nodes = []
    query_tokens = [token.casefold() for token in re.findall(r"\w+", strip_diacritics(expanded_query), flags=re.UNICODE)]

    def is_strong_name_match(node_name: str) -> bool:
        candidate = strip_diacritics(node_name.casefold())
        candidate_tokens = [token.casefold() for token in re.findall(r"\w+", candidate, flags=re.UNICODE)]
        if not expanded_query:
            return False
        expanded_plain = strip_diacritics(expanded_query.casefold())
        if candidate == expanded_plain:
            return True
        phrase_ratio = SequenceMatcher(None, candidate, expanded_plain).ratio()
        if phrase_ratio >= 0.9:
            return True
        if len(query_tokens) == 1:
            token = query_tokens[0]
            if len(token) <= 4:
                if token in candidate_tokens:
                    return True
                return any(SequenceMatcher(None, token, candidate_token).ratio() >= 0.88 for candidate_token in candidate_tokens)
            return (
                bool(re.search(rf"\b{re.escape(expanded_plain)}\b", candidate))
                or expanded_plain in candidate
                or any(SequenceMatcher(None, expanded_plain, candidate_token).ratio() >= 0.88 for candidate_token in candidate_tokens)
            )
        if expanded_plain in candidate or all(token in candidate_tokens for token in query_tokens):
            return True
        matched = 0
        for token in query_tokens:
            if any(SequenceMatcher(None, token, candidate_token).ratio() >= 0.84 for candidate_token in candidate_tokens):
                matched += 1
        return matched == len(query_tokens)

    for node in top_nodes:
        node_name = str(node.get("name", "")).casefold()
        if is_strong_name_match(node_name):
            strong_nodes.append(node)

    if require_strong_match and not strong_nodes:
        return []

    candidate_nodes = strong_nodes or top_nodes[:2]

    for node in candidate_nodes:
        if node["label"] == "Person":
            person_ids.append(node["id"])
        elif node["label"] == "Role":
            for rel in adjacency.get(node["id"], []):
                if rel["type"] == "INVERSE_HAS_ROLE":
                    person_ids.append(rel["end"])
        elif node["label"] == "JobDescription":
            for rel in adjacency.get(node["id"], []):
                if rel["type"] == "INVERSE_LINKED_TO_JD":
                    person_ids.append(rel["end"])

    deduped: list[str] = []
    seen = set()
    for person_id in person_ids:
        if person_id not in seen:
            seen.add(person_id)
            deduped.append(person_id)
    return deduped


def try_reporting_answer(
    question: str,
    indexes: dict[str, Any],
    gemini_model_name: str = "",
    ollama_model_name: str = "",
    ollama_host: str = "",
) -> tuple[str, dict[str, Any], str] | None:
    normalized = expand_query(question)
    match = re.search(r"(?:who\s+)?reports?\s+to\s+(.+)", normalized)
    if not match:
        match = re.search(r"who\s+works?\s+under\s+(.+)", normalized)
    if not match:
        match = re.search(r"who\s+works?\s+for\s+(.+)", normalized)
    if not match:
        match = re.search(r"who\s+is\s+under\s+(.+)", normalized)
    if not match:
        match = re.search(r"^\s*(?!who\b)(?!does\b)(?!is\b)(?!are\b)(.+?)\s+(team|workers?|people|staff)\s*\??\s*$", normalized)
    if not match:
        return None

    target_phrase = match.group(1).strip(" ?.")
    if not target_phrase:
        return None

    nodes_by_id = indexes["nodes_by_id"]
    adjacency = indexes["adjacency"]
    target_person_ids = find_person_ids_for_target(indexes, target_phrase, require_strong_match=True)
    if not target_person_ids:
        return build_closest_match_suggestion(
            target_phrase,
            indexes,
            {"Person", "Role"},
            f"I could not find the exact person or role `{display_query_term(target_phrase)}` in the current graph.",
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )

    answer_lines = []
    top_nodes = []
    relationships = []

    for person_id in target_person_ids:
        person_node = nodes_by_id.get(person_id)
        if not person_node:
            continue
        top_nodes.append(person_node)

        direct_reports = []
        role_names = []
        for rel in adjacency.get(person_id, []):
            if rel["type"] == "INVERSE_REPORTS_TO":
                report_node = nodes_by_id.get(rel["end"])
                if report_node:
                    direct_reports.append(report_node["name"])
                    top_nodes.append(report_node)
                    relationships.append({"start": rel["end"], "type": "REPORTS_TO", "end": person_id})
            elif rel["type"] == "HAS_ROLE":
                role_node = nodes_by_id.get(rel["end"])
                if role_node:
                    role_names.append(role_node["name"])
                    top_nodes.append(role_node)

        person_name = person_node["name"]
        role_suffix = f", who holds the {format_role_names(role_names)} role" if role_names else ""
        if direct_reports:
            reports_text = ", ".join(direct_reports[:-1]) + (" and " + direct_reports[-1] if len(direct_reports) > 1 else direct_reports[0])
            answer_lines.append(f"{reports_text} currently report to {person_name}{role_suffix}.")
        else:
            answer_lines.append(f"The graph does not show anyone currently reporting to {person_name}{role_suffix}.")

    if not answer_lines:
        return None

    seen_top = {}
    for node in top_nodes:
        seen_top[node["id"]] = node
    evidence = {
        "top_nodes": [dict(node, _score=10.0) if "_score" not in node else node for node in seen_top.values()],
        "related_nodes": list(seen_top.values()),
        "relationships": relationships[:18],
    }
    return "\n".join(answer_lines), evidence, "Graph Search"


def try_reverse_reporting_answer(
    question: str,
    indexes: dict[str, Any],
    gemini_model_name: str = "",
    ollama_model_name: str = "",
    ollama_host: str = "",
) -> tuple[str, dict[str, Any], str] | None:
    normalized = expand_query(question)
    english_patterns = [
        r"who\s+does\s+(.+?)\s+report\s+to",
        r"who\s+is\s+(.+?)\s+reporting\s+to",
        r"who\s+is\s+(.+?)(?:'s|s)\s+(?:boss|manager|supervisor)\b",
        r"who\s+is\s+the\s+(?:boss|manager|supervisor)\s+of\s+(.+)",
    ]
    english_match = None
    for pattern in english_patterns:
        english_match = re.search(pattern, normalized)
        if english_match:
            break
    if english_match:
        target_phrase = english_match.group(1).strip(" ?.")
        if not target_phrase:
            return None

        nodes_by_id = indexes["nodes_by_id"]
        adjacency = indexes["adjacency"]
        person_ids = find_person_ids_for_target(indexes, target_phrase, require_strong_match=True)
        if not person_ids:
            return build_closest_match_suggestion(
                target_phrase,
                indexes,
                {"Person", "Role"},
                f"I could not find the exact person or role `{display_query_term(target_phrase)}` in the current graph.",
                gemini_model_name,
                ollama_model_name,
                ollama_host,
            )

        answer_lines = []
        top_nodes = []
        relationships = []

        for person_id in person_ids:
            person_node = nodes_by_id.get(person_id)
            if not person_node:
                continue
            top_nodes.append(person_node)

            manager_names = []
            manager_roles = []
            for rel in adjacency.get(person_id, []):
                if rel["type"] == "REPORTS_TO":
                    manager_node = nodes_by_id.get(rel["end"])
                    if manager_node:
                        manager_names.append(manager_node["name"])
                        top_nodes.append(manager_node)
                        relationships.append({"start": person_id, "type": "REPORTS_TO", "end": rel["end"]})
                        for manager_rel in adjacency.get(rel["end"], []):
                            if manager_rel["type"] == "HAS_ROLE":
                                role_node = nodes_by_id.get(manager_rel["end"])
                                if role_node:
                                    manager_roles.append(role_node["name"])
                                    top_nodes.append(role_node)

            if manager_names:
                manager_text = format_human_list(manager_names)
                role_suffix = f", who holds the {format_role_names(manager_roles)} role" if manager_roles else ""
                answer_lines.append(f"{person_node['name']} currently reports to {manager_text}{role_suffix}.")
            else:
                answer_lines.append(f"The graph does not show a current manager for {person_node['name']}.")

        if not answer_lines:
            return None

        seen_top = {}
        for node in top_nodes:
            seen_top[node["id"]] = node
        evidence = {
            "top_nodes": [dict(node, _score=10.0) if "_score" not in node else node for node in seen_top.values()],
            "related_nodes": list(seen_top.values()),
            "relationships": relationships[:18],
        }
        return "\n".join(answer_lines), evidence, "Graph Search"
def try_greeting_or_intro_answer(question: str) -> tuple[str, dict[str, Any], str] | None:
    normalized = expand_query(question).strip().casefold()
    if not normalized:
        return None

    greeting_patterns = [
        r"^(hi|hello|hey|good morning|good afternoon|good evening)\s*!?\s*$",
        r"^(hi|hello|hey)\s+there\s*!?\s*$",
    ]
    intro_patterns = [
        r"^(who are you|what are you|introduce yourself|tell me about yourself)\??\s*$",
        r"^(what can you do|what do you do|how can you help|help)\??\s*$",
    ]

    if any(re.fullmatch(pattern, normalized) for pattern in greeting_patterns):
        answer = (
            "Hi, I'm SkillWiki. I help you explore the company knowledge graph in a natural way. "
            "You can ask me about people, roles, reporting lines, departments, locations, skills, systems, and relationships between nodes."
        )
        return answer, {"top_nodes": [], "related_nodes": [], "relationships": []}, "Graph Search"

    if any(re.fullmatch(pattern, normalized) for pattern in intro_patterns):
        answer = (
            "I'm SkillWiki, a graph-grounded assistant for navigating people, roles, teams, skills, systems, sites, and reporting structure. "
            "I can help with questions like who reports to whom, who works in a department, who knows a system, where someone is based, or how two nodes are connected."
        )
        return answer, {"top_nodes": [], "related_nodes": [], "relationships": []}, "Graph Search"

    return None


def try_identity_answer(question: str, indexes: dict[str, Any]) -> tuple[str, dict[str, Any], str] | None:
    normalized = expand_query(question)
    if re.search(r"\b(?:boss|manager|supervisor)\b", normalized):
        return None
    if re.search(r"\b(?:does\s+.+\s+report\s+to|reporting\s+to)\b", normalized):
        return None
    match = re.search(r"who\s+is\s+(.+)", normalized)
    if not match:
        return None

    target_phrase = match.group(1).strip(" ?.")
    if not target_phrase:
        return None

    nodes_by_id = indexes["nodes_by_id"]
    adjacency = indexes["adjacency"]
    person_ids = find_person_ids_for_target(indexes, target_phrase, require_strong_match=True)
    if not person_ids:
        return None

    answers = []
    top_nodes = []
    relationships = []

    for person_id in person_ids:
        person_node = nodes_by_id.get(person_id)
        if not person_node:
            continue
        top_nodes.append(person_node)

        role_names = []
        for rel in adjacency.get(person_id, []):
            if rel["type"] == "HAS_ROLE":
                role_node = nodes_by_id.get(rel["end"])
                if role_node:
                    role_names.append(role_node["name"])
                    top_nodes.append(role_node)
                    relationships.append({"start": person_id, "type": "HAS_ROLE", "end": rel["end"]})
            elif rel["type"] == "LINKED_TO_JD":
                jd_node = nodes_by_id.get(rel["end"])
                if jd_node:
                    top_nodes.append(jd_node)
                    relationships.append({"start": person_id, "type": "LINKED_TO_JD", "end": rel["end"]})

        if role_names:
            answers.append(f"{person_node['name']} holds the {format_role_names(role_names)} role.")
        else:
            answers.append(f"{person_node['name']} is the strongest identity match for that role or title in the graph.")

    if not answers:
        return None

    seen_top = {}
    for node in top_nodes:
        seen_top[node["id"]] = node
    evidence = {
        "top_nodes": [dict(node, _score=10.0) if "_score" not in node else node for node in seen_top.values()],
        "related_nodes": list(seen_top.values()),
        "relationships": relationships[:18],
    }
    return "\n".join(answers), evidence, "Graph Search"


def try_person_location_answer(
    question: str,
    indexes: dict[str, Any],
    last_query_state: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any], str, dict[str, Any] | None] | None:
    normalized = expand_query(question)

    target_phrase = ""
    group_people: list[str] = []

    if re.search(r"\bwhere\b", normalized):
        person_match = re.search(r"where\s+is\s+(.+?)\s+(?:based|located|working|work)\b", normalized)
        if not person_match:
            person_match = re.search(r"where\s+does\s+(.+?)\s+work\b", normalized)
        if person_match:
            target_phrase = person_match.group(1).strip(" ?.!<")
        else:
            group_match = re.search(r"where\s+are\s+(.+?)\s+(?:based|located|working)\b", normalized)
            if not group_match:
                group_match = re.search(r"where\s+do\s+(.+?)\s+work\b", normalized)
            if group_match:
                raw_target = group_match.group(1).strip(" ?.!<")
                if raw_target in {"they", "them", "these people", "those people"} and last_query_state:
                    if last_query_state.get("kind") in {"membership", "people_for_keyword", "person_location"}:
                        group_people = [str(name) for name in last_query_state.get("shown_people", []) if str(name).strip()]
                else:
                    target_phrase = raw_target

    if not target_phrase and not group_people:
        shorthand_match = re.search(
            r"^(?:what\s+is\s+)?(.+?)\s+(?:site|sites|location|locations|locality|localities|locali\w*|locati\w*)\s*$",
            normalized,
        )
        if shorthand_match:
            target_phrase = shorthand_match.group(1).strip(" ?.!<")

    nodes_by_id = indexes["nodes_by_id"]
    adjacency = indexes["adjacency"]

    person_ids: list[str] = []
    if group_people:
        for person_name in group_people:
            person_ids.extend(find_person_ids_for_target(indexes, person_name, require_strong_match=True))
    elif target_phrase:
        person_ids = find_person_ids_for_target(indexes, target_phrase, require_strong_match=True)
    else:
        return None

    deduped_person_ids: list[str] = []
    seen_person_ids = set()
    for person_id in person_ids:
        if person_id not in seen_person_ids:
            seen_person_ids.add(person_id)
            deduped_person_ids.append(person_id)
    person_ids = deduped_person_ids

    if not person_ids:
        return None

    answers: list[str] = []
    top_nodes: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    shown_people: list[str] = []

    for person_id in person_ids:
        person_node = nodes_by_id.get(person_id)
        if not person_node:
            continue

        sites: list[dict[str, Any]] = []
        countries: list[dict[str, Any]] = []
        for rel in adjacency.get(person_id, []):
            if rel["type"] == "AT_SITE":
                site_node = nodes_by_id.get(rel["end"])
                if site_node and site_node.get("label") == "Site":
                    sites.append(site_node)
                    relationships.append({"start": person_id, "type": "AT_SITE", "end": rel["end"]})
            elif rel["type"] == "LOCATED_IN":
                country_node = nodes_by_id.get(rel["end"])
                if country_node and country_node.get("label") == "Country":
                    countries.append(country_node)
                    relationships.append({"start": person_id, "type": "LOCATED_IN", "end": rel["end"]})

        site_names = sorted({str(site["name"]) for site in sites if site.get("name")})
        country_names = sorted({str(country["name"]) for country in countries if country.get("name")})

        if not site_names and not country_names:
            continue

        shown_people.append(str(person_node["name"]))
        top_nodes.append(person_node)
        top_nodes.extend(sites)
        top_nodes.extend(countries)

        if site_names and country_names:
            answers.append(
                f"{person_node['name']} is based at {format_human_list(site_names)} in {format_human_list(country_names)}."
            )
        elif site_names:
            answers.append(f"{person_node['name']} is based at {format_human_list(site_names)}.")
        else:
            answers.append(f"{person_node['name']} is based in {format_human_list(country_names)}.")

    if not answers:
        return None

    seen_top = {}
    for node in top_nodes:
        seen_top[node["id"]] = dict(node, _score=10.0) if "_score" not in node else node
    evidence = {
        "top_nodes": list(seen_top.values()),
        "related_nodes": list(seen_top.values()),
        "relationships": relationships[:24],
    }
    query_state = {
        "kind": "person_location",
        "shown_people": shown_people,
    }
    return "\n".join(answers), evidence, "Graph Search", query_state


def try_person_summary_answer(question: str, indexes: dict[str, Any]) -> tuple[str, dict[str, Any], str] | None:
    normalized = expand_query(question)
    match = re.search(r"(?:tell\s+me\s+everything\s+about|tell\s+me\s+about|what\s+do\s+you\s+know\s+about|everything\s+about)\s+(.+)", normalized)
    if not match:
        return None

    target_phrase = match.group(1).strip(" ?.!<")
    if not target_phrase:
        return None

    person_ids = find_person_ids_for_target(indexes, target_phrase, require_strong_match=True)
    if not person_ids:
        return None

    nodes_by_id = indexes["nodes_by_id"]
    adjacency = indexes["adjacency"]
    answers: list[str] = []
    top_nodes: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []

    for person_id in person_ids:
        person_node = nodes_by_id.get(person_id)
        if not person_node:
            continue

        roles: list[str] = []
        teams: list[str] = []
        sites: list[str] = []
        countries: list[str] = []
        managers: list[str] = []
        skills: list[str] = []
        topics: list[str] = []
        systems: list[str] = []

        top_nodes.append(person_node)

        for rel in adjacency.get(person_id, []):
            rel_type = str(rel["type"])
            node = nodes_by_id.get(rel["end"])
            if not node:
                continue

            if rel_type == "HAS_ROLE" and node.get("label") == "Role":
                roles.append(str(node["name"]))
                top_nodes.append(node)
                relationships.append({"start": person_id, "type": "HAS_ROLE", "end": rel["end"]})
            elif rel_type == "MEMBER_OF" and node.get("label") == "Team":
                teams.append(str(node["name"]))
                top_nodes.append(node)
                relationships.append({"start": person_id, "type": "MEMBER_OF", "end": rel["end"]})
            elif rel_type == "AT_SITE" and node.get("label") == "Site":
                sites.append(str(node["name"]))
                top_nodes.append(node)
                relationships.append({"start": person_id, "type": "AT_SITE", "end": rel["end"]})
            elif rel_type == "LOCATED_IN" and node.get("label") == "Country":
                countries.append(str(node["name"]))
                top_nodes.append(node)
                relationships.append({"start": person_id, "type": "LOCATED_IN", "end": rel["end"]})
            elif rel_type == "REPORTS_TO" and node.get("label") == "Person":
                managers.append(str(node["name"]))
                top_nodes.append(node)
                relationships.append({"start": person_id, "type": "REPORTS_TO", "end": rel["end"]})
            elif rel_type == "HAS_SKILL" and node.get("label") == "Skill":
                skills.append(str(node["name"]))
                top_nodes.append(node)
                relationships.append({"start": person_id, "type": "HAS_SKILL", "end": rel["end"]})
            elif rel_type == "OWNS_TOPIC" and node.get("label") == "Topic":
                topics.append(str(node["name"]))
                top_nodes.append(node)
                relationships.append({"start": person_id, "type": "OWNS_TOPIC", "end": rel["end"]})
            elif rel_type == "KNOWS_SYSTEM" and node.get("label") == "System":
                systems.append(str(node["name"]))
                top_nodes.append(node)
                relationships.append({"start": person_id, "type": "KNOWS_SYSTEM", "end": rel["end"]})

        role_text = format_role_names(sorted(set(roles))) if roles else "no explicitly linked role"
        summary_parts = [f"{person_node['name']} currently holds the {role_text} role." if roles else f"The graph does not show an explicitly linked role for {person_node['name']}."]

        if teams:
            summary_parts.append(f"They are in {format_human_list(sorted(set(teams)))}.")
        if sites and countries:
            summary_parts.append(f"They are based at {format_human_list(sorted(set(sites)))} in {format_human_list(sorted(set(countries)))}.")
        elif sites:
            summary_parts.append(f"They are based at {format_human_list(sorted(set(sites)))}.")
        elif countries:
            summary_parts.append(f"They are based in {format_human_list(sorted(set(countries)))}.")
        if managers:
            summary_parts.append(f"They report to {format_human_list(sorted(set(managers)))}.")
        if skills:
            summary_parts.append(f"Key skills include {format_human_list(sorted(set(skills))[:5])}.")
        if topics:
            summary_parts.append(f"Owned topics include {format_human_list(sorted(set(topics))[:4])}.")
        if systems:
            summary_parts.append(f"Known systems include {format_human_list(sorted(set(systems))[:4])}.")

        answers.append(" ".join(summary_parts))

    if not answers:
        return None

    seen_top = {}
    for node in top_nodes:
        seen_top[node["id"]] = dict(node, _score=10.0) if "_score" not in node else node
    evidence = {
        "top_nodes": list(seen_top.values()),
        "related_nodes": list(seen_top.values()),
        "relationships": relationships[:28],
    }
    return "\n".join(answers), evidence, "Graph Search"


def try_location_people_and_sites_answer(question: str, indexes: dict[str, Any]) -> tuple[str, dict[str, Any], str] | None:
    normalized = expand_query(question)
    if "site" not in normalized and "sites" not in normalized:
        return None

    match = re.search(
        r"who\s+works\s+in\s+(.+?)(?:\s+and\s+what\s+(?:are\s+)?(?:its|their|the)\s+sites?\b|\s+and\s+what\s+sites?\s+are\s+there\b|\s+and\s+which\s+sites?\b)",
        normalized,
    )
    if not match:
        return None

    target_phrase = match.group(1).strip(" ?.")
    if not target_phrase:
        return None

    entity_labels = {"Country", "Site"}
    matched_nodes = find_named_nodes(indexes, target_phrase, entity_labels, limit=5, min_score=30)
    if not matched_nodes:
        countries = sorted(node["name"] for node in indexes["nodes_by_id"].values() if node.get("label") == "Country")
        sites = sorted(node["name"] for node in indexes["nodes_by_id"].values() if node.get("label") == "Site")
        empty_evidence = {"top_nodes": [], "related_nodes": [], "relationships": []}
        answer = (
            f"I could not find the exact location `{display_query_term(target_phrase)}` in the current graph. "
            f"Available countries are {format_human_list(countries)}. "
            f"Available sites include {format_human_list(sites[:8])}."
        )
        return answer, empty_evidence, "Graph Search"

    best = matched_nodes[0]
    label = str(best.get("label"))
    nodes_by_id = indexes["nodes_by_id"]
    adjacency = indexes["adjacency"]
    people: list[dict[str, Any]] = []
    site_nodes: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []

    if label == "Country":
        for rel in adjacency.get(best["id"], []):
            if rel["type"] == "INVERSE_LOCATED_IN":
                person = nodes_by_id.get(rel["end"])
                if person and person.get("label") == "Person":
                    people.append(person)
                    relationships.append({"start": person["id"], "type": "LOCATED_IN", "end": best["id"]})
            elif rel["type"] == "INVERSE_IN_COUNTRY":
                site = nodes_by_id.get(rel["end"])
                if site and site.get("label") == "Site":
                    site_nodes.append(site)
                    relationships.append({"start": site["id"], "type": "IN_COUNTRY", "end": best["id"]})
    else:
        for rel in adjacency.get(best["id"], []):
            if rel["type"] == "INVERSE_AT_SITE":
                person = nodes_by_id.get(rel["end"])
                if person and person.get("label") == "Person":
                    people.append(person)
                    relationships.append({"start": person["id"], "type": "AT_SITE", "end": best["id"]})
        site_nodes.append(best)

    deduped_people = []
    seen_people = set()
    for person in people:
        if person["id"] not in seen_people:
            seen_people.add(person["id"])
            deduped_people.append(person)
    people = deduped_people

    deduped_sites = []
    seen_sites = set()
    for site in site_nodes:
        if site["id"] not in seen_sites:
            seen_sites.add(site["id"])
            deduped_sites.append(site)
    site_nodes = sorted(deduped_sites, key=lambda node: str(node.get("name", "")))

    if not people and not site_nodes:
        empty_evidence = {"top_nodes": [dict(best, _score=best.get("_score", 10.0))], "related_nodes": [best], "relationships": []}
        return f"I found `{best['name']}`, but the current graph does not show people or sites directly linked to it.", empty_evidence, "Graph Search"

    people_names = [person["name"] for person in people]
    site_names = [site["name"] for site in site_nodes]
    answer_parts = []
    if people_names:
        verb = "works" if len(people_names) == 1 else "work"
        answer_parts.append(f"{format_human_list(people_names)} {verb} in `{best['name']}`")
    else:
        answer_parts.append(f"The graph does not show people directly located in `{best['name']}`")

    if site_names:
        site_verb = "site is" if len(site_names) == 1 else "sites are"
        answer_parts.append(f"the recorded {site_verb} {format_human_list(site_names)}")
    else:
        answer_parts.append(f"the graph does not show named sites for `{best['name']}`")

    answer = ". ".join(part[:1].upper() + part[1:] for part in answer_parts if part) + "."
    top_nodes = [dict(best, _score=best.get("_score", 10.0))]
    top_nodes.extend(dict(person, _score=10.0) for person in people[:10])
    top_nodes.extend(dict(site, _score=10.0) for site in site_nodes[:8])
    seen_top = {}
    for node in top_nodes:
        seen_top[node["id"]] = node
    evidence = {
        "top_nodes": list(seen_top.values()),
        "related_nodes": list(seen_top.values()),
        "relationships": relationships[:24],
    }
    return answer, evidence, "Graph Search"


def try_membership_answer(
    question: str,
    indexes: dict[str, Any],
    gemini_model_name: str = "",
    ollama_model_name: str = "",
    ollama_host: str = "",
) -> tuple[str, dict[str, Any], str] | None:
    normalized = expand_query(question)
    match = re.search(r"who\s+is\s+in\s+(.+)", normalized)
    if not match:
        match = re.search(r"who'?s\s+in\s+(.+)", normalized)
    if not match:
        match = re.search(r"who\s+works\s+in\s+(.+)", normalized)
    if not match:
        return None

    target_phrase = match.group(1).strip(" ?.")
    if not target_phrase:
        return None

    entity_labels = {"Department", "Team", "Country", "Site"}
    matched_nodes = find_named_nodes(indexes, target_phrase, entity_labels, limit=5, min_score=30)
    if not matched_nodes:
        countries = sorted(node["name"] for node in indexes["nodes_by_id"].values() if node.get("label") == "Country")
        sites = sorted(node["name"] for node in indexes["nodes_by_id"].values() if node.get("label") == "Site")
        empty_evidence = {"top_nodes": [], "related_nodes": [], "relationships": []}
        answer = (
            f"I could not find the exact team, department, or location `{display_query_term(target_phrase)}` in the current graph. "
            f"Available countries are {format_human_list(countries)}. "
            f"Available sites include {format_human_list(sites[:6])}."
        )
        return answer, empty_evidence, "Graph Search"

    best = matched_nodes[0]
    label = str(best.get("label"))
    nodes_by_id = indexes["nodes_by_id"]
    adjacency = indexes["adjacency"]
    people: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []

    if label == "Team":
        for rel in adjacency.get(best["id"], []):
            if rel["type"] == "INVERSE_MEMBER_OF":
                person = nodes_by_id.get(rel["end"])
                if person and person.get("label") == "Person":
                    people.append(person)
                    relationships.append({"start": person["id"], "type": "MEMBER_OF", "end": best["id"]})
    elif label == "Department":
        role_ids = [rel["end"] for rel in adjacency.get(best["id"], []) if rel["type"] == "INVERSE_BELONGS_TO_DEPARTMENT"]
        seen_people = set()
        for role_id in role_ids:
            role_node = nodes_by_id.get(role_id)
            if role_node:
                relationships.append({"start": role_id, "type": "BELONGS_TO_DEPARTMENT", "end": best["id"]})
            for rel in adjacency.get(role_id, []):
                if rel["type"] == "INVERSE_HAS_ROLE":
                    person = nodes_by_id.get(rel["end"])
                    if person and person.get("label") == "Person" and person["id"] not in seen_people:
                        seen_people.add(person["id"])
                        people.append(person)
                        relationships.append({"start": person["id"], "type": "HAS_ROLE", "end": role_id})
    elif label in {"Country", "Site"}:
        inverse_rel = "INVERSE_LOCATED_IN" if label == "Country" else "INVERSE_AT_SITE"
        direct_rel = "LOCATED_IN" if label == "Country" else "AT_SITE"
        for rel in adjacency.get(best["id"], []):
            if rel["type"] == inverse_rel:
                person = nodes_by_id.get(rel["end"])
                if person and person.get("label") == "Person":
                    people.append(person)
                    relationships.append({"start": person["id"], "type": direct_rel, "end": best["id"]})

    deduped = []
    seen = set()
    for person in people:
        if person["id"] not in seen:
            seen.add(person["id"])
            deduped.append(person)
    people = deduped

    if not people:
        empty_evidence = {"top_nodes": [dict(best, _score=best.get("_score", 10.0))], "related_nodes": [best], "relationships": []}
        return f"I found `{best['name']}`, but the current graph does not show people directly linked to it.", empty_evidence, "Graph Search"

    people_names = [person["name"] for person in people[:8]]
    verb = "is" if len(people_names) == 1 else "are"
    answer = f"{format_human_list(people_names)} {verb} in `{best['name']}`."
    top_nodes = [dict(best, _score=best.get("_score", 10.0))]
    top_nodes.extend(dict(person, _score=10.0) for person in people[:8])
    seen_top = {}
    for node in top_nodes:
        seen_top[node["id"]] = node
    evidence = {
        "top_nodes": list(seen_top.values()),
        "related_nodes": list(seen_top.values()),
        "relationships": relationships[:18],
    }
    return answer, evidence, "Graph Search"


def try_list_entities_answer(question: str, indexes: dict[str, Any]) -> tuple[str, dict[str, Any], str] | None:
    normalized = expand_query(question)
    if not re.search(r"\b(list|show|what are)\b", normalized):
        return None

    target_kind = None
    if re.search(r"\b(location|locations|site|sites|country|countries)\b", normalized):
        target_kind = "locations"
    elif re.search(r"\b(team|teams)\b", normalized):
        target_kind = "teams"
    elif re.search(r"\b(department|departments)\b", normalized):
        target_kind = "departments"
    elif re.search(r"\b(role|roles|position|positions)\b", normalized):
        target_kind = "roles"

    if not target_kind:
        return None

    nodes = indexes["nodes_by_id"].values()
    top_nodes: list[dict[str, Any]] = []

    if target_kind == "locations":
        countries = sorted(node["name"] for node in nodes if node.get("label") == "Country")
        sites = sorted(node["name"] for node in nodes if node.get("label") == "Site")
        answer = f"The company graph currently includes these countries: {format_human_list(countries)}. Key sites include {format_human_list(sites)}."
        top_nodes = [dict(node, _score=10.0) for node in indexes["nodes_by_id"].values() if node.get("label") in {"Country", "Site"}]
    elif target_kind == "teams":
        teams = sorted(node["name"] for node in nodes if node.get("label") == "Team")
        answer = f"The graph currently includes these teams: {format_human_list(teams)}."
        top_nodes = [dict(node, _score=10.0) for node in indexes["nodes_by_id"].values() if node.get("label") == "Team"]
    elif target_kind == "departments":
        departments = sorted(node["name"] for node in nodes if node.get("label") == "Department")
        answer = f"The graph currently includes these departments: {format_human_list(departments)}."
        top_nodes = [dict(node, _score=10.0) for node in indexes["nodes_by_id"].values() if node.get("label") == "Department"]
    else:
        roles = sorted(node["name"] for node in nodes if node.get("label") == "Role")
        answer = f"The graph currently includes these roles: {format_human_list(roles[:20])}."
        top_nodes = [dict(node, _score=10.0) for node in indexes["nodes_by_id"].values() if node.get("label") == "Role"]

    evidence = {
        "top_nodes": top_nodes[:18],
        "related_nodes": top_nodes[:18],
        "relationships": [],
    }
    return answer, evidence, "Graph Search"


def try_knows_answer(
    question: str,
    indexes: dict[str, Any],
    gemini_model_name: str = "",
    ollama_model_name: str = "",
    ollama_host: str = "",
) -> tuple[str, dict[str, Any], str] | None:
    normalized = expand_query(question)
    match = re.search(r"who\s+knows\s+(.+)", normalized)
    if not match:
        return None

    target_phrase = re.sub(r"^(the\s+)?(system|platform|tool|application)\s+", "", match.group(1).strip(" ?."), flags=re.IGNORECASE)
    if not target_phrase:
        return None

    matched_nodes = find_named_nodes(indexes, target_phrase, {"System", "Skill"}, limit=5, min_score=35)
    if not matched_nodes:
        return build_closest_match_suggestion(
            target_phrase,
            indexes,
            {"System", "Skill"},
            f"I could not find an exact system or skill match for `{display_query_term(target_phrase)}` in the current graph.",
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )
    best_score = matched_nodes[0]["_score"]
    matched_nodes = [node for node in matched_nodes if node["_score"] >= best_score - 5][:3]

    nodes_by_id = indexes["nodes_by_id"]
    adjacency = indexes["adjacency"]
    answer_lines = []
    top_nodes = []
    relationships = []

    for node in matched_nodes:
        label = node.get("label")
        inverse_rel = "INVERSE_KNOWS_SYSTEM" if label == "System" else "INVERSE_HAS_SKILL"
        relation_name = "know" if label == "System" else "have as a skill"
        holder_names = []
        top_nodes.append(node)

        for rel in adjacency.get(node["id"], []):
            if rel["type"] != inverse_rel:
                continue
            person_node = nodes_by_id.get(rel["end"])
            if person_node:
                holder_names.append(person_node["name"])
                top_nodes.append(person_node)
                relationships.append({"start": rel["end"], "type": "KNOWS_SYSTEM" if label == "System" else "HAS_SKILL", "end": node["id"]})

        if holder_names:
            verb = "knows" if len(holder_names) == 1 and label == "System" else "know"
            if label == "Skill":
                verb = "has" if len(holder_names) == 1 else "have"
            relation_suffix = f"`{node['name']}`" if label == "System" else f"`{node['name']}` as a skill"
            answer_lines.append(f"{format_human_list(holder_names)} currently {verb} {relation_suffix}.")
        else:
            answer_lines.append(f"The graph contains `{node['name']}`, but no people are currently linked to it.")

    seen_top = {}
    for node in top_nodes:
        seen_top[node["id"]] = node
    evidence = {
        "top_nodes": [dict(node, _score=node.get("_score", 10.0)) for node in seen_top.values()],
        "related_nodes": list(seen_top.values()),
        "relationships": relationships[:18],
    }
    return "\n".join(answer_lines), evidence, "Graph Search"


def try_skill_answer(
    question: str,
    indexes: dict[str, Any],
    gemini_model_name: str = "",
    ollama_model_name: str = "",
    ollama_host: str = "",
) -> tuple[str, dict[str, Any], str] | None:
    normalized = expand_query(question)
    match = re.search(r"who\s+has\s+(?:the\s+)?skill\s+(.+)", normalized)
    if not match:
        match = re.search(r"who\s+has\s+(.+?)\s+skill", normalized)
    if not match:
        return None

    target_phrase = match.group(1).strip(" ?.")
    target_phrase = re.sub(r"\bas\s+a\b", "", target_phrase, flags=re.IGNORECASE).strip()
    if not target_phrase:
        return None

    matched_skills = find_named_nodes(indexes, target_phrase, {"Skill"}, limit=5, min_score=35)
    if not matched_skills:
        return build_closest_match_suggestion(
            target_phrase,
            indexes,
            {"Skill", "System"},
            f"I could not find the exact skill `{display_query_term(target_phrase)}` in the current graph.",
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )
    normalized_target = normalize_target_phrase(target_phrase)
    target_tokens = tokenize(normalized_target)
    is_short_generic = len(target_tokens) == 1 and len(target_tokens[0]) <= 4
    best_score = matched_skills[0]["_score"]
    if is_short_generic:
        broader_matches = find_named_nodes(indexes, target_phrase, {"Skill"}, limit=8, min_score=18)
        matched_skills = broader_matches[:5] if broader_matches else matched_skills[:3]
    else:
        matched_skills = [node for node in matched_skills if node["_score"] >= best_score - 5][:3]

    nodes_by_id = indexes["nodes_by_id"]
    adjacency = indexes["adjacency"]
    answer_lines = []
    top_nodes = []
    relationships = []

    positive_lines = []
    empty_lines = []
    for skill_node in matched_skills:
        holder_names = []
        top_nodes.append(skill_node)
        for rel in adjacency.get(skill_node["id"], []):
            if rel["type"] != "INVERSE_HAS_SKILL":
                continue
            person_node = nodes_by_id.get(rel["end"])
            if person_node:
                holder_names.append(person_node["name"])
                top_nodes.append(person_node)
                relationships.append({"start": rel["end"], "type": "HAS_SKILL", "end": skill_node["id"]})

        if holder_names:
            verb = "has" if len(holder_names) == 1 else "have"
            positive_lines.append(f"{format_human_list(holder_names)} currently {verb} `{skill_node['name']}` listed as a skill.")
        else:
            empty_lines.append(f"The graph contains the skill `{skill_node['name']}`, but no people are currently linked to it.")

    answer_lines.extend(positive_lines)
    answer_lines.extend(empty_lines)

    seen_top = {}
    for node in top_nodes:
        seen_top[node["id"]] = node
    evidence = {
        "top_nodes": [dict(node, _score=node.get("_score", 10.0)) for node in seen_top.values()],
        "related_nodes": list(seen_top.values()),
        "relationships": relationships[:18],
    }
    return "\n".join(answer_lines), evidence, "Graph Search"


def try_people_for_keyword_answer(
    question: str,
    indexes: dict[str, Any],
    exclude_people: set[str] | None = None,
) -> tuple[str, dict[str, Any], str, dict[str, Any]] | None:
    normalized = expand_query(question)
    match = re.search(r"who\s+(?:all\s+)?(?:works?|is\s+working)\s+(?:with|on|in)\s+(.+)", normalized)
    if not match:
        match = re.search(r"which\s+people\s+(?:work|are\s+connected)\s+(?:with|to|on)\s+(.+)", normalized)
    if not match:
        return None

    target_phrase = match.group(1).strip(" ?.")
    if not target_phrase:
        return None

    matched_nodes = find_named_nodes(indexes, target_phrase, {"Skill", "Topic", "System"}, limit=8, min_score=18)
    if not matched_nodes:
        return None

    exclude_people = exclude_people or set()
    person_scores: dict[str, float] = defaultdict(float)
    person_nodes: dict[str, dict[str, Any]] = {}
    supporting_nodes: dict[str, dict[str, Any]] = {}
    relationships: list[dict[str, Any]] = []
    person_reasons: dict[str, list[str]] = defaultdict(list)

    for node in matched_nodes:
        people_names, people_list = related_people_for_node(indexes, node)
        if not people_list:
            continue
        supporting_nodes[node["id"]] = node
        relation_type = {
            "Skill": "HAS_SKILL",
            "Topic": "OWNS_TOPIC",
            "System": "KNOWS_SYSTEM",
        }.get(str(node.get("label")), "RELATED_TO")
        reason_text = {
            "Skill": f"skill `{node['name']}`",
            "Topic": f"topic `{node['name']}`",
            "System": f"system `{node['name']}`",
        }.get(str(node.get("label")), f"graph link `{node['name']}`")
        for person in people_list:
            if person["name"] in exclude_people:
                continue
            person_scores[person["id"]] += float(node.get("_score", 1.0))
            person_nodes[person["id"]] = person
            relationships.append({"start": person["id"], "type": relation_type, "end": node["id"]})
            person_reasons[person["name"]].append(reason_text)

    if not person_scores:
        return None

    ranked_people = sorted(
        person_nodes.values(),
        key=lambda node: (person_scores[node["id"]], node.get("name", "")),
        reverse=True,
    )
    top_people = ranked_people[:5]
    top_names = [node["name"] for node in top_people]
    explanation_parts = []
    for person in top_people[:3]:
        reasons = person_reasons.get(person["name"], [])
        unique_reasons = []
        seen_reasons = set()
        for reason in reasons:
            if reason not in seen_reasons:
                seen_reasons.add(reason)
                unique_reasons.append(reason)
        if unique_reasons:
            explanation_parts.append(f"{person['name']} because of {format_human_list(unique_reasons[:3])}")
        else:
            explanation_parts.append(f"{person['name']} through broader graph relevance")

    if len(top_names) == 1:
        answer = f"{format_human_list(top_names)} is the strongest match for working with `{display_query_term(target_phrase)}`."
    else:
        answer = f"{format_human_list(top_names)} are the strongest matches for working with `{display_query_term(target_phrase)}`."
    if explanation_parts:
        answer += " " + "; ".join(explanation_parts) + "."

    top_nodes = [dict(node, _score=round(person_scores[node["id"]], 2)) for node in top_people]
    top_nodes.extend(list(supporting_nodes.values())[:4])
    seen_top = {}
    for node in top_nodes:
        seen_top[node["id"]] = node
    evidence = {
        "top_nodes": list(seen_top.values()),
        "related_nodes": list(seen_top.values()),
        "relationships": relationships[:18],
    }
    query_state = {
        "kind": "people_for_keyword",
        "question": question,
        "target": target_phrase,
        "shown_people": top_names,
    }
    return answer, evidence, "Graph Search", query_state


def try_more_results_answer(
    question: str,
    indexes: dict[str, Any],
    last_query_state: dict[str, Any] | None,
) -> tuple[str, dict[str, Any], str, dict[str, Any]] | None:
    if not is_more_results_question(question) or not last_query_state:
        return None

    if last_query_state.get("kind") != "people_for_keyword":
        return None

    previous_people = set(last_query_state.get("shown_people", []))
    target = str(last_query_state.get("target", "")).strip()
    if not target:
        return None

    rerun = try_people_for_keyword_answer(f"who works with {target}", indexes, exclude_people=previous_people)
    if not rerun:
        empty_evidence = {"top_nodes": [], "related_nodes": [], "relationships": []}
        return (
            f"I could not find any additional strong matches for `{display_query_term(target)}` in the current graph.",
            empty_evidence,
            "Graph Search",
            last_query_state,
        )

    answer, evidence, backend, query_state = rerun
    answer = answer.replace("are the strongest matches", "are additional matches", 1)
    combined = dict(query_state)
    combined["shown_people"] = list(previous_people) + query_state.get("shown_people", [])
    return answer, evidence, backend, combined


def try_why_followup_answer(
    question: str,
    last_query_state: dict[str, Any] | None,
    last_evidence: dict[str, Any] | None,
) -> tuple[str, dict[str, Any], str, dict[str, Any] | None] | None:
    if not is_why_question(question) or not last_query_state or not last_evidence:
        return None

    if last_query_state.get("kind") != "people_for_keyword":
        return None

    shown_people = list(last_query_state.get("shown_people", []))
    target = str(last_query_state.get("target", "")).strip()
    if not shown_people:
        return None

    nodes_by_id = {
        node["id"]: node
        for node in last_evidence.get("related_nodes", []) + last_evidence.get("top_nodes", [])
        if isinstance(node, dict) and node.get("id")
    }
    person_reasons: dict[str, list[str]] = defaultdict(list)

    for rel in last_evidence.get("relationships", []):
        if not isinstance(rel, dict):
            continue
        start = nodes_by_id.get(rel.get("start"))
        end = nodes_by_id.get(rel.get("end"))
        if not start or not end or start.get("label") != "Person":
            continue
        person_name = str(start.get("name", "")).strip()
        if person_name not in shown_people:
            continue
        rel_type = str(rel.get("type", ""))
        if rel_type == "HAS_SKILL":
            person_reasons[person_name].append(f"linked to the skill `{end.get('name', '')}`")
        elif rel_type == "OWNS_TOPIC":
            person_reasons[person_name].append(f"owns the topic `{end.get('name', '')}`")
        elif rel_type == "KNOWS_SYSTEM":
            person_reasons[person_name].append(f"knows the system `{end.get('name', '')}`")

    lines = [f"They were matched because of their graph links to `{display_query_term(target)}`-related skills, topics, or systems:"]
    for person_name in shown_people:
        reasons = person_reasons.get(person_name, [])
        if reasons:
            lines.append(f"- {person_name}: {format_human_list(reasons[:3])}.")
        else:
            lines.append(f"- {person_name}: appears through broader graph relevance around `{display_query_term(target)}`.")

    return "\n".join(lines), last_evidence, "Graph Search", last_query_state


def try_group_location_followup_answer(
    question: str,
    indexes: dict[str, Any],
    last_query_state: dict[str, Any] | None,
) -> tuple[str, dict[str, Any], str, dict[str, Any] | None] | None:
    if not last_query_state or last_query_state.get("kind") not in {"membership", "people_for_keyword", "person_location"}:
        return None

    normalized = expand_query(question)
    if not re.search(r"\bwhere\b", normalized):
        return None
    if not re.search(r"\b(based|located)\b", normalized):
        return None
    if not re.search(r"\b(they|them|these people|those people)\b", normalized):
        return None

    shown_people = [str(name).strip() for name in last_query_state.get("shown_people", []) if str(name).strip()]
    if not shown_people:
        return None

    nodes_by_id = indexes["nodes_by_id"]
    adjacency = indexes["adjacency"]
    person_ids: list[str] = []
    for person_name in shown_people:
        direct_matches = find_named_nodes(indexes, person_name, {"Person"}, limit=3, min_score=1)
        if direct_matches:
            person_ids.extend([str(node["id"]) for node in direct_matches if node.get("label") == "Person" and node.get("id")])
        else:
            person_ids.extend(find_person_ids_for_target(indexes, person_name, require_strong_match=True))

    deduped_person_ids: list[str] = []
    seen_ids = set()
    for person_id in person_ids:
        if person_id not in seen_ids:
            seen_ids.add(person_id)
            deduped_person_ids.append(person_id)
    person_ids = deduped_person_ids
    if not person_ids:
        return None

    lines: list[str] = []
    top_nodes: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    resolved_people: list[str] = []

    for person_id in person_ids:
        person_node = nodes_by_id.get(person_id)
        if not person_node:
            continue

        sites: list[dict[str, Any]] = []
        countries: list[dict[str, Any]] = []
        for rel in adjacency.get(person_id, []):
            if rel["type"] == "AT_SITE":
                site_node = nodes_by_id.get(rel["end"])
                if site_node and site_node.get("label") == "Site":
                    sites.append(site_node)
                    relationships.append({"start": person_id, "type": "AT_SITE", "end": rel["end"]})
            elif rel["type"] == "LOCATED_IN":
                country_node = nodes_by_id.get(rel["end"])
                if country_node and country_node.get("label") == "Country":
                    countries.append(country_node)
                    relationships.append({"start": person_id, "type": "LOCATED_IN", "end": rel["end"]})

        site_names = sorted({str(site["name"]) for site in sites if site.get("name")})
        country_names = sorted({str(country["name"]) for country in countries if country.get("name")})
        if not site_names and not country_names:
            continue

        resolved_people.append(str(person_node["name"]))
        top_nodes.append(person_node)
        top_nodes.extend(sites)
        top_nodes.extend(countries)

        if site_names and country_names:
            lines.append(f"- {person_node['name']}: based at {format_human_list(site_names)} in {format_human_list(country_names)}.")
        elif site_names:
            lines.append(f"- {person_node['name']}: based at {format_human_list(site_names)}.")
        else:
            lines.append(f"- {person_node['name']}: based in {format_human_list(country_names)}.")

    if not lines:
        return None

    seen_top = {}
    for node in top_nodes:
        seen_top[node["id"]] = dict(node, _score=10.0) if "_score" not in node else node
    evidence = {
        "top_nodes": list(seen_top.values()),
        "related_nodes": list(seen_top.values()),
        "relationships": relationships[:24],
    }
    query_state = {
        "kind": "person_location",
        "shown_people": resolved_people,
    }
    answer = "Here is where they are based:\n" + "\n".join(lines)
    return answer, evidence, "Graph Search", query_state


def try_person_keyword_followup_answer(
    question: str,
    indexes: dict[str, Any],
    last_query_state: dict[str, Any] | None,
) -> tuple[str, dict[str, Any], str, dict[str, Any] | None] | None:
    if not last_query_state or last_query_state.get("kind") != "people_for_keyword":
        return None

    normalized = expand_query(question)
    match = re.search(r"what\s+about\s+(.+)", normalized)
    if not match:
        return None

    target_person = match.group(1).strip(" ?.")
    concept_target = str(last_query_state.get("target", "")).strip()
    if not target_person or not concept_target:
        return None

    person_ids = find_person_ids_for_target(indexes, target_person, require_strong_match=True)
    if not person_ids:
        return None

    matched_nodes = find_named_nodes(indexes, concept_target, {"Skill", "Topic", "System"}, limit=8, min_score=18)
    if not matched_nodes:
        return None

    nodes_by_id = indexes["nodes_by_id"]
    adjacency = indexes["adjacency"]
    person_node = nodes_by_id.get(person_ids[0])
    if not person_node:
        return None

    supporting: list[tuple[str, str, dict[str, Any]]] = []
    for node in matched_nodes:
        for rel in adjacency.get(person_node["id"], []):
            rel_type = str(rel["type"])
            if rel["end"] != node["id"]:
                continue
            if rel_type == "HAS_SKILL":
                supporting.append(("skill", str(node["name"]), {"start": person_node["id"], "type": "HAS_SKILL", "end": node["id"]}))
            elif rel_type == "KNOWS_SYSTEM":
                supporting.append(("system", str(node["name"]), {"start": person_node["id"], "type": "KNOWS_SYSTEM", "end": node["id"]}))
            elif rel_type == "OWNS_TOPIC":
                supporting.append(("topic", str(node["name"]), {"start": person_node["id"], "type": "OWNS_TOPIC", "end": node["id"]}))

    top_nodes = [dict(person_node, _score=10.0)]
    relationships: list[dict[str, Any]] = []
    related_nodes: list[dict[str, Any]] = [dict(person_node, _score=10.0)]
    for kind, node_name, rel in supporting[:4]:
        node = nodes_by_id.get(rel["end"])
        if node:
            top_nodes.append(dict(node, _score=9.0))
            related_nodes.append(dict(node, _score=9.0))
            relationships.append(rel)

    evidence = {
        "top_nodes": top_nodes,
        "related_nodes": related_nodes,
        "relationships": relationships[:18],
    }

    if supporting:
        reason_text = "; ".join(f"{person_node['name']} because of {kind} `{name}`" for kind, name, _ in supporting[:3])
        answer = f"Yes. {reason_text}."
    else:
        answer = f"The current graph does not show strong `{display_query_term(concept_target)}` links for {person_node['name']}."

    return answer, evidence, "Graph Search", last_query_state


def try_group_keyword_followup_answer(
    question: str,
    indexes: dict[str, Any],
    last_query_state: dict[str, Any] | None,
) -> tuple[str, dict[str, Any], str, dict[str, Any] | None] | None:
    if not last_query_state or last_query_state.get("kind") not in {"membership", "people_for_keyword"}:
        return None

    normalized = expand_query(question)
    if "these people" not in normalized and "those people" not in normalized and "they" not in normalized:
        return None

    target_phrase = None
    match = re.search(r"(?:work|works)\s+(?:with|on|in)\s+(.+)", normalized)
    if match:
        target_phrase = match.group(1).strip(" ?.")
    if not target_phrase:
        return None

    shown_people = list(last_query_state.get("shown_people", []))
    if not shown_people:
        return None

    matched_nodes = find_named_nodes(indexes, target_phrase, {"Skill", "Topic", "System"}, limit=8, min_score=18)
    if not matched_nodes:
        return None

    person_reasons: dict[str, list[str]] = defaultdict(list)
    supporting_nodes: dict[str, dict[str, Any]] = {}
    person_nodes: dict[str, dict[str, Any]] = {}
    relationships: list[dict[str, Any]] = []

    for node in matched_nodes:
        supporting_nodes[node["id"]] = node
        relation_type = {
            "Skill": "HAS_SKILL",
            "Topic": "OWNS_TOPIC",
            "System": "KNOWS_SYSTEM",
        }.get(str(node.get("label")), "RELATED_TO")
        reason_text = {
            "Skill": f"skill `{node['name']}`",
            "Topic": f"topic `{node['name']}`",
            "System": f"system `{node['name']}`",
        }.get(str(node.get("label")), f"graph link `{node['name']}`")
        _, people_list = related_people_for_node(indexes, node)
        for person in people_list:
            person_name = person["name"]
            if person_name not in shown_people:
                continue
            person_nodes[person["id"]] = person
            person_reasons[person_name].append(reason_text)
            relationships.append({"start": person["id"], "type": relation_type, "end": node["id"]})

    supported = [name for name in shown_people if person_reasons.get(name)]
    unsupported = [name for name in shown_people if name not in supported]

    if not supported:
        answer = (
            f"The current graph does not show direct `{display_query_term(target_phrase)}`-related evidence for {format_human_list(shown_people)}. "
            f"They may still work with `{display_query_term(target_phrase)}` in reality, but it is not explicitly captured in this graph."
        )
    elif unsupported:
        support_parts = []
        for name in supported:
            reasons = []
            seen = set()
            for reason in person_reasons.get(name, []):
                if reason not in seen:
                    seen.add(reason)
                    reasons.append(reason)
            support_parts.append(f"{name} because of {format_human_list(reasons[:3])}")
        answer = (
            f"Partly. {format_human_list(supported)} has direct `{display_query_term(target_phrase)}` evidence in the graph; "
            + "; ".join(support_parts)
            + f". The current graph does not show equally strong `{display_query_term(target_phrase)}` links for {format_human_list(unsupported)}."
        )
    else:
        support_parts = []
        for name in supported:
            reasons = []
            seen = set()
            for reason in person_reasons.get(name, []):
                if reason not in seen:
                    seen.add(reason)
                    reasons.append(reason)
            support_parts.append(f"{name} because of {format_human_list(reasons[:3])}")
        answer = (
            f"Yes. {format_human_list(supported)} all show direct `{display_query_term(target_phrase)}` evidence in the graph: "
            + "; ".join(support_parts)
            + "."
        )

    top_nodes = [dict(node, _score=10.0) for node in person_nodes.values()]
    top_nodes.extend(list(supporting_nodes.values())[:4])
    seen_top = {}
    for node in top_nodes:
        seen_top[node["id"]] = node
    evidence = {
        "top_nodes": list(seen_top.values()),
        "related_nodes": list(seen_top.values()),
        "relationships": relationships[:18],
    }
    return answer, evidence, "Graph Search", last_query_state


def try_person_concept_answer(
    question: str,
    indexes: dict[str, Any],
    gemini_model_name: str = "",
    ollama_model_name: str = "",
    ollama_host: str = "",
) -> tuple[str, dict[str, Any], str] | None:
    normalized = expand_query(question)
    match = re.search(r"does\s+(.+?)\s+(know|have)\s+(.+)", normalized)
    if not match:
        return None

    person_phrase = match.group(1).strip(" ?.")
    relation_verb = match.group(2).strip()
    concept_phrase = match.group(3).strip(" ?.")
    concept_phrase = re.sub(r"\bas\s+a\s+skill\b", "", concept_phrase, flags=re.IGNORECASE).strip()
    if not person_phrase or not concept_phrase:
        return None

    person_ids = find_person_ids_for_target(indexes, person_phrase, require_strong_match=True)
    if not person_ids:
        return build_closest_match_suggestion(
            person_phrase,
            indexes,
            {"Person", "Role"},
            f"I could not find the exact person or role `{display_query_term(person_phrase)}` in the current graph.",
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )

    matched_nodes = find_named_nodes(indexes, concept_phrase, {"Skill", "System", "Topic"}, limit=6, min_score=18)
    if not matched_nodes:
        return build_closest_match_suggestion(
            concept_phrase,
            indexes,
            {"Skill", "System", "Topic"},
            f"I could not find a confident concept match for `{display_query_term(concept_phrase)}` in the current graph.",
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )

    nodes_by_id = indexes["nodes_by_id"]
    adjacency = indexes["adjacency"]
    person_node = nodes_by_id.get(person_ids[0])
    if not person_node:
        return None

    support_lines: list[str] = []
    top_nodes = [dict(person_node, _score=10.0)]
    relationships: list[dict[str, Any]] = []
    seen_support = set()

    for node in matched_nodes:
        for rel in adjacency.get(person_node["id"], []):
            if rel["end"] != node["id"]:
                continue
            rel_type = str(rel["type"])
            if rel_type == "HAS_SKILL":
                support_lines.append(f"{person_node['name']} currently has `{node['name']}` as a skill.")
            elif rel_type == "KNOWS_SYSTEM":
                support_lines.append(f"{person_node['name']} currently knows the system `{node['name']}`.")
            elif rel_type == "OWNS_TOPIC":
                support_lines.append(f"{person_node['name']} is currently linked to the topic `{node['name']}`.")
            else:
                continue
            if node["id"] not in seen_support:
                seen_support.add(node["id"])
                top_nodes.append(dict(node, _score=9.0))
            relationships.append({"start": person_node["id"], "type": rel_type, "end": node["id"]})

    if not support_lines:
        empty_evidence = {"top_nodes": [dict(person_node, _score=10.0)], "related_nodes": [dict(person_node, _score=10.0)], "relationships": []}
        if relation_verb == "know":
            return f"The current graph does not show `{display_query_term(concept_phrase)}` as something {person_node['name']} currently knows.", empty_evidence, "Graph Search"
        return f"The current graph does not show `{display_query_term(concept_phrase)}` as a current skill or topic link for {person_node['name']}.", empty_evidence, "Graph Search"

    evidence = {
        "top_nodes": top_nodes,
        "related_nodes": top_nodes,
        "relationships": relationships[:18],
    }
    return " ".join(support_lines[:3]), evidence, "Graph Search"


def try_group_relationship_followup_answer(
    question: str,
    indexes: dict[str, Any],
    last_query_state: dict[str, Any] | None,
) -> tuple[str, dict[str, Any], str, dict[str, Any] | None] | None:
    if not last_query_state or last_query_state.get("kind") not in {"membership", "people_for_keyword"}:
        return None

    normalized = expand_query(question)
    if not re.search(r"\b(do|are)\s+(they|these people|those people)\b", normalized):
        return None
    if not re.search(r"\b(work with each other|work together|collaborate|know each other)\b", normalized):
        return None

    shown_people = list(last_query_state.get("shown_people", []))
    if len(shown_people) < 2:
        return None

    nodes_by_id = indexes["nodes_by_id"]
    adjacency = indexes["adjacency"]
    people_by_name = {
        str(node.get("name", "")).strip(): node
        for node in nodes_by_id.values()
        if node.get("label") == "Person" and node.get("name")
    }
    group_people = [people_by_name[name] for name in shown_people if name in people_by_name]
    if len(group_people) < 2:
        return None

    group_ids = {person["id"] for person in group_people}
    direct_reporting_pairs = []
    shared_teams: dict[str, list[str]] = defaultdict(list)
    shared_departments: dict[str, list[str]] = defaultdict(list)
    relationships: list[dict[str, Any]] = []
    top_nodes = [dict(person, _score=10.0) for person in group_people]

    for person in group_people:
        person_id = person["id"]
        person_name = person["name"]
        for rel in adjacency.get(person_id, []):
            rel_type = str(rel["type"])
            end_node = nodes_by_id.get(rel["end"])
            if not end_node:
                continue
            if rel_type == "REPORTS_TO" and rel["end"] in group_ids:
                direct_reporting_pairs.append(f"{person_name} reports to {end_node['name']}")
                relationships.append({"start": person_id, "type": "REPORTS_TO", "end": rel["end"]})
                top_nodes.append(dict(end_node, _score=10.0))
            elif rel_type == "MEMBER_OF" and end_node.get("label") == "Team":
                shared_teams[end_node["name"]].append(person_name)
                relationships.append({"start": person_id, "type": "MEMBER_OF", "end": rel["end"]})
                top_nodes.append(dict(end_node, _score=9.0))
            elif rel_type == "HAS_ROLE":
                for role_rel in adjacency.get(rel["end"], []):
                    if role_rel["type"] == "BELONGS_TO_DEPARTMENT":
                        dept_node = nodes_by_id.get(role_rel["end"])
                        if dept_node and dept_node.get("label") == "Department":
                            shared_departments[dept_node["name"]].append(person_name)
                            relationships.append({"start": rel["end"], "type": "BELONGS_TO_DEPARTMENT", "end": role_rel["end"]})
                            top_nodes.append(dict(dept_node, _score=8.5))

    team_statements = [
        f"{format_human_list(sorted(set(members)))} are in the team `{team}`"
        for team, members in shared_teams.items()
        if len(set(members)) >= 2
    ]
    department_statements = [
        f"{format_human_list(sorted(set(members)))} are in the department `{department}`"
        for department, members in shared_departments.items()
        if len(set(members)) >= 2
    ]

    if direct_reporting_pairs or team_statements or department_statements:
        lines = ["The graph suggests they are connected:"]
        if direct_reporting_pairs:
            for statement in sorted(set(direct_reporting_pairs)):
                lines.append(f"- {statement}.")
        if team_statements:
            for statement in sorted(set(team_statements)):
                lines.append(f"- {statement}.")
        if department_statements:
            for statement in sorted(set(department_statements)):
                lines.append(f"- {statement}.")
        lines.append("So while the graph does not contain an explicit `COLLABORATES_WITH` edge, it does show organizational links between them.")
        answer = "\n".join(lines)
    else:
        answer = (
            f"The graph does not show explicit collaboration links between {format_human_list(shown_people)}. "
            "That does not mean they do not work together in reality; it only means the current graph does not capture direct evidence for it."
        )

    seen_top = {}
    for node in top_nodes:
        seen_top[node["id"]] = node
    evidence = {
        "top_nodes": list(seen_top.values()),
        "related_nodes": list(seen_top.values()),
        "relationships": relationships[:18],
    }
    return answer, evidence, "Graph Search", last_query_state


def try_confirmation_followup_answer(
    question: str,
    indexes: dict[str, Any],
    last_query_state: dict[str, Any] | None,
    gemini_model_name: str = "",
    ollama_model_name: str = "",
    ollama_host: str = "",
) -> tuple[str, dict[str, Any], str, dict[str, Any] | None] | None:
    if not last_query_state or last_query_state.get("kind") != "pending_suggestion":
        return None

    normalized = expand_query(question)
    if not re.fullmatch(r"\s*(yes|yes please|yes her|yes him|yes that one|yes that person|yes that role|okay|ok)\s*\??\s*", normalized):
        return None

    suggested_name = str(last_query_state.get("suggested_name", "")).strip()
    original_intent = str(last_query_state.get("intent", "")).strip()
    if not suggested_name or not original_intent:
        return None

    if original_intent == "person_work_with":
        rerun = try_person_work_with_answer(
            f"who does {suggested_name} work with",
            indexes,
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )
        if rerun:
            answer, evidence, backend = rerun
            query_state = {"kind": "person_collaboration", "target": suggested_name}
            return answer, evidence, backend, query_state

    return None


def try_relationship_followup_answer(
    question: str,
    indexes: dict[str, Any],
    last_query_state: dict[str, Any] | None,
    gemini_model_name: str = "",
    ollama_model_name: str = "",
    ollama_host: str = "",
) -> tuple[str, dict[str, Any], str, dict[str, Any] | None] | None:
    if not last_query_state or last_query_state.get("kind") != "relationship_pair":
        return None

    normalized = expand_query(question)
    match = re.search(r"what\s+about\s+(.+)", normalized)
    if not match:
        return None

    new_target = match.group(1).strip(" ?.")
    left_name = str(last_query_state.get("left_name", "")).strip()
    right_name = str(last_query_state.get("right_name", "")).strip()
    if not new_target or not left_name or not right_name:
        return None

    left_answer = try_node_relationship_answer(
        f"how is {new_target} related to {left_name}",
        indexes,
        gemini_model_name,
        ollama_model_name,
        ollama_host,
    )
    right_answer = try_node_relationship_answer(
        f"how is {new_target} related to {right_name}",
        indexes,
        gemini_model_name,
        ollama_model_name,
        ollama_host,
    )

    usable_answers = [item for item in [left_answer, right_answer] if item]
    if not usable_answers:
        return None

    answer_parts: list[str] = []
    top_nodes: dict[str, dict[str, Any]] = {}
    relationships: list[dict[str, Any]] = []
    for answer_text, evidence, _backend in usable_answers:
        answer_parts.append(answer_text)
        for node in evidence.get("top_nodes", []) + evidence.get("related_nodes", []):
            if isinstance(node, dict) and node.get("id"):
                top_nodes[node["id"]] = node
        for rel in evidence.get("relationships", []):
            if isinstance(rel, dict):
                relationships.append(rel)

    evidence = {
        "top_nodes": list(top_nodes.values()),
        "related_nodes": list(top_nodes.values()),
        "relationships": relationships[:24],
    }
    query_state = {
        "kind": "relationship_pair",
        "left_name": left_name,
        "right_name": right_name,
        "expanded_with": new_target,
    }
    return "\n\n".join(answer_parts), evidence, "Graph Search", query_state


def try_other_people_with_name_answer(
    question: str,
    indexes: dict[str, Any],
    last_evidence: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any], str, dict[str, Any] | None] | None:
    normalized = expand_query(question)
    match = re.search(r"(?:are\s+there\s+)?any\s+other\s+([a-zA-Z\u00C0-\u017F]+)", normalized)
    if not match:
        return None

    raw_target = match.group(1).strip(" ?.")
    if not raw_target:
        return None

    target = strip_diacritics(raw_target.casefold())
    if target.endswith("ies") and len(target) > 4:
        target = target[:-3] + "y"
    elif target.endswith("s") and len(target) > 3:
        target = target[:-1]

    matched_people: list[dict[str, Any]] = []
    for node in indexes["nodes_by_id"].values():
        if node.get("label") != "Person" or not node.get("name"):
            continue
        first_name = strip_diacritics(str(node["name"]).split()[0].casefold())
        ratio = SequenceMatcher(None, first_name, target).ratio()
        if first_name == target or ratio >= 0.88:
            matched_people.append(node)

    if not matched_people:
        empty_evidence = {"top_nodes": [], "related_nodes": [], "relationships": []}
        return (
            f"I could not find any people with a first name close to `{display_query_term(raw_target)}` in the current graph.",
            empty_evidence,
            "Graph Search",
            None,
        )

    already_shown_ids: set[str] = set()
    if last_evidence:
        for node in last_evidence.get("top_nodes", []) + last_evidence.get("related_nodes", []):
            if isinstance(node, dict) and node.get("label") == "Person" and node.get("id"):
                node_first = strip_diacritics(str(node.get("name", "")).split()[0].casefold()) if node.get("name") else ""
                if node_first == target:
                    already_shown_ids.add(str(node["id"]))

    remaining = [person for person in matched_people if str(person["id"]) not in already_shown_ids]
    focus_people = remaining or matched_people
    people_names = [str(person["name"]) for person in focus_people[:8]]
    top_nodes = [dict(person, _score=10.0) for person in focus_people[:8]]
    evidence = {"top_nodes": top_nodes, "related_nodes": top_nodes, "relationships": []}

    if remaining:
        verb = "is" if len(people_names) == 1 else "are"
        answer = f"{format_human_list(people_names)} {verb} other people with the first name `{display_query_term(target)}` in the current graph."
    elif len(matched_people) == 1:
        answer = f"I could not find any other people named `{display_query_term(target)}` in the current graph. The only match is {matched_people[0]['name']}."
    else:
        answer = f"I could not find additional people beyond {format_human_list([str(person['name']) for person in matched_people[:8]])} with the first name `{display_query_term(target)}` in the current graph."

    query_state = {
        "kind": "name_listing",
        "target_first_name": target,
        "shown_people": people_names,
    }
    return answer, evidence, "Graph Search", query_state


def try_person_work_with_answer(
    question: str,
    indexes: dict[str, Any],
    gemini_model_name: str = "",
    ollama_model_name: str = "",
    ollama_host: str = "",
) -> tuple[str, dict[str, Any], str] | None:
    normalized = expand_query(question)
    match = re.search(r"who(?:\s+else)?\s+does\s+(.+?)\s+work\s+with", normalized)
    if not match:
        match = re.search(r"who\s+works\s+with\s+(.+)", normalized)
    if not match:
        return None

    target_phrase = match.group(1).strip(" ?.")
    if not target_phrase:
        return None

    strong_entity_nodes = find_named_nodes(
        indexes,
        target_phrase,
        {"Person", "Role", "JobDescription", "Department", "Team", "Country", "Site", "Skill", "Topic", "System"},
        limit=5,
        min_score=30,
    )
    if not strong_entity_nodes:
        near_person_or_role = find_named_nodes(indexes, target_phrase, {"Person", "Role", "JobDescription"}, limit=3, min_score=18)
        if near_person_or_role:
            return build_closest_match_suggestion(
                target_phrase,
                indexes,
                {"Person", "Role", "JobDescription"},
                f"I could not find the exact person or role `{display_query_term(target_phrase)}` in the current graph.",
                gemini_model_name,
                ollama_model_name,
                ollama_host,
            )

        near_concepts = find_named_nodes(indexes, target_phrase, {"Skill", "Topic", "System", "Department", "Team", "Country", "Site"}, limit=3, min_score=18)
        if near_concepts:
            best_entity = near_concepts[0]
            strong_entity_nodes = [best_entity]
        else:
            empty_evidence = {"top_nodes": [], "related_nodes": [], "relationships": []}
            return (
                f"I could not find a confident person, role, or concept match for `{display_query_term(target_phrase)}` in the current graph.",
                empty_evidence,
                "Graph Search",
            )

    best_entity = strong_entity_nodes[0]
    best_label = str(best_entity.get("label"))
    person_ids = find_person_ids_for_target(indexes, target_phrase, require_strong_match=True)

    if best_label in {"Department", "Team", "Country", "Site"}:
        nodes_by_id = indexes["nodes_by_id"]
        adjacency = indexes["adjacency"]
        people: list[dict[str, Any]] = []
        relationships: list[dict[str, Any]] = []

        if best_label == "Team":
            for rel in adjacency.get(best_entity["id"], []):
                if rel["type"] == "INVERSE_MEMBER_OF":
                    person = nodes_by_id.get(rel["end"])
                    if person and person.get("label") == "Person":
                        people.append(person)
                        relationships.append({"start": person["id"], "type": "MEMBER_OF", "end": best_entity["id"]})
        elif best_label == "Department":
            role_ids = [rel["end"] for rel in adjacency.get(best_entity["id"], []) if rel["type"] == "INVERSE_BELONGS_TO_DEPARTMENT"]
            seen_people = set()
            for role_id in role_ids:
                role_node = nodes_by_id.get(role_id)
                if role_node:
                    relationships.append({"start": role_id, "type": "BELONGS_TO_DEPARTMENT", "end": best_entity["id"]})
                for rel in adjacency.get(role_id, []):
                    if rel["type"] == "INVERSE_HAS_ROLE":
                        person = nodes_by_id.get(rel["end"])
                        if person and person.get("label") == "Person" and person["id"] not in seen_people:
                            seen_people.add(person["id"])
                            people.append(person)
                            relationships.append({"start": person["id"], "type": "HAS_ROLE", "end": role_id})
        else:
            inverse_rel = "INVERSE_LOCATED_IN" if best_label == "Country" else "INVERSE_AT_SITE"
            direct_rel = "LOCATED_IN" if best_label == "Country" else "AT_SITE"
            for rel in adjacency.get(best_entity["id"], []):
                if rel["type"] == inverse_rel:
                    person = nodes_by_id.get(rel["end"])
                    if person and person.get("label") == "Person":
                        people.append(person)
                        relationships.append({"start": person["id"], "type": direct_rel, "end": best_entity["id"]})

        deduped_people = []
        seen_people = set()
        for person in people:
            if person["id"] not in seen_people:
                seen_people.add(person["id"])
                deduped_people.append(person)
        people = deduped_people

        if not people:
            return None

        people_names = [person["name"] for person in people[:8]]
        verb = "is" if len(people_names) == 1 else "are"
        answer = f"{format_human_list(people_names)} {verb} most directly associated in the graph with `{best_entity['name']}`."
        top_nodes = [dict(best_entity, _score=best_entity.get("_score", 10.0))]
        top_nodes.extend(dict(person, _score=10.0) for person in people[:8])
        seen_top = {}
        for node in top_nodes:
            seen_top[node["id"]] = node
        evidence = {
            "top_nodes": list(seen_top.values()),
            "related_nodes": list(seen_top.values()),
            "relationships": relationships[:18],
        }

        return answer, evidence, "Graph Search"

    if best_label in {"Skill", "Topic", "System"}:
        return None

    if not person_ids and best_label in {"Person", "Role", "JobDescription"}:
        return build_closest_match_suggestion(
            target_phrase,
            indexes,
            {"Person", "Role"},
            f"I could not find the exact person or role `{display_query_term(target_phrase)}` in the current graph.",
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )
    if not person_ids:
        return None

    nodes_by_id = indexes["nodes_by_id"]
    adjacency = indexes["adjacency"]
    answer_lines = []
    top_nodes = []
    relationships = []

    for person_id in person_ids:
        person_node = nodes_by_id.get(person_id)
        if not person_node:
            continue
        person_name = person_node["name"]
        top_nodes.append(person_node)

        collaborators: dict[str, list[str]] = defaultdict(list)

        for rel in adjacency.get(person_id, []):
            rel_type = str(rel["type"])
            end_node = nodes_by_id.get(rel["end"])
            if not end_node:
                continue

            if rel_type == "REPORTS_TO" and end_node.get("label") == "Person":
                collaborators[end_node["name"]].append("reporting line")
                top_nodes.append(end_node)
                relationships.append({"start": person_id, "type": "REPORTS_TO", "end": end_node["id"]})
            elif rel_type == "INVERSE_REPORTS_TO" and end_node.get("label") == "Person":
                collaborators[end_node["name"]].append("reporting line")
                top_nodes.append(end_node)
                relationships.append({"start": end_node["id"], "type": "REPORTS_TO", "end": person_id})
            elif rel_type == "MEMBER_OF" and end_node.get("label") == "Team":
                team_name = end_node["name"]
                top_nodes.append(end_node)
                relationships.append({"start": person_id, "type": "MEMBER_OF", "end": end_node["id"]})
                for team_rel in adjacency.get(end_node["id"], []):
                    if team_rel["type"] == "INVERSE_MEMBER_OF":
                        teammate = nodes_by_id.get(team_rel["end"])
                        if teammate and teammate.get("label") == "Person" and teammate["id"] != person_id:
                            collaborators[teammate["name"]].append(f"team `{team_name}`")
                            top_nodes.append(teammate)
                            relationships.append({"start": teammate["id"], "type": "MEMBER_OF", "end": end_node["id"]})

        if not collaborators:
            answer_lines.append(
                f"The graph does not show direct people links for {person_name} beyond their individual role, skills, topics, and systems."
            )
            continue

        collaborator_names = list(collaborators.keys())
        reason_parts = []
        for collaborator_name in collaborator_names[:5]:
            reasons = []
            seen = set()
            for reason in collaborators[collaborator_name]:
                if reason not in seen:
                    seen.add(reason)
                    reasons.append(reason)
            reason_parts.append(f"{collaborator_name} through {format_human_list(reasons)}")

        answer_lines.append(
            f"{person_name} is most directly connected in the graph to {format_human_list(collaborator_names[:5])}. "
            + "; ".join(reason_parts)
            + "."
        )

    if not answer_lines:
        return None

    seen_top = {}
    for node in top_nodes:
        seen_top[node["id"]] = node
    evidence = {
        "top_nodes": [dict(node, _score=10.0) if "_score" not in node else node for node in seen_top.values()],
        "related_nodes": list(seen_top.values()),
        "relationships": relationships[:20],
    }
    return "\n".join(answer_lines), evidence, "Graph Search"


def try_node_relationship_answer(
    question: str,
    indexes: dict[str, Any],
    gemini_model_name: str = "",
    ollama_model_name: str = "",
    ollama_host: str = "",
) -> tuple[str, dict[str, Any], str] | None:
    normalized = expand_query(question)
    via_match = re.search(r"(?:are|is)\s+(.+?)\s+and\s+(.+?)\s+connected\s+(?:through|via)\s+(.+)", normalized)
    if via_match:
        left_phrase = via_match.group(1).strip(" ?.")
        right_phrase = via_match.group(2).strip(" ?.")
        via_phrase = via_match.group(3).strip(" ?.")
        if not left_phrase or not right_phrase or not via_phrase:
            return None

        left_node = resolve_best_entity(indexes, left_phrase)
        right_node = resolve_best_entity(indexes, right_phrase)
        via_node = resolve_best_entity(indexes, via_phrase)
        if not left_node:
            return build_closest_match_suggestion(
                left_phrase,
                indexes,
                {"Person", "Role", "JobDescription", "Department", "Team", "Country", "Site", "Skill", "Topic", "System"},
                f"I could not find the exact node `{display_query_term(left_phrase)}` in the current graph.",
                gemini_model_name,
                ollama_model_name,
                ollama_host,
            )
        if not right_node:
            return build_closest_match_suggestion(
                right_phrase,
                indexes,
                {"Person", "Role", "JobDescription", "Department", "Team", "Country", "Site", "Skill", "Topic", "System"},
                f"I could not find the exact node `{display_query_term(right_phrase)}` in the current graph.",
                gemini_model_name,
                ollama_model_name,
                ollama_host,
            )
        if not via_node:
            return build_closest_match_suggestion(
                via_phrase,
                indexes,
                {"Person", "Role", "JobDescription", "Department", "Team", "Country", "Site", "Skill", "Topic", "System"},
                f"I could not find the exact node `{display_query_term(via_phrase)}` in the current graph.",
                gemini_model_name,
                ollama_model_name,
                ollama_host,
            )

        left_path = find_shortest_relationship_path(indexes, left_node["id"], via_node["id"], max_depth=2) or find_shortest_relationship_path(indexes, via_node["id"], left_node["id"], max_depth=2)
        right_path = find_shortest_relationship_path(indexes, right_node["id"], via_node["id"], max_depth=2) or find_shortest_relationship_path(indexes, via_node["id"], right_node["id"], max_depth=2)
        if not left_path or not right_path:
            evidence = {
                "top_nodes": [dict(left_node, _score=10.0), dict(right_node, _score=10.0), dict(via_node, _score=10.0)],
                "related_nodes": [dict(left_node, _score=10.0), dict(right_node, _score=10.0), dict(via_node, _score=10.0)],
                "relationships": [],
            }
            return (
                f"The current graph does not show a clear relationship path linking `{left_node['name']}` and `{right_node['name']}` through `{via_node['name']}`.",
                evidence,
                "Graph Search",
            )

        nodes_by_id = indexes["nodes_by_id"]
        top_nodes = {
            left_node["id"]: dict(left_node, _score=10.0),
            right_node["id"]: dict(right_node, _score=10.0),
            via_node["id"]: dict(via_node, _score=10.0),
        }
        relationships: list[dict[str, Any]] = []
        left_steps: list[str] = []
        right_steps: list[str] = []
        for rel in left_path:
            start_node = nodes_by_id.get(rel["start"], {"id": rel["start"], "name": rel["start"]})
            end_node = nodes_by_id.get(rel["end"], {"id": rel["end"], "name": rel["end"]})
            top_nodes[start_node["id"]] = dict(start_node, _score=9.0)
            top_nodes[end_node["id"]] = dict(end_node, _score=9.0)
            relationships.append({"start": rel["start"], "type": rel["type"], "end": rel["end"]})
            left_steps.append(describe_relationship_step(start_node, str(rel["type"]), end_node))
        for rel in right_path:
            start_node = nodes_by_id.get(rel["start"], {"id": rel["start"], "name": rel["start"]})
            end_node = nodes_by_id.get(rel["end"], {"id": rel["end"], "name": rel["end"]})
            top_nodes[start_node["id"]] = dict(start_node, _score=9.0)
            top_nodes[end_node["id"]] = dict(end_node, _score=9.0)
            relationships.append({"start": rel["start"], "type": rel["type"], "end": rel["end"]})
            right_steps.append(describe_relationship_step(start_node, str(rel["type"]), end_node))

        answer = (
            f"Yes. The graph connects `{left_node['name']}` and `{right_node['name']}` through `{via_node['name']}`.\n"
            + "\n".join(f"- {step}." for step in left_steps + right_steps)
        )
        evidence = {
            "top_nodes": list(top_nodes.values()),
            "related_nodes": list(top_nodes.values()),
            "relationships": relationships[:24],
        }
        return answer, evidence, "Graph Search"

    patterns = [
        r"how\s+is\s+(.+?)\s+related\s+to\s+(.+)",
        r"(?:what\s+is\s+the\s+|any\s+)?relationship\s+between\s+(.+?)\s+and\s+(.+)",
        r"is\s+(.+?)\s+related\s+to\s+(.+)",
        r"is\s+(.+?)\s+connected\s+to\s+(.+)",
        r"(?:is|are)\s+(.+?)\s+and\s+(.+?)\s+connected(?:\s+somehow)?",
        r"does\s+(.+?)\s+work\s+with\s+(.+)",
    ]
    match = None
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            break
    if not match:
        return None

    left_phrase = match.group(1).strip(" ?.")
    right_phrase = match.group(2).strip(" ?.")
    if not left_phrase or not right_phrase:
        return None

    left_node = resolve_best_entity(indexes, left_phrase)
    right_node = resolve_best_entity(indexes, right_phrase)

    if not left_node:
        return build_closest_match_suggestion(
            left_phrase,
            indexes,
            {"Person", "Role", "JobDescription", "Department", "Team", "Country", "Site", "Skill", "Topic", "System"},
            f"I could not find the exact node `{display_query_term(left_phrase)}` in the current graph.",
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )
    if not right_node:
        return build_closest_match_suggestion(
            right_phrase,
            indexes,
            {"Person", "Role", "JobDescription", "Department", "Team", "Country", "Site", "Skill", "Topic", "System"},
            f"I could not find the exact node `{display_query_term(right_phrase)}` in the current graph.",
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )

    path = find_shortest_relationship_path(indexes, left_node["id"], right_node["id"], max_depth=3)
    if not path:
        reverse_path = find_shortest_relationship_path(indexes, right_node["id"], left_node["id"], max_depth=3)
        path = reverse_path
        if path:
            left_node, right_node = right_node, left_node

    if not path:
        top_nodes = [dict(left_node, _score=10.0), dict(right_node, _score=10.0)]
        evidence = {"top_nodes": top_nodes, "related_nodes": top_nodes, "relationships": []}
        answer = (
            f"The current graph does not show an explicit direct relationship path between `{left_node['name']}` "
            f"and `{right_node['name']}` within the supported graph depth."
        )
        return answer, evidence, "Graph Search"

    nodes_by_id = indexes["nodes_by_id"]
    top_nodes = {left_node["id"]: dict(left_node, _score=10.0), right_node["id"]: dict(right_node, _score=10.0)}
    compact_relationships: list[dict[str, Any]] = []
    step_texts: list[str] = []
    current_id = left_node["id"]
    for rel in path:
        start_node = nodes_by_id.get(rel["start"], {"id": rel["start"], "name": rel["start"]})
        end_node = nodes_by_id.get(rel["end"], {"id": rel["end"], "name": rel["end"]})
        top_nodes[start_node["id"]] = dict(start_node, _score=9.0)
        top_nodes[end_node["id"]] = dict(end_node, _score=9.0)
        compact_relationships.append({"start": rel["start"], "type": rel["type"], "end": rel["end"]})
        step_texts.append(describe_relationship_step(start_node, str(rel["type"]), end_node))
        current_id = rel["end"]

    answer = (
        f"The graph links `{left_node['name']}` and `{right_node['name']}` through this path:\n"
        + "\n".join(f"- {step}." for step in step_texts)
    )
    evidence = {
        "top_nodes": list(top_nodes.values()),
        "related_nodes": list(top_nodes.values()),
        "relationships": compact_relationships[:18],
    }
    return answer, evidence, "Graph Search"


def is_identity_question(question: str) -> bool:
    normalized = expand_query(question)
    if re.search(r"\b(?:boss|manager|supervisor)\b", normalized):
        return False
    if re.search(r"\b(?:does\s+.+\s+report\s+to|reporting\s+to)\b", normalized):
        return False
    return bool(re.search(r"^\s*who\s+is\s+.+", normalized))


def build_similar_role_suggestion(
    question: str,
    indexes: dict[str, Any],
    gemini_model_name: str = "",
    ollama_model_name: str = "",
    ollama_host: str = "",
) -> tuple[str, dict[str, Any], str] | None:
    normalized = expand_query(question)
    match = re.search(r"^\s*who\s+is\s+(.+)", normalized)
    if not match:
        return None

    target_phrase = match.group(1).strip(" ?.")
    config = load_query_normalization()
    suggested_roles = config.get("similar_roles", {}).get(target_phrase, [])
    if not suggested_roles:
        return None

    nodes_by_id = indexes["nodes_by_id"]
    adjacency = indexes["adjacency"]
    top_nodes: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    answer_lines = [f"I could not find the exact title `{target_phrase.title()}` in the current graph."]

    for role_name in suggested_roles:
        matched_role = None
        for node in nodes_by_id.values():
            if node.get("label") == "Role" and str(node.get("name", "")).casefold() == role_name.casefold():
                matched_role = node
                break
        if not matched_role:
            continue

        top_nodes.append(dict(matched_role, _score=6.0))
        holders = []
        for rel in adjacency.get(matched_role["id"], []):
            if rel["type"] == "INVERSE_HAS_ROLE":
                person_node = nodes_by_id.get(rel["end"])
                if person_node:
                    holders.append(person_node["name"])
                    top_nodes.append(dict(person_node, _score=6.0))
                    relationships.append({"start": rel["end"], "type": "HAS_ROLE", "end": matched_role["id"]})

        if holders:
            holders_text = ", ".join(holders[:-1]) + (" and " + holders[-1] if len(holders) > 1 else holders[0])
            answer_lines.append(f"A close related role in this graph is `{matched_role['name']}`, which is currently held by {holders_text}.")
        else:
            answer_lines.append(f"A close related role in this graph is `{matched_role['name']}`.")

    if len(answer_lines) == 1:
        generic = build_closest_match_suggestion(
            target_phrase,
            indexes,
            {"Role", "Person", "JobDescription"},
            f"I could not find the exact title `{display_query_term(target_phrase)}` in the current graph.",
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )
        return generic

    seen = {}
    for node in top_nodes:
        seen[node["id"]] = node
    evidence = {
        "top_nodes": list(seen.values()),
        "related_nodes": list(seen.values()),
        "relationships": relationships[:18],
    }
    return "\n".join(answer_lines), evidence, "Graph Search"


def summarize_node(node: dict[str, Any]) -> str:
    highlights = []
    for key in ("department", "team", "country", "location_context", "role_level"):
        if node.get(key):
            highlights.append(f"{key.replace('_', ' ').title()}: {node[key]}")
    return " | ".join(highlights)


def build_evidence(indexes: dict[str, Any], query: str, node_limit: int = 6, rel_limit: int = 18) -> dict[str, Any]:
    top_nodes = find_relevant_nodes(indexes, query, limit=node_limit)
    nodes_by_id = indexes["nodes_by_id"]
    adjacency = indexes["adjacency"]

    selected_nodes = {node["id"]: node for node in top_nodes}
    selected_relationships: list[dict[str, Any]] = []

    for node in top_nodes:
        for rel in adjacency.get(node["id"], [])[:rel_limit]:
            selected_relationships.append(rel)
            neighbor_id = rel["end"]
            if neighbor_id in nodes_by_id and len(selected_nodes) < node_limit * 3:
                selected_nodes.setdefault(neighbor_id, nodes_by_id[neighbor_id])

    compact_relationships = []
    seen = set()
    for rel in selected_relationships:
        key = (rel["start"], rel["type"], rel["end"])
        if key in seen:
            continue
        seen.add(key)
        compact_relationships.append(rel)

    return {
        "top_nodes": top_nodes,
        "related_nodes": list(selected_nodes.values()),
        "relationships": compact_relationships[:rel_limit],
    }


def readable_relation_type(rel_type: str) -> str:
    cleaned = rel_type.replace("INVERSE_", "").replace("_", " ").lower()
    if rel_type.startswith("INVERSE_"):
        return f"inverse {cleaned}"
    return cleaned


def format_relation_endpoints(evidence: dict[str, Any], rel: dict[str, Any]) -> tuple[str, str, str]:
    related_by_id = {node["id"]: node for node in evidence.get("related_nodes", [])}
    start_node = related_by_id.get(rel["start"])
    end_node = related_by_id.get(rel["end"])
    start_label = start_node.get("name", rel["start"]) if start_node else rel["start"]
    end_label = end_node.get("name", rel["end"]) if end_node else rel["end"]
    return start_label, readable_relation_type(rel["type"]), end_label


def format_context_for_llm(evidence: dict[str, Any]) -> str:
    lines = ["Relevant nodes:"]
    for node in evidence["top_nodes"]:
        summary = summarize_node(node)
        line = f"- {node.get('label')}: {node.get('name')}"
        if summary:
            line += f" | {summary}"
        lines.append(line)

    if evidence["relationships"]:
        lines.append("")
        lines.append("Relevant relationships:")
        for rel in evidence["relationships"]:
            start_label, relation_label, end_label = format_relation_endpoints(evidence, rel)
            lines.append(f"- {start_label} --{relation_label}--> {end_label}")

    return "\n".join(lines)


def get_api_key() -> str:
    env_key = os.getenv("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key
    try:
        return str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except Exception:
        return ""


def get_secret_or_env(name: str, default: str = "") -> str:
    env_value = os.getenv(name, "").strip()
    if env_value:
        return env_value
    try:
        return str(st.secrets.get(name, default)).strip()
    except Exception:
        return default


def is_ollama_available(host: str) -> bool:
    try:
        request = urllib.request.Request(f"{host.rstrip('/')}/api/tags", method="GET")
        with urllib.request.urlopen(request, timeout=0.45) as response:
            return response.status == 200
    except Exception:
        return False


def detect_runtime_mode(ollama_available: bool) -> str:
    explicit = get_secret_or_env("APP_RUNTIME_MODE", "").casefold()
    if explicit in {"local", "cloud"}:
        return explicit
    return "local" if ollama_available else "cloud"


def is_gemini_quota_error(error: Exception) -> bool:
    message = str(error).casefold()
    markers = [
        "quota",
        "resource exhausted",
        "resource_exhausted",
        "rate limit",
        "429",
        "too many requests",
        "insufficient",
        "billing",
    ]
    return any(marker in message for marker in markers)


def mark_gemini_unavailable(reason: str) -> None:
    try:
        st.session_state["gemini_model_disabled"] = True
        st.session_state["gemini_model_disabled_reason"] = reason
    except Exception:
        pass


def clear_gemini_unavailable() -> None:
    try:
        st.session_state["gemini_model_disabled"] = False
        st.session_state["gemini_model_disabled_reason"] = None
    except Exception:
        pass


def get_model_timeout_seconds() -> int:
    try:
        value = int(st.session_state.get("model_timeout_seconds", DEFAULT_MODEL_TIMEOUT_SECONDS))
    except Exception:
        value = DEFAULT_MODEL_TIMEOUT_SECONDS
    return max(5, min(120, value))


def is_timeout_error(error: Exception) -> bool:
    return isinstance(error, TimeoutError) or "timed out" in str(error).casefold()


def provider_chain(runtime_mode: str, use_model: bool, ollama_available: bool, gemini_ready: bool) -> list[str]:
    if not use_model:
        return ["search"]
    if runtime_mode == "local":
        return ["ollama", "search"] if ollama_available else ["search"]
    return ["gemini", "search"] if gemini_ready else ["search"]


def natural_search_answer(question: str, evidence: dict[str, Any]) -> str:
    top_nodes = evidence["top_nodes"]
    relationships = evidence["relationships"]

    if not top_nodes:
        return "I could not find a confident match for that question in the current graph."

    people = [node["name"] for node in top_nodes if node.get("label") == "Person"][:3]
    skills = [node["name"] for node in top_nodes if node.get("label") == "Skill"][:3]
    roles = [node["name"] for node in top_nodes if node.get("label") == "Role"][:3]

    lines = []
    if people:
        lines.append(f"The strongest people matches are {', '.join(people)}.")
    elif roles:
        lines.append(f"The strongest role matches are {', '.join(roles)}.")
    else:
        lines.append(f"The strongest graph matches are {', '.join(node['name'] for node in top_nodes[:3])}.")

    if skills:
        lines.append(f"Related skill evidence in this result set includes {', '.join(skills)}.")

    if relationships:
        lines.append("The graph also shows direct links around these matches, such as:")
        for rel in relationships[:3]:
            start_label, relation_label, end_label = format_relation_endpoints(evidence, rel)
            lines.append(f"- {relation_label} between {start_label} and {end_label}")
    else:
        lines.append("The current result set does not expose many direct relationships beyond the top matches.")

    lines.append("If you want, ask a narrower follow-up like a specific person, skill, system, or reporting line.")
    return "\n".join(lines)


def answer_mentions_name(answer_text: str, name: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(name.casefold())}(?!\w)", answer_text.casefold()))


def extract_person_like_phrases(text: str) -> list[str]:
    candidates = []
    for match in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b", text):
        candidates.append(match.group(1).strip())
    return candidates


def validate_llm_answer(answer_text: str, question: str, evidence: dict[str, Any], indexes: dict[str, Any]) -> tuple[bool, str]:
    allowed_people = {
        str(node.get("name", "")).strip()
        for node in evidence.get("top_nodes", []) + evidence.get("related_nodes", [])
        if isinstance(node, dict) and node.get("label") == "Person" and node.get("name")
    }
    all_people = {
        str(node.get("name", "")).strip()
        for node in indexes["nodes_by_id"].values()
        if node.get("label") == "Person" and node.get("name")
    }

    mentioned_known_people = [name for name in all_people if answer_mentions_name(answer_text, name)]
    unsupported_known_people = [name for name in mentioned_known_people if name not in allowed_people]
    if unsupported_known_people:
        return False, f"Referenced person outside current graph evidence: {format_human_list(sorted(unsupported_known_people))}."

    question_lc = question.casefold()
    known_node_names = {str(node.get("name", "")).strip().casefold() for node in indexes["nodes_by_id"].values() if node.get("name")}
    suspicious_phrases = []
    for phrase in extract_person_like_phrases(answer_text):
        phrase_lc = phrase.casefold()
        if phrase_lc in question_lc:
            continue
        if phrase_lc in known_node_names:
            continue
        suspicious_phrases.append(phrase)

    if suspicious_phrases:
        return False, f"Potential unsupported named entity in model answer: {format_human_list(sorted(set(suspicious_phrases)))}."

    return True, "Validated against current graph evidence."


def infer_focus_entity(evidence: dict[str, Any]) -> dict[str, str] | None:
    for collection_name in ("top_nodes", "related_nodes"):
        for node in evidence.get(collection_name, []):
            label = str(node.get("label", ""))
            name = str(node.get("name", "")).strip()
            if label in {"Person", "Role"} and name:
                return {"label": label, "name": name}
    return None


def summarize_recent_messages(messages: list[dict[str, str]] | None, limit: int = 4) -> str:
    if not messages:
        return "No prior conversation context."
    lines = []
    for message in messages[-limit:]:
        role = str(message.get("role", "")).strip().title() or "Message"
        content = str(message.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "No prior conversation context."


def resolve_followup_question(question: str, focus: dict[str, str] | None) -> str:
    if not focus:
        return question

    name = str(focus.get("name", "")).strip()
    label = str(focus.get("label", "")).strip()
    if not name or label not in {"Person", "Role"}:
        return question

    resolved = question.strip()
    pronoun_patterns = []
    if label == "Person":
        pronoun_patterns = [
            (r"\bhim\b", name),
            (r"\bher\b", name),
            (r"\bthem\b", name),
            (r"\bthat person\b", name),
            (r"\bthis person\b", name),
        ]
    elif label == "Role":
        pronoun_patterns = [
            (r"\bthat role\b", name),
            (r"\bthis role\b", name),
            (r"\bthat position\b", name),
            (r"\bthis position\b", name),
        ]

    replaced = False
    for pattern, replacement in pronoun_patterns:
        next_value, count = re.subn(pattern, replacement, resolved, flags=re.IGNORECASE)
        if count:
            resolved = next_value
            replaced = True

    if replaced:
        resolved = re.sub(r"^\s*and\s+", "", resolved, flags=re.IGNORECASE)
    return resolved


def parse_person_work_target(question: str) -> str | None:
    normalized = expand_query(question)
    match = re.search(r"who(?:\s+else)?\s+does\s+(.+?)\s+work\s+with", normalized)
    if not match:
        match = re.search(r"who\s+works\s+with\s+(.+)", normalized)
    if not match:
        return None
    target = match.group(1).strip(" ?.")
    return target or None


def parse_relationship_pair(question: str) -> tuple[str, str] | None:
    normalized = expand_query(question)
    patterns = [
        r"how\s+is\s+(.+?)\s+related\s+to\s+(.+)",
        r"(?:what\s+is\s+the\s+|any\s+)?relationship\s+between\s+(.+?)\s+and\s+(.+)",
        r"is\s+(.+?)\s+related\s+to\s+(.+)",
        r"is\s+(.+?)\s+connected\s+to\s+(.+)",
        r"(?:is|are)\s+(.+?)\s+and\s+(.+?)\s+connected(?:\s+somehow)?",
        r"does\s+(.+?)\s+work\s+with\s+(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            left = match.group(1).strip(" ?.")
            right = match.group(2).strip(" ?.")
            if left and right:
                return left, right
    return None


def has_sufficient_evidence(evidence: dict[str, Any]) -> bool:
    top_nodes = evidence.get("top_nodes", [])
    if not top_nodes:
        return False
    best_score = max((float(node.get("_score", 0)) for node in top_nodes), default=0.0)
    return best_score >= 3.5


def build_llm_prompt(question: str, dataset_name: str, graph_scope: str, context_text: str) -> str:
    return f"""
You are an enterprise knowledge graph assistant.
Answer only from the supplied graph context.
If the graph does not clearly support a claim, say so directly.

Dataset: {dataset_name}
Scope: {graph_scope}

User question:
{question}

Graph context:
{context_text}

Answer style:
- Start with a direct answer.
- Sound natural and helpful.
- Use reporting_up for wording like "who does X report to", "who is X reporting to", "who is X's boss", "who is X's manager", or "who is the supervisor of X".
- Use standard uppercase for common abbreviations like COO, CEO, CFO, BI, and HR.
"""


def extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
        return None
    snippet = text[start : end + 1]
    try:
        parsed = json.loads(snippet)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return None
    return None


def interpret_query(
    question: str,
    indexes: dict[str, Any],
    gemini_model_name: str,
    ollama_model_name: str,
    ollama_host: str,
    conversation_focus: dict[str, str] | None = None,
    recent_messages: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    role_names = role_names_in_graph(indexes)
    focus_text = "None"
    if conversation_focus and conversation_focus.get("name") and conversation_focus.get("label"):
        focus_text = f"{conversation_focus['label']}: {conversation_focus['name']}"
    history_text = summarize_recent_messages(recent_messages)
    prompt = f"""
You are a query interpreter for an enterprise knowledge graph assistant.
Your job is to map a user question to one of these intents:
- identity
- reporting_down
- reporting_up
- membership
- knows
- skill
- people_keyword
- explain_previous
- more_results
- unknown

Return JSON only with this schema:
{{
  "intent": "identity | reporting_down | reporting_up | membership | knows | skill | people_keyword | explain_previous | more_results | unknown",
  "target": "short target phrase from the user question",
  "confidence": "high | medium | low"
}}

Rules:
- Do not answer the user question.
- Do not invent people or roles.
- Resolve follow-up references like him, her, them, that role, that person, this team, and short elliptical phrasing using the conversation context when possible.
- Normalize abbreviations and paraphrases when you can do so confidently.
- If the user target clearly corresponds to an existing role name in the catalog below, use that exact role name as the target.
- If the user asks about a title that does not exist exactly in the graph, keep the original business title as the target instead of inventing a mapped role.
- Use reporting_down for wording like "who reports to", "who works under", "head of it workers", "people under X".
- Use reporting_down for shorthand phrases like "CFO team", "head of IT workers", "people under X", or "X staff".
- Use reporting_up for wording like "who does X report to", "who is X reporting to", "who is X's boss", "who is X's manager", or "who is the supervisor of X".
- Use membership for questions like "who is in HR", "who is in finance", "who is in the Romania team", or "who is in Germany".
- Use knows for systems, tools, platforms, or software knowledge.
- Use skill for capability or competency questions.
- Use people_keyword for broad topic questions like "who works with data", "who works on ERP", or "who is connected to planning".
- Relationship questions like "how is X related to Y", "what is the relationship between X and Y", or "does X work with Y" should return unknown unless you can confidently map them to a simpler intent, because the app has a dedicated graph relationship handler for them.
- Use explain_previous for short follow-ups like "why?", "why them?", or "how so?" when the user is asking why the previous answer was returned.
- Use more_results for follow-ups like "who else?", "is there any other?", or "anyone else?" when the user asks for additional results from the previous answer.
- Use identity for "who is X" role/title identity questions.
- If unclear, return unknown.

Examples:
- "who works under head of it" -> reporting_down, target "IT Director / Head of IT"
- "head of it workers?" -> reporting_down, target "IT Director / Head of IT"
- "cfo team?" -> reporting_down, target "Chief Financial Officer"
- "who does Filip Hruby report to" -> reporting_up, target "Filip Hruby"
- "who is Filip's boss" -> reporting_up, target "Filip Hruby"
- "who is the manager of Filip Hruby" -> reporting_up, target "Filip Hruby"
- "who is in HR" -> membership, target "Human Resources"
- "who knows Azure" -> knows, target "Azure"
- "who has skill API integrations" -> skill, target "API integrations"
- "who works with data" -> people_keyword, target "data"
- "how is Petra Novakova related to Manuela Kovacova" -> unknown, target ""
- "why?" -> explain_previous, target ""
- "who else?" -> more_results, target ""
- "who is CIO" -> identity, target "Chief Information Officer"
- "who is CTO" -> identity, target "Chief Technology Officer"

Known role names in the graph:
{chr(10).join(role_names)}

Last graph focus:
{focus_text}

Recent conversation:
{history_text}

User question:
{question}
"""

    ollama_available = bool(ollama_host) and is_ollama_available(ollama_host)
    runtime_mode = detect_runtime_mode(ollama_available)
    gemini_ready = bool(gemini_model_name) and bool(get_api_key()) and not bool(st.session_state.get("gemini_model_disabled", False))
    use_model = bool(ollama_model_name) or gemini_ready
    chain = provider_chain(runtime_mode, use_model, ollama_available, gemini_ready)

    for backend in chain:
        try:
            if backend == "ollama":
                if not ollama_available:
                    continue
                raw = call_ollama(prompt, ollama_model_name, ollama_host)
            elif backend == "gemini":
                if not gemini_ready:
                    continue
                raw = call_gemini(prompt, gemini_model_name)
            else:
                continue
        except Exception as error:
            if is_timeout_error(error):
                note_internal_model_use(backend, "timed out")
            if backend == "gemini" and is_gemini_quota_error(error):
                mark_gemini_unavailable("Gemini is temporarily unavailable because the API quota or rate limit was reached.")
            continue

        parsed = extract_json_object(raw)
        if not parsed:
            continue
        intent = str(parsed.get("intent", "")).strip().casefold()
        target = str(parsed.get("target", "")).strip()
        confidence = str(parsed.get("confidence", "")).strip().casefold()
        if intent not in {"identity", "reporting_down", "reporting_up", "membership", "knows", "skill", "people_keyword", "explain_previous", "more_results", "unknown"}:
            continue
        if not target and intent not in {"unknown", "explain_previous", "more_results"}:
            continue
        if confidence not in {"high", "medium", "low"}:
            confidence = "low"
        return {"intent": intent, "target": target, "confidence": confidence, "backend": backend}

    return None


def call_gemini(prompt: str, model_name: str) -> str:
    client = genai.Client(api_key=get_api_key() or None)

    def _run() -> str:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                top_p=0.9,
                max_output_tokens=700,
            ),
        )
        return (response.text or "").strip()

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_run)
    try:
        return future.result(timeout=get_model_timeout_seconds())
    except FuturesTimeoutError as error:
        raise TimeoutError(f"Gemini timed out after {get_model_timeout_seconds()} seconds.") from error
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def call_ollama(prompt: str, model_name: str, host: str) -> str:
    payload = json.dumps(
        {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
            },
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{host.rstrip('/')}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=get_model_timeout_seconds()) as response:
        body = json.loads(response.read().decode("utf-8"))
    return str(body.get("response", "")).strip()


def reset_internal_model_usage_trace() -> None:
    st.session_state["internal_model_usage_trace"] = []


def note_internal_model_use(backend: str, reason: str) -> None:
    if not backend:
        return
    backend_label = backend.title()
    entry = f"{backend_label} ({reason})" if reason else backend_label
    current = list(st.session_state.get("internal_model_usage_trace", []))
    if entry not in current:
        current.append(entry)
    st.session_state["internal_model_usage_trace"] = current


def get_internal_model_usage_trace() -> str:
    entries = list(st.session_state.get("internal_model_usage_trace", []))
    return ", ".join(entries) if entries else "None"


def make_answer_trace(
    final_backend: str,
    resolution_mode: str,
    interpreter_backend: str | None = None,
    validation: str = "Graph-grounded by structured handler",
) -> dict[str, str]:
    return {
        "final_backend": final_backend,
        "resolution_mode": resolution_mode,
        "interpreter_backend": interpreter_backend or "None",
        "internal_model_use": get_internal_model_usage_trace(),
        "validation": validation,
    }


def answer_question(
    question: str,
    dataset_name: str,
    graph_payload: dict[str, Any],
    indexes: dict[str, Any],
    gemini_model_name: str,
    ollama_model_name: str,
    ollama_host: str,
    conversation_focus: dict[str, str] | None = None,
    recent_messages: list[dict[str, str]] | None = None,
    last_query_state: dict[str, Any] | None = None,
    last_evidence: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any], str, dict[str, Any] | None, dict[str, str]]:
    reset_internal_model_usage_trace()
    other_people_name_answer = try_other_people_with_name_answer(question, indexes, last_evidence)
    if other_people_name_answer:
        answer, evidence, backend, query_state = other_people_name_answer
        return answer, evidence, backend, query_state, make_answer_trace(backend, "Follow-up same-name lookup from graph evidence")

    confirmation_followup = try_confirmation_followup_answer(
        question,
        indexes,
        last_query_state,
        gemini_model_name,
        ollama_model_name,
        ollama_host,
    )
    if confirmation_followup:
        answer, evidence, backend, query_state = confirmation_followup
        return answer, evidence, backend, query_state, make_answer_trace(backend, "Follow-up confirmation over graph evidence")

    why_followup_answer = try_why_followup_answer(question, last_query_state, last_evidence)
    if why_followup_answer:
        answer, evidence, backend, query_state = why_followup_answer
        return answer, evidence, backend, query_state, make_answer_trace(backend, "Follow-up explanation from graph evidence")

    person_keyword_followup = try_person_keyword_followup_answer(question, indexes, last_query_state)
    if person_keyword_followup:
        answer, evidence, backend, query_state = person_keyword_followup
        return answer, evidence, backend, query_state, make_answer_trace(backend, "Follow-up person check against previous graph evidence")

    more_results_answer = try_more_results_answer(question, indexes, last_query_state)
    if more_results_answer:
        answer, evidence, backend, query_state = more_results_answer
        return answer, evidence, backend, query_state, make_answer_trace(backend, "Follow-up expansion from graph evidence")

    group_location_followup = try_group_location_followup_answer(question, indexes, last_query_state)
    if group_location_followup:
        answer, evidence, backend, query_state = group_location_followup
        return answer, evidence, backend, query_state, make_answer_trace(backend, "Follow-up group location from graph evidence")

    group_relationship_followup = try_group_relationship_followup_answer(question, indexes, last_query_state)
    if group_relationship_followup:
        answer, evidence, backend, query_state = group_relationship_followup
        return answer, evidence, backend, query_state, make_answer_trace(backend, "Follow-up group relationship from graph evidence")

    group_keyword_followup = try_group_keyword_followup_answer(question, indexes, last_query_state)
    if group_keyword_followup:
        answer, evidence, backend, query_state = group_keyword_followup
        return answer, evidence, backend, query_state, make_answer_trace(backend, "Follow-up group comparison from graph evidence")

    relationship_followup = try_relationship_followup_answer(
        question,
        indexes,
        last_query_state,
        gemini_model_name,
        ollama_model_name,
        ollama_host,
    )
    if relationship_followup:
        answer, evidence, backend, query_state = relationship_followup
        return answer, evidence, backend, query_state, make_answer_trace(backend, "Follow-up relationship expansion from graph evidence")

    fallback_question = resolve_followup_question(question, conversation_focus)

    def dispatch_safe(question_text: str) -> tuple[str, dict[str, Any], str, dict[str, Any] | None, str] | None:
        greeting_answer = try_greeting_or_intro_answer(question_text)
        if greeting_answer:
            answer, evidence, backend = greeting_answer
            return answer, evidence, backend, None, "Structured app handler: greeting/introduction"

        person_location_answer = try_person_location_answer(question_text, indexes, last_query_state)
        if person_location_answer:
            answer, evidence, backend, query_state = person_location_answer
            return answer, evidence, backend, query_state, "Structured graph handler: person location"

        person_summary_answer = try_person_summary_answer(question_text, indexes)
        if person_summary_answer:
            answer, evidence, backend = person_summary_answer
            return answer, evidence, backend, None, "Structured graph handler: person summary"

        node_relationship_answer = try_node_relationship_answer(
            question_text,
            indexes,
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )
        if node_relationship_answer:
            answer, evidence, backend = node_relationship_answer
            relationship_pair = parse_relationship_pair(question_text)
            query_state = None
            if relationship_pair:
                query_state = {
                    "kind": "relationship_pair",
                    "left_name": relationship_pair[0],
                    "right_name": relationship_pair[1],
                }
            return answer, evidence, backend, query_state, "Structured graph handler: node relationship path"

        location_people_sites_answer = try_location_people_and_sites_answer(question_text, indexes)
        if location_people_sites_answer:
            answer, evidence, backend = location_people_sites_answer
            return answer, evidence, backend, None, "Structured graph handler: location + sites"

        list_answer = try_list_entities_answer(question_text, indexes)
        if list_answer:
            answer, evidence, backend = list_answer
            return answer, evidence, backend, None, "Structured graph handler: entity listing"

        membership_answer = try_membership_answer(
            question_text,
            indexes,
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )
        if membership_answer:
            answer, evidence, backend = membership_answer
            membership_people = [
                node["name"]
                for node in evidence.get("top_nodes", [])
                if isinstance(node, dict) and node.get("label") == "Person" and node.get("name")
            ]
            membership_target = ""
            for node in evidence.get("top_nodes", []):
                if isinstance(node, dict) and node.get("label") in {"Department", "Team", "Country", "Site"} and node.get("name"):
                    membership_target = str(node["name"])
                    break
            query_state = {
                "kind": "membership",
                "target": membership_target,
                "shown_people": membership_people,
            }
            return answer, evidence, backend, query_state, "Structured graph handler: membership/location"

        identity_answer = try_identity_answer(question_text, indexes)
        if identity_answer:
            answer, evidence, backend = identity_answer
            return answer, evidence, backend, None, "Structured graph handler: identity"

        if is_identity_question(question_text):
            suggested_answer = build_similar_role_suggestion(
                question_text,
                indexes,
                gemini_model_name,
                ollama_model_name,
                ollama_host,
            )
            if suggested_answer:
                answer, evidence, backend = suggested_answer
                return answer, evidence, backend, None, "Graph-supported similar role suggestion"
            empty_evidence = {"top_nodes": [], "related_nodes": [], "relationships": []}
            return "I could not find a confident person or role match for that title in the current graph.", empty_evidence, "Graph Search", None, "Structured graph handler: identity not found"

        reporting_answer = try_reporting_answer(
            question_text,
            indexes,
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )
        if reporting_answer:
            answer, evidence, backend = reporting_answer
            return answer, evidence, backend, None, "Structured graph handler: reporting down"

        reverse_reporting_answer = try_reverse_reporting_answer(
            question_text,
            indexes,
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )
        if reverse_reporting_answer:
            answer, evidence, backend = reverse_reporting_answer
            return answer, evidence, backend, None, "Structured graph handler: reporting up"

        person_concept_answer = try_person_concept_answer(
            question_text,
            indexes,
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )
        if person_concept_answer:
            answer, evidence, backend = person_concept_answer
            return answer, evidence, backend, None, "Structured graph handler: person + concept"

        person_work_with_answer = try_person_work_with_answer(
            question_text,
            indexes,
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )
        if person_work_with_answer:
            answer, evidence, backend = person_work_with_answer
            person_target = parse_person_work_target(question_text)
            query_state = None
            if answer.startswith("I could not find the exact person or role"):
                suggested_person = infer_focus_entity(evidence)
                if suggested_person and suggested_person.get("label") in {"Person", "Role"}:
                    query_state = {
                        "kind": "pending_suggestion",
                        "intent": "person_work_with",
                        "suggested_name": str(suggested_person.get("name", "")),
                    }
            elif person_target:
                query_state = {
                    "kind": "person_collaboration",
                    "target": person_target,
                }
            return answer, evidence, backend, query_state, "Structured graph handler: person collaboration"

        keyword_people_answer = try_people_for_keyword_answer(question_text, indexes)
        if keyword_people_answer:
            answer, evidence, backend, query_state = keyword_people_answer
            return answer, evidence, backend, query_state, "Structured graph handler: broad people keyword"

        knows_answer = try_knows_answer(
            question_text,
            indexes,
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )
        if knows_answer:
            answer, evidence, backend = knows_answer
            return answer, evidence, backend, None, "Structured graph handler: system knowledge"

        skill_answer = try_skill_answer(
            question_text,
            indexes,
            gemini_model_name,
            ollama_model_name,
            ollama_host,
        )
        if skill_answer:
            answer, evidence, backend = skill_answer
            return answer, evidence, backend, None, "Structured graph handler: skill match"

        return None

    if re.search(r"^\s*(who('?s| is)\s+in|who\s+works\s+in)\s+.+", expand_query(fallback_question)):
        direct_membership_answer = dispatch_safe(fallback_question)
        if direct_membership_answer:
            answer, evidence, backend, query_state, resolution_mode = direct_membership_answer
            return answer, evidence, backend, query_state, make_answer_trace(backend, resolution_mode)
    if re.search(r"\b(reports?\s+to|works?\s+under|works?\s+for|is\s+under|does.+report\s+to|reporting\s+to)\b", expand_query(fallback_question)):
        direct_reporting_answer = dispatch_safe(fallback_question)
        if direct_reporting_answer:
            answer, evidence, backend, query_state, resolution_mode = direct_reporting_answer
            return answer, evidence, backend, query_state, make_answer_trace(backend, resolution_mode)
    if (
        re.search(r"\b(related\s+to|relationship\s+between|connected\s+to|connected\s+through|connected\s+via)\b", expand_query(fallback_question))
        or re.search(r"\bdoes\b.+\bwork\s+with\b", expand_query(fallback_question))
        or re.search(r"\b(?:is|are)\b.+\band\b.+\bconnected(?:\s+somehow)?\b", expand_query(fallback_question))
    ):
        direct_relationship_answer = dispatch_safe(fallback_question)
        if direct_relationship_answer:
            answer, evidence, backend, query_state, resolution_mode = direct_relationship_answer
            return answer, evidence, backend, query_state, make_answer_trace(backend, resolution_mode)
    if re.search(r"\b(list|show|what are)\b", expand_query(fallback_question)):
        direct_list_answer = dispatch_safe(fallback_question)
        if direct_list_answer:
            answer, evidence, backend, query_state, resolution_mode = direct_list_answer
            return answer, evidence, backend, query_state, make_answer_trace(backend, resolution_mode)

    direct_answer = dispatch_safe(fallback_question)
    if direct_answer:
        answer, evidence, backend, query_state, resolution_mode = direct_answer
        return answer, evidence, backend, query_state, make_answer_trace(backend, resolution_mode)

    interpreted = interpret_query(
        fallback_question,
        indexes,
        gemini_model_name,
        ollama_model_name,
        ollama_host,
        conversation_focus,
        recent_messages,
    )
    interpreter_backend = str(interpreted.get("backend")) if interpreted else None
    if interpreted and interpreted.get("intent") != "unknown":
        lowered_question = fallback_question.casefold()
        interpreted_intent = str(interpreted.get("intent"))
        if interpreted_intent == "more_results":
            more_results_answer = try_more_results_answer(question, indexes, last_query_state)
            if more_results_answer:
                answer, evidence, backend, query_state = more_results_answer
                return answer, evidence, backend, query_state, make_answer_trace(backend, "Follow-up expansion from graph evidence", interpreter_backend)
        if interpreted_intent == "explain_previous":
            why_answer = try_why_followup_answer(question, last_query_state, last_evidence)
            if why_answer:
                answer, evidence, backend, query_state = why_answer
                return answer, evidence, backend, query_state, make_answer_trace(backend, "Follow-up explanation from graph evidence", interpreter_backend)
        if re.search(r"\b(reports?\s+to|works?\s+under|works?\s+for|under)\b", lowered_question):
            interpreted["intent"] = "reporting_down"
        if re.search(r"\bdoes\b.+\breport\s+to\b", lowered_question) or re.search(r"\breporting\s+to\b", lowered_question):
            interpreted["intent"] = "reporting_up"
        if interpreted_intent == "people_keyword" or re.search(r"\bworks?\s+(with|on|in)\b", lowered_question):
            person_work_with_answer = try_person_work_with_answer(
                fallback_question,
                indexes,
                gemini_model_name,
                ollama_model_name,
                ollama_host,
            )
            if person_work_with_answer:
                answer, evidence, backend = person_work_with_answer
                return answer, evidence, backend, None, make_answer_trace(
                    backend,
                    "Structured graph handler: person collaboration",
                    interpreter_backend,
                )
            keyword_answer = try_people_for_keyword_answer(fallback_question, indexes)
            if keyword_answer:
                answer, evidence, backend, query_state = keyword_answer
                return answer, evidence, backend, query_state, make_answer_trace(backend, "Structured graph handler: broad people keyword", interpreter_backend)
        if (
            str(interpreted.get("intent")) == "identity"
            and re.search(r"\b(team|workers?|people|staff)\b", lowered_question)
        ):
            interpreted["intent"] = "reporting_down"
        canonical_questions = {
            "identity": f"who is {interpreted['target']}",
            "reporting_down": f"who reports to {interpreted['target']}",
            "reporting_up": f"who does {interpreted['target']} report to",
            "membership": f"who is in {interpreted['target']}",
            "knows": f"who knows {interpreted['target']}",
            "skill": f"who has skill {interpreted['target']}",
            "people_keyword": f"who works with {interpreted['target']}",
        }
        canonical_question = canonical_questions.get(str(interpreted["intent"]))
        if canonical_question:
            interpreted_answer = dispatch_safe(canonical_question)
            if interpreted_answer:
                answer, evidence, backend, query_state, resolution_mode = interpreted_answer
                return answer, evidence, backend, query_state, make_answer_trace(backend, resolution_mode, interpreter_backend)

    evidence = build_evidence(indexes, fallback_question)
    if not has_sufficient_evidence(evidence):
        return natural_search_answer(fallback_question, evidence), evidence, "Graph Search", None, make_answer_trace("Graph Search", "Graph-only fallback over retrieved evidence", interpreter_backend)

    context_text = format_context_for_llm(evidence)
    prompt = build_llm_prompt(
        question=fallback_question,
        dataset_name=dataset_name,
        graph_scope=graph_payload["meta"].get("graph_scope", ""),
        context_text=context_text,
    )

    ollama_available = bool(ollama_host) and is_ollama_available(ollama_host)
    runtime_mode = detect_runtime_mode(ollama_available)
    gemini_ready = bool(gemini_model_name) and bool(get_api_key()) and not bool(st.session_state.get("gemini_model_disabled", False))
    use_model = bool(ollama_model_name) or gemini_ready
    chain = provider_chain(runtime_mode, use_model, ollama_available, gemini_ready)

    for backend in chain:
        if backend == "ollama":
            if not ollama_available:
                continue
            try:
                answer = call_ollama(prompt, ollama_model_name, ollama_host)
                if answer:
                    is_valid, validation_reason = validate_llm_answer(answer, fallback_question, evidence, indexes)
                    if is_valid:
                        return answer, evidence, "Ollama", None, make_answer_trace("Ollama", "LLM answer over retrieved graph context", interpreter_backend, validation_reason)
                    fallback_answer = natural_search_answer(question, evidence)
                    return fallback_answer, evidence, "Graph Search", None, make_answer_trace("Graph Search", "Validator fallback after unsupported Ollama answer", interpreter_backend, validation_reason)
            except Exception as error:
                if is_timeout_error(error):
                    note_internal_model_use("Ollama", "timed out")
                continue

        if backend == "gemini":
            if not gemini_ready:
                continue
            try:
                answer = call_gemini(prompt, gemini_model_name)
                if answer:
                    is_valid, validation_reason = validate_llm_answer(answer, fallback_question, evidence, indexes)
                    if is_valid:
                        return answer, evidence, "Gemini", None, make_answer_trace("Gemini", "LLM answer over retrieved graph context", interpreter_backend, validation_reason)
                    fallback_answer = natural_search_answer(question, evidence)
                    return fallback_answer, evidence, "Graph Search", None, make_answer_trace("Graph Search", "Validator fallback after unsupported Gemini answer", interpreter_backend, validation_reason)
            except Exception as error:
                if is_timeout_error(error):
                    note_internal_model_use("Gemini", "timed out")
                if is_gemini_quota_error(error):
                    mark_gemini_unavailable("Gemini is temporarily unavailable because the API quota or rate limit was reached.")
                continue

        if backend == "search":
            resolution = "Graph-only fallback after model timeout" if "timed out" in get_internal_model_usage_trace().casefold() else "Graph-only fallback over retrieved evidence"
            return natural_search_answer(question, evidence), evidence, "Graph Search", None, make_answer_trace("Graph Search", resolution, interpreter_backend)

    resolution = "Graph-only fallback after model timeout" if "timed out" in get_internal_model_usage_trace().casefold() else "Graph-only fallback over retrieved evidence"
    return natural_search_answer(question, evidence), evidence, "Graph Search", None, make_answer_trace("Graph Search", resolution, interpreter_backend)


def render_hero(dataset_name: str, graph_payload: dict[str, Any], backend_order: list[str]) -> None:
    meta = graph_payload.get("meta", {})
    backend_labels = {
        "ollama": "Ollama",
        "gemini": "Gemini",
        "search": "Graph Search",
    }
    backend_html = "".join(
        f'<span class="backend-badge">{backend_labels[item]}</span>' for item in backend_order
    )
    stat_html = f"""
    <div class="hero-card">
      <div class="hero-eyebrow">Graph-grounded workspace</div>
      {skillwiki_brand_html(include_logo_text_class=True)}
      <div class="hero-subtitle">
        Explore people, roles, skills, systems, teams, and evidence through a clear conversational layer.
        The app retrieves graph context first, then answers through the best available model path.
      </div>
      <div class="chip-row">
        <span class="chip">{dataset_name}</span>
        <span class="chip">{meta.get("graph_scope", "Knowledge graph")}</span>
      </div>
      <div style="margin-top:0.9rem;">{backend_html}</div>
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-label">Nodes</div>
          <div class="stat-value">{meta.get("node_count", 0)}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Relationships</div>
          <div class="stat-value">{meta.get("relationship_count", 0)}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Datasets</div>
          <div class="stat-value">2 modes</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Answer path</div>
          <div class="stat-value">{' -> '.join(backend_labels[item] for item in backend_order)}</div>
        </div>
      </div>
    </div>
    """
    st.markdown(stat_html, unsafe_allow_html=True)


def render_evidence_panel(evidence: dict[str, Any], backend_used: str | None, answer_trace: dict[str, str] | None = None) -> None:
    st.markdown(
        """
        <div class="section-card">
          <div class="section-header">
            <div class="section-title">Evidence Panel</div>
            <div class="section-subtitle">Top retrieved nodes and graph links used for the current answer.</div>
          </div>
          <div class="section-body">
        """,
        unsafe_allow_html=True,
    )

    if answer_trace:
        st.caption(f"Final answer: {answer_trace.get('final_backend', backend_used or 'Unknown')}")
        st.caption(f"Question interpretation: {answer_trace.get('interpreter_backend', 'None')}")
        st.caption(f"Model assistance used internally: {answer_trace.get('internal_model_use', 'None')}")
        st.caption(f"Resolution mode: {answer_trace.get('resolution_mode', 'Unknown')}")
        st.caption(f"Validation: {answer_trace.get('validation', 'Unknown')}")
    elif backend_used:
        st.caption(f"Last answer path: {backend_used}")

    if not evidence["top_nodes"]:
        st.info("Ask a question to see the strongest supporting graph evidence.")
    else:
        for node in evidence["top_nodes"]:
            summary = summarize_node(node)
            st.markdown(
                f"""
                <div class="evidence-card">
                  <div class="evidence-kicker">{node.get('label')}</div>
                  <div class="evidence-title">{node.get('name')}</div>
                  <div class="evidence-body">
                    Score: {node.get('_score', 0)}<br/>
                    {summary if summary else "No extra summary fields on this node."}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with st.expander("Relationship trace", expanded=False):
            if evidence["relationships"]:
                for rel in evidence["relationships"]:
                    start_label, relation_label, end_label = format_relation_endpoints(evidence, rel)
                    st.write(f"`{start_label}` -> `{relation_label}` -> `{end_label}`")
            else:
                st.write("No relationship trace available for this query.")

    st.markdown("</div></div>", unsafe_allow_html=True)


def init_state() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("last_evidence", {"top_nodes": [], "related_nodes": [], "relationships": []})
    st.session_state.setdefault("prompt_queue", None)
    st.session_state.setdefault("pending_prompt", None)
    st.session_state.setdefault("is_processing", False)
    st.session_state.setdefault("last_backend", None)
    st.session_state.setdefault("last_answer_trace", None)
    st.session_state.setdefault("last_focus", None)
    st.session_state.setdefault("last_query_state", None)
    st.session_state.setdefault("gemini_model_disabled", False)
    st.session_state.setdefault("gemini_model_disabled_reason", None)


def sidebar_controls() -> tuple[str, str, str, str, bool, list[str], list[str], str]:
    with st.sidebar:
        st.markdown(
            skillwiki_brand_html(compact=True),
            unsafe_allow_html=True,
        )
        st.markdown("## Workspace")
        dataset_options = list(GRAPH_OPTIONS.keys())
        default_dataset_index = dataset_options.index("Detailed Graph") if "Detailed Graph" in dataset_options else 0
        dataset_name = st.selectbox("Dataset", dataset_options, index=default_dataset_index)
        ollama_model_name = st.text_input("Ollama model", value=get_secret_or_env("OLLAMA_MODEL", "llama3.2"))
        ollama_host = st.text_input("Ollama host", value=get_secret_or_env("OLLAMA_HOST", "http://127.0.0.1:11434"))
        timeout_value = st.number_input(
            "Model timeout (s)",
            min_value=5,
            max_value=120,
            value=int(st.session_state.get("model_timeout_seconds", DEFAULT_MODEL_TIMEOUT_SECONDS)),
            step=5,
            help="If model assistance takes longer than this, the app stops waiting for the model step and falls back safely.",
        )
        st.session_state["model_timeout_seconds"] = int(timeout_value)
        selected_payload = load_graph(str(GRAPH_OPTIONS[dataset_name]))
        ollama_available = is_ollama_available(ollama_host)
        runtime_mode = detect_runtime_mode(ollama_available)
        gemini_disabled = bool(st.session_state.get("gemini_model_disabled", False))
        gemini_ready = bool(get_api_key()) and not gemini_disabled
        model_available = ollama_available if runtime_mode == "local" else gemini_ready
        default_model_enabled = model_available if runtime_mode == "local" else False
        if "use_model_assistance" not in st.session_state:
            st.session_state["use_model_assistance"] = default_model_enabled
        use_model = st.toggle(
            "Use model assistance",
            key="use_model_assistance",
            disabled=not model_available,
            help="Local mode uses Ollama. Cloud mode uses Gemini. If disabled, the app answers directly from graph logic only.",
        )
        if not model_available:
            use_model = False

        effective_ollama_model = ollama_model_name if runtime_mode == "local" and use_model and ollama_available else ""
        effective_gemini_model = DEFAULT_GEMINI_MODEL if runtime_mode == "cloud" and use_model and gemini_ready else ""
        order = provider_chain(runtime_mode, use_model, ollama_available, gemini_ready)

        st.markdown(
            f"""
            <div class="sidebar-note">
              <strong>Current scope</strong><br/>
              {selected_payload.get("meta", {}).get("graph_scope", "Knowledge graph")}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Suggested prompts")
        prompts = [
            "Who is strongest in ERP and IFS?",
            "Find people connected to production planning.",
            "Who reports to the COO?",
            "Which people seem closest to data governance and BI?",
        ]
        for prompt in prompts:
            if st.button(prompt, use_container_width=True):
                st.session_state["prompt_queue"] = prompt

        st.markdown("### Backend status")
        if ollama_available:
            st.success(f"Ollama reachable at {ollama_host}")
        else:
            st.info("Ollama not reachable. The app will skip it automatically.")

        if gemini_disabled:
            st.warning(str(st.session_state.get("gemini_model_disabled_reason", "Gemini is temporarily unavailable. The app switched to Graph Search.")))
        elif get_api_key():
            st.success("Gemini key detected.")
        else:
            st.warning("Gemini key not found. The app will fall back to graph-only answers.")

        if runtime_mode == "local":
            st.caption("Model target: Ollama" if use_model and ollama_available else "Model target: Off")
        else:
            st.caption("Model target: Gemini" if use_model and gemini_ready else "Model target: Off")

        st.caption(f"Runtime mode: {runtime_mode.title()}")
        st.caption("Answer order: " + " -> ".join(item.title() if item != "search" else "Graph Search" for item in order))

        st.markdown("### Graph snapshot")
        st.caption(f"Nodes: {selected_payload.get('meta', {}).get('node_count', 0)}")
        st.caption(f"Relationships: {selected_payload.get('meta', {}).get('relationship_count', 0)}")
        st.caption(f"Labels: {len({node['label'] for node in selected_payload.get('nodes', [])})}")

    return dataset_name, effective_gemini_model, effective_ollama_model, ollama_host, ollama_available, prompts, order, runtime_mode


def render_chat(messages: list[dict[str, str]]) -> None:
    st.markdown(
        """
        <div class="section-card">
          <div class="section-header">
            <div class="section-title section-title-brand">"""
        + skillwiki_brand_html(compact=True)
        + """</div>
            <div class="section-subtitle">Ask free-form questions over the graph. Answers stay grounded in retrieved graph evidence.</div>
          </div>
          <div class="section-body">
        """,
        unsafe_allow_html=True,
    )

    if not messages:
        st.info("Try a question like: `Who reports to the COO?` or `Find people connected to ERP and planning.`")
    else:
        for message in messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    st.markdown("</div></div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="SkillWiki",
        page_icon="K",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()
    init_state()

    dataset_name, gemini_model_name, ollama_model_name, ollama_host, ollama_available, _, backend_order, _ = sidebar_controls()
    graph_path = str(GRAPH_OPTIONS[dataset_name])
    graph_payload = load_graph(graph_path)
    indexes = build_indexes(graph_path)

    render_hero(dataset_name, graph_payload, backend_order)

    col_chat, col_evidence = st.columns([1.45, 0.85], gap="large")

    with col_chat:
        render_chat(st.session_state["messages"])
        if st.session_state.get("is_processing") and st.session_state.get("pending_prompt"):
            with st.chat_message("user"):
                st.markdown(st.session_state["pending_prompt"])
            with st.chat_message("assistant"):
                st.markdown("Thinking...")
        prompt = st.chat_input(
            "Ask about people, roles, skills, systems, or reporting lines",
            disabled=bool(st.session_state.get("is_processing")),
        )

    queued_prompt = st.session_state.get("prompt_queue")
    if queued_prompt and not st.session_state.get("is_processing"):
        st.session_state["prompt_queue"] = None
        st.session_state["pending_prompt"] = queued_prompt
        st.session_state["is_processing"] = True
        st.rerun()

    if prompt and not st.session_state.get("is_processing"):
        st.session_state["pending_prompt"] = prompt
        st.session_state["is_processing"] = True
        st.rerun()

    active_prompt = st.session_state.get("pending_prompt")
    if st.session_state.get("is_processing") and active_prompt:
        recent_messages = st.session_state["messages"][-4:]
        st.session_state["messages"].append({"role": "user", "content": active_prompt})
        with col_chat:
            with st.spinner("Searching the graph and preparing an answer..."):
                answer, evidence, backend_used, query_state, answer_trace = answer_question(
                    question=active_prompt,
                    dataset_name=dataset_name,
                    graph_payload=graph_payload,
                    indexes=indexes,
                    gemini_model_name=gemini_model_name,
                    ollama_model_name=ollama_model_name,
                    ollama_host=ollama_host,
                    conversation_focus=st.session_state.get("last_focus"),
                    recent_messages=recent_messages,
                    last_query_state=st.session_state.get("last_query_state"),
                    last_evidence=st.session_state.get("last_evidence"),
                )
        st.session_state["messages"].append({"role": "assistant", "content": answer})
        st.session_state["last_evidence"] = evidence
        st.session_state["last_backend"] = backend_used
        st.session_state["last_answer_trace"] = answer_trace
        st.session_state["last_focus"] = infer_focus_entity(evidence)
        st.session_state["last_query_state"] = query_state
        st.session_state["pending_prompt"] = None
        st.session_state["is_processing"] = False
        st.rerun()

    with col_evidence:
        render_evidence_panel(
            st.session_state["last_evidence"],
            st.session_state["last_backend"],
            st.session_state.get("last_answer_trace"),
        )

        with st.expander("Advanced context", expanded=False):
            context_text = format_context_for_llm(st.session_state["last_evidence"])
            if context_text.strip():
                st.code(context_text, language="text")
            else:
                st.write("No retrieved context yet.")


if __name__ == "__main__":
    main()
