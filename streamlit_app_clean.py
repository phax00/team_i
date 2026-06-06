import base64
import html
import re
from pathlib import Path

import streamlit as st

import streamlit_app as core


ROOT = Path(__file__).resolve().parent
LOCAL_LOGO_ICON = ROOT / "skillwiki_logo_icon.png"
LOCAL_LOGO_JPEG = ROOT / "skillwiki_logo.jpeg"
LOCAL_DEFAULT_MODEL_TIMEOUT_SECONDS = 60
LOCAL_FALLBACK_LOGO_SVG = """
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
  </g>
</svg>
""".strip()


def clean_logo_src() -> str:
    if hasattr(core, "skillwiki_logo_src"):
        try:
            return core.skillwiki_logo_src()
        except Exception:
            pass
    if LOCAL_LOGO_ICON.exists():
        return "data:image/png;base64," + base64.b64encode(LOCAL_LOGO_ICON.read_bytes()).decode("ascii")
    if LOCAL_LOGO_JPEG.exists():
        return "data:image/jpeg;base64," + base64.b64encode(LOCAL_LOGO_JPEG.read_bytes()).decode("ascii")
    return "data:image/svg+xml;base64," + base64.b64encode(LOCAL_FALLBACK_LOGO_SVG.encode("utf-8")).decode("ascii")


def clean_brand_html(compact: bool = False) -> str:
    if hasattr(core, "skillwiki_brand_html"):
        try:
            return core.skillwiki_brand_html(compact=compact)
        except Exception:
            pass
    brand_class = "skillwiki-brand skillwiki-brand--compact" if compact else "skillwiki-brand"
    return (
        f'<div class="{brand_class}">'
        f'<span class="skillwiki-icon"><img src="{clean_logo_src()}" alt="SkillWiki logo"/></span>'
        '<span class="skillwiki-wordmark">Skill<span>Wiki</span></span>'
        "</div>"
    )


