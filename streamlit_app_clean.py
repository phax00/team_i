import html
import re

import streamlit as st

import streamlit_app as core


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
            padding-top: 1.6rem;
            padding-bottom: 2.2rem;
        }

        section[data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.82);
            border-right: 1px solid var(--border);
        }

        .clean-hero {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 22px;
            padding: 1.15rem 1.3rem 1rem 1.3rem;
            margin-bottom: 1.1rem;
            box-shadow: 0 14px 32px rgba(123, 58, 237, 0.08);
        }

        .clean-eyebrow {
            color: var(--primary);
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.72rem;
            font-weight: 700;
            margin-bottom: 0.45rem;
        }

        .clean-title {
            font-size: 2rem;
            line-height: 1.05;
            font-weight: 800;
            margin-bottom: 0.4rem;
        }

        .skillwiki-logo {
            font-size: 2.05rem;
            line-height: 1;
            font-weight: 900;
            letter-spacing: -0.04em;
            margin-bottom: 0.45rem;
            color: #141414;
        }

        .skillwiki-logo span {
            color: var(--primary);
        }

        .clean-subtitle {
            color: var(--muted);
            font-size: 0.98rem;
            line-height: 1.55;
        }

        .conversation {
            display: flex;
            flex-direction: column;
            gap: 0.9rem;
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
        st.markdown("### SkillWiki")

        dataset_options = list(core.GRAPH_OPTIONS.keys())
        default_dataset_index = dataset_options.index("Detailed Graph") if "Detailed Graph" in dataset_options else 0
        dataset_name = st.selectbox("Dataset", dataset_options, index=default_dataset_index)
        ollama_model_name = core.get_secret_or_env("OLLAMA_MODEL", "llama3.2")
        ollama_host = core.get_secret_or_env("OLLAMA_HOST", "http://127.0.0.1:11434")

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


def render_header(dataset_name: str) -> None:
    st.markdown(
        f"""
        <div class="clean-hero">
          <div class="clean-eyebrow">Enterprise Assistant</div>
          <div class="skillwiki-logo">Skill<span>Wiki</span></div>
          <div class="clean-subtitle">
            Ask direct questions about people, roles, skills, systems, locations, and reporting lines.
            Answers stay grounded in the selected graph.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


def render_message(role: str, content: str, trace: dict[str, str] | None = None) -> None:
    label = "You" if role == "user" else "SkillWiki"
    role_class = "user" if role == "user" else "assistant"
    body_html = format_message_html(content)
    trace_html = render_trace_html(trace) if role == "assistant" else ""

    st.markdown(
        f"""
        <div class="msg-row {role_class}">
          <div class="msg-label">{label}</div>
          <div class="msg-bubble {role_class}">
            <div class="msg-body">{body_html}</div>
            {trace_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
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

    render_header(dataset_name)

    if not st.session_state["messages"]:
        st.info("Try a question like `Who reports to the COO?`, `Who knows Azure?`, or `How is Petra related to Filip?`")

    st.markdown('<div class="conversation">', unsafe_allow_html=True)
    for message in st.session_state["messages"]:
        render_message(message["role"], message["content"], message.get("trace"))
    st.markdown("</div>", unsafe_allow_html=True)

    prompt = st.chat_input("Ask about people, roles, skills, systems, or reporting lines")
    if not prompt:
        return

    st.session_state["messages"].append({"role": "user", "content": prompt})
    render_message("user", prompt)

    thinking_placeholder = st.empty()
    thinking_placeholder.markdown(
        """
        <div class="msg-row assistant">
          <div class="msg-label">SkillWiki</div>
          <div class="thinking-card">Thinking...</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    answer, evidence, backend_used, query_state, answer_trace = core.answer_question(
        prompt,
        dataset_name,
        graph_payload,
        indexes,
        gemini_model_name,
        ollama_model_name,
        ollama_host,
        conversation_focus=st.session_state.get("last_focus"),
        recent_messages=st.session_state.get("messages"),
        last_query_state=st.session_state.get("last_query_state"),
        last_evidence=st.session_state.get("last_evidence"),
    )
    thinking_placeholder.empty()
    render_message("assistant", answer, answer_trace)

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


if __name__ == "__main__":
    main()
