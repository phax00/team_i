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
            border-radius: 24px;
            padding: 1.3rem 1.4rem 1.1rem 1.4rem;
            margin-bottom: 1rem;
            box-shadow: 0 16px 40px rgba(123, 58, 237, 0.08);
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

        .chip-row {
            display: flex;
            gap: 0.55rem;
            flex-wrap: wrap;
            margin-top: 0.9rem;
        }

        .chip {
            display: inline-flex;
            align-items: center;
            padding: 0.44rem 0.72rem;
            border-radius: 999px;
            border: 1px solid var(--border);
            background: var(--primary-soft);
            color: var(--primary-dark);
            font-size: 0.83rem;
            font-weight: 700;
        }

        .stChatMessage {
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 0.15rem 0.2rem;
        }

        .stChatMessage [data-testid="stMarkdownContainer"] p {
            line-height: 1.58;
        }

        .answer-meta {
            margin-top: 0.45rem;
            color: var(--muted);
            font-size: 0.8rem;
        }

        .answer-meta strong {
            color: var(--primary-dark);
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
        </style>
        """,
        unsafe_allow_html=True,
    )


def build_sidebar() -> tuple[str, str, str, str]:
    with st.sidebar:
        st.markdown("### SkillWiki")

        dataset_name = st.selectbox("Dataset", list(core.GRAPH_OPTIONS.keys()), index=0)
        ollama_model_name = core.get_secret_or_env("OLLAMA_MODEL", "llama3.2")
        ollama_host = core.get_secret_or_env("OLLAMA_HOST", "http://127.0.0.1:11434")

        ollama_available = core.is_ollama_available(ollama_host)
        runtime_mode = core.detect_runtime_mode(ollama_available)
        gemini_disabled = bool(st.session_state.get("gemini_model_disabled", False))
        gemini_ready = bool(core.get_api_key()) and not gemini_disabled
        model_available = ollama_available if runtime_mode == "local" else gemini_ready
        default_model_enabled = model_available if runtime_mode == "local" else False

        use_model = st.toggle(
            "Use model assistance",
            value=default_model_enabled,
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


def render_trace(trace: dict[str, str] | None) -> None:
    if not trace:
        return
    final_backend = trace.get("final_backend", "Unknown")
    interpreter_backend = trace.get("interpreter_backend", "None")
    resolution_mode = trace.get("resolution_mode", "Unknown")
    st.markdown(
        f"""
        <div class="answer-meta">
          <strong>Answered with:</strong> {final_backend}
          &nbsp;|&nbsp;
          <strong>Interpreted with:</strong> {interpreter_backend}
          &nbsp;|&nbsp;
          <strong>Mode:</strong> {resolution_mode}
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

    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                render_trace(message.get("trace"))

    prompt = st.chat_input("Ask about people, roles, skills, systems, or reporting lines")
    if not prompt:
        return

    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
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
        st.markdown(answer)
        render_trace(answer_trace)

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