def inject_clean_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --primary: #7B3AED;
            --primary-dark: #6026C9;
            --primary-soft: #F5F0FF;
            --surface: #FFFFFF;
            --surface-soft: #FAF8FF;
            --text: #171717;
            --muted: #5F5B70;
            --border: #E8DDFD;
        }

        .stApp {
            background: linear-gradient(180deg, #FCFBFF 0%, #F6F1FF 100%);
            color: var(--text);
        }

        .block-container {
            max-width: 980px;
            padding-top: 2.4rem;
            padding-bottom: 2.2rem;
        }

        section[data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.82);
            border-right: 1px solid var(--border);
        }

        .skillwiki-brand {
            display: flex;
            align-items: center;
            gap: 0.68rem;
            width: max-content;
            max-width: 100%;
            overflow: visible;
        }

        .skillwiki-brand--compact {
            gap: 0.5rem;
        }

        .skillwiki-icon {
            width: 2.1rem;
            height: 2.1rem;
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

        .skillwiki-logo,
        .skillwiki-wordmark {
            line-height: 1.15;
            font-weight: 900;
            letter-spacing: -0.04em;
            color: #141414;
            display: inline-block;
            padding-top: 0.03rem;
            padding-bottom: 0.03rem;
        }

        .skillwiki-logo {
            font-size: 2.05rem;
        }

        .skillwiki-wordmark {
            font-size: 1.02rem;
        }

        .skillwiki-logo span,
        .skillwiki-wordmark span {
            color: var(--primary);
        }

        .sidebar-brand {
            margin-bottom: 0.95rem;
        }

        .msg-row {
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
            width: 100%;
        }

        .msg-row.user {
            align-items: flex-end;
        }

        .msg-row.assistant {
            align-items: flex-start;
        }

        .msg-label {
            font-size: 0.77rem;
            letter-spacing: 0.02em;
            text-transform: uppercase;
            font-weight: 800;
            color: var(--muted);
            padding: 0 0.15rem;
            line-height: 1.25;
            overflow: visible;
        }

        .msg-label.user {
            padding-top: 0.42rem;
            padding-bottom: 0.1rem;
            min-height: 1.9rem;
        }

        .msg-bubble {
            width: min(100%, 780px);
            border-radius: 20px;
            border: 1px solid var(--border);
            box-shadow: 0 10px 26px rgba(123, 58, 237, 0.06);
            padding: 0.95rem 1rem 0.8rem 1rem;
        }

        .msg-bubble.user {
            background: linear-gradient(180deg, #FFFFFF 0%, #FBF7FF 100%);
        }

        .msg-bubble.assistant {
            background: #FFFFFF;
        }

        .msg-body {
            color: var(--text);
            font-size: 1rem;
            line-height: 1.62;
            word-break: break-word;
        }

        .msg-body p {
            margin: 0 0 0.55rem 0;
        }

        .msg-body p:last-child {
            margin-bottom: 0;
        }

        .msg-body ul {
            margin: 0.2rem 0 0.5rem 1.1rem;
            padding: 0;
        }

        .msg-body li {
            margin: 0.18rem 0;
        }

        .msg-label.assistant {
            display: block;
            color: var(--muted);
            padding-top: 0.42rem;
            padding-bottom: 0.1rem;
            min-height: 1.9rem;
        }

        .assistant-label-brand {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            line-height: 1.1;
            overflow: visible;
            transform: translateY(2px);
        }

        .assistant-label-icon {
            width: 1.08rem;
            height: 1.08rem;
            flex: 0 0 auto;
            display: inline-flex;
            align-items: center;
        }

        .assistant-label-icon img {
            width: 100%;
            height: 100%;
            display: block;
            object-fit: contain;
        }

        .assistant-label-text {
            font-size: 0.9rem;
            font-weight: 900;
            letter-spacing: -0.03em;
            text-transform: none;
            color: #141414;
            display: inline-block;
            line-height: 1.15;
        }

        .assistant-label-text span {
            color: var(--primary);
        }

        .inline-tag {
            display: inline-block;
            padding: 0.08rem 0.42rem;
            border-radius: 999px;
            background: #F3F4F6;
            border: 1px solid #E5E7EB;
            color: #374151;
            font-size: 0.94em;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        }

        .answer-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 0.38rem;
            margin-top: 0.72rem;
        }

        .meta-pill {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            border: 1px solid var(--border);
            background: var(--primary-soft);
            color: var(--primary-dark);
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.22rem 0.55rem;
        }

        .meta-pill span {
            color: var(--muted);
            font-weight: 600;
            margin-right: 0.28rem;
        }

        .thinking-card {
            width: min(100%, 780px);
            border-radius: 20px;
            border: 1px solid var(--border);
            background: rgba(255, 255, 255, 0.88);
            padding: 0.9rem 1rem;
            color: var(--muted);
            font-weight: 700;
            box-shadow: 0 10px 26px rgba(123, 58, 237, 0.06);
        }

        .stButton > button,
        .stFormSubmitButton > button {
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 12px;
            font-weight: 700;
        }

        .stButton > button:hover,
        .stFormSubmitButton > button:hover {
            background: var(--primary-dark);
        }

        .stTextInput input,
        .stSelectbox div[data-baseweb="select"] > div,
        .stTextArea textarea {
            border-radius: 12px !important;
            border-color: var(--border) !important;
            background: #FFFFFF !important;
        }

        [data-testid="stChatInput"] {
            margin-top: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_inline_tags(text: str) -> str:
    placeholders: list[str] = []

    def capture(match: re.Match[str]) -> str:
        placeholders.append(match.group(1))
        return f"__INLINE_TAG_{len(placeholders) - 1}__"

    protected = re.sub(r"`([^`]+)`", capture, text)
    escaped = html.escape(protected)

    for index, value in enumerate(placeholders):
        token = f"__INLINE_TAG_{index}__"
        escaped = escaped.replace(
            token,
            f'<span class="inline-tag">{html.escape(value)}</span>',
        )

    return escaped


def format_message_html(text: str) -> str:
    rendered_blocks: list[str] = []
    paragraphs = [block.strip() for block in text.strip().split("\n\n") if block.strip()]

    if not paragraphs:
        return "<p></p>"

    for block in paragraphs:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines and all(line.startswith("- ") for line in lines):
            items = "".join(f"<li>{_render_inline_tags(line[2:])}</li>" for line in lines)
            rendered_blocks.append(f"<ul>{items}</ul>")
            continue

        joined = "<br>".join(_render_inline_tags(line) for line in lines)
        rendered_blocks.append(f"<p>{joined}</p>")

    return "".join(rendered_blocks)


def build_sidebar() -> tuple[str, str, str, str]:
    with st.sidebar:
        st.markdown(
            f'<div class="sidebar-brand">{clean_brand_html(compact=True)}</div>',
            unsafe_allow_html=True,
        )

        dataset_options = list(core.GRAPH_OPTIONS.keys())
        default_dataset_index = dataset_options.index("Detailed Graph") if "Detailed Graph" in dataset_options else 0
        dataset_name = st.selectbox("Dataset", dataset_options, index=default_dataset_index)
        ollama_model_name = core.get_secret_or_env("OLLAMA_MODEL", "llama3.2")
        ollama_host = core.get_secret_or_env("OLLAMA_HOST", "http://127.0.0.1:11434")
        timeout_value = st.number_input(
            "Model timeout (s)",
            min_value=5,
            max_value=120,
            value=int(st.session_state.get("model_timeout_seconds", getattr(core, "DEFAULT_MODEL_TIMEOUT_SECONDS", LOCAL_DEFAULT_MODEL_TIMEOUT_SECONDS))),
            step=5,
            help="If model assistance takes longer than this, the app stops waiting for the model step and falls back safely.",
        )
        st.session_state["model_timeout_seconds"] = int(timeout_value)

        ollama_available = core.is_ollama_available(ollama_host)
        runtime_mode = core.detect_runtime_mode(ollama_available)
        gemini_disabled = bool(st.session_state.get("gemini_model_disabled", False))
        gemini_ready = bool(core.get_api_key()) and not gemini_disabled
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
        effective_gemini_model = core.DEFAULT_GEMINI_MODEL if runtime_mode == "cloud" and use_model and gemini_ready else ""

        if st.button("Clear conversation", use_container_width=True):
            st.session_state["messages"] = []
            st.session_state["last_focus"] = None
            st.session_state["last_evidence"] = {"top_nodes": [], "related_nodes": [], "relationships": []}
            st.session_state["last_query_state"] = None
            st.session_state["last_answer_trace"] = None
            st.session_state["pending_prompt"] = None
            st.session_state["is_processing"] = False
            st.rerun()

        st.caption(f"Runtime: {runtime_mode.title()}")
        st.caption("Mode: " + ("Model + Graph" if use_model else "Graph only"))

        if runtime_mode == "local":
            st.caption("Model target: Ollama" if effective_ollama_model else "Model target: Off")
        else:
            st.caption("Model target: Gemini" if effective_gemini_model else "Model target: Off")

        if gemini_disabled:
            st.warning(str(st.session_state.get("gemini_model_disabled_reason", "Gemini is temporarily unavailable.")))

    return dataset_name, effective_gemini_model, effective_ollama_model, ollama_host


def render_trace_html(trace: dict[str, str] | None) -> str:
    if not trace:
        return ""
    final_backend = trace.get("final_backend", "Unknown")
    interpreter_backend = trace.get("interpreter_backend", "None")
    internal_model_use = trace.get("internal_model_use", "None")
    resolution_mode = trace.get("resolution_mode", "Unknown")

    return (
        f"""
        <div class="answer-meta">
          <div class="meta-pill"><span>Answered with</span>{html.escape(final_backend)}</div>
          <div class="meta-pill"><span>Interpreted with</span>{html.escape(interpreter_backend)}</div>
          <div class="meta-pill"><span>Internal model use</span>{html.escape(internal_model_use)}</div>
          <div class="meta-pill"><span>Mode</span>{html.escape(resolution_mode)}</div>
        </div>
        """
    )


def render_assistant_label_html() -> str:
    logo_src = clean_logo_src()
    return (
        '<span class="assistant-label-brand">'
        f'<span class="assistant-label-icon"><img src="{logo_src}" alt="SkillWiki logo"/></span>'
        '<span class="assistant-label-text">Skill<span>Wiki</span></span>'
        "</span>"
    )


def render_message(role: str, content: str, trace: dict[str, str] | None = None) -> None:
    body_html = format_message_html(content)
    trace_html = render_trace_html(trace) if role == "assistant" else ""

    if role == "user":
        st.markdown(
            f"""
            <div class="msg-row user">
              <div class="msg-label user">You</div>
              <div class="msg-bubble user">
                <div class="msg-body">{body_html}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f"""
        <div class="msg-row assistant">
          <div class="msg-label assistant">{render_assistant_label_html()}</div>
          <div class="msg-bubble assistant">
            <div class="msg-body">{body_html}</div>
            {trace_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="SkillWiki",
        page_icon="K",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_clean_styles()
    dataset_name, gemini_model_name, ollama_model_name, ollama_host = build_sidebar()

    selected_graph_path = str(core.GRAPH_OPTIONS[dataset_name])
    graph_payload = core.load_graph(selected_graph_path)
    indexes = core.build_indexes(selected_graph_path)

    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("last_focus", None)
    st.session_state.setdefault("last_evidence", {"top_nodes": [], "related_nodes": [], "relationships": []})
    st.session_state.setdefault("last_query_state", None)
    st.session_state.setdefault("last_answer_trace", None)
    st.session_state.setdefault("pending_prompt", None)
    st.session_state.setdefault("is_processing", False)

    if not st.session_state["messages"]:
        welcome_message = (
            "Hi, I'm SkillWiki. I can help you explore people, roles, reporting lines, departments, locations, "
            "skills, systems, and relationships across the company graph.\n\n"
            "Try something like:\n"
            "- Who reports to the COO?\n"
            "- Who knows Azure?\n"
            "- Who works in Slovakia?"
        )
        st.session_state["messages"].append({"role": "assistant", "content": welcome_message, "trace": None})

    for message in st.session_state["messages"]:
        render_message(message["role"], message["content"], message.get("trace"))

    if st.session_state.get("is_processing") and st.session_state.get("pending_prompt"):
        render_message("user", str(st.session_state["pending_prompt"]))
        st.markdown(
            f"""
            <div class="msg-row assistant">
              <div class="msg-label assistant">{render_assistant_label_html()}</div>
              <div class="thinking-card">Thinking...</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    prompt = st.chat_input(
        "Ask about people, roles, skills, systems, or reporting lines",
        disabled=bool(st.session_state.get("is_processing")),
    )
    if prompt and not st.session_state.get("is_processing"):
        st.session_state["pending_prompt"] = prompt
        st.session_state["is_processing"] = True
        st.rerun()

    if not (st.session_state.get("is_processing") and st.session_state.get("pending_prompt")):
        return

    prompt_text = str(st.session_state["pending_prompt"])
    recent_messages = st.session_state["messages"][-4:]
    st.session_state["messages"].append({"role": "user", "content": prompt_text})

    answer, evidence, backend_used, query_state, answer_trace = core.answer_question(
        prompt_text,
        dataset_name,
        graph_payload,
        indexes,
        gemini_model_name,
        ollama_model_name,
        ollama_host,
        conversation_focus=st.session_state.get("last_focus"),
        recent_messages=recent_messages,
        last_query_state=st.session_state.get("last_query_state"),
        last_evidence=st.session_state.get("last_evidence"),
    )

    st.session_state["messages"].append(
        {
            "role": "assistant",
            "content": answer,
            "trace": answer_trace,
        }
    )
    st.session_state["last_evidence"] = evidence
    st.session_state["last_query_state"] = query_state
    st.session_state["last_focus"] = core.infer_focus_entity(evidence)
    st.session_state["last_answer_trace"] = answer_trace
    st.session_state["pending_prompt"] = None
    st.session_state["is_processing"] = False
    st.rerun()


if __name__ == "__main__":
    main()
