# SkillWiki

SkillWiki is a graph-grounded chat application built on top of enterprise knowledge graph data.

The repository contains:

- `streamlit_app.py`: full internal/demo app
- `streamlit_app_clean.py`: simplified user-facing app
- `Basic Graph`: core enterprise graph
- `Detailed Graph`: extended graph with GitHub and Jira evidence

## Runnable

### Prerequisites

- Python 3.11+
- `pip`
- optional for local model assistance: [Ollama](https://ollama.com/) with `llama3.2`
- optional for cloud model assistance: Gemini API key

### Install

```powershell
pip install -r requirements.txt
```

### Optional `.env`

```env
GEMINI_API_KEY=your_gemini_key
APP_RUNTIME_MODE=local
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
```

### Optional local Ollama setup

```powershell
ollama pull llama3.2
ollama serve
```

### Run clean app - MVP

```powershell
streamlit run streamlit_app_clean.py
```

### Run full app - used for testing

```powershell
streamlit run streamlit_app.py
```

### Run local knowledge graph visualization

```powershell
python -m http.server 8000
```

Then open:

```text
http://127.0.0.1:8000/docs/
```

## Documentation Map

- Architecture diagram: `drawio_diagrams/ARCHITECTURE_DIAGRAM.drawio` and `drawio_diagrams/ARCHITECTURE_DIAGRAM.png` 
- Data lineage diagram: `drawio_diagrams/DATA_LINEAGE.drawio` and `drawio_diagrams/DATA_LINEAGE.png`

## Technical Standards

### Code Quality

The project follows a simple MVP-oriented Python structure with descriptive naming for graph loading, query normalization, retrieval, routing, and answer generation. The main app (`streamlit_app.py`) contains the full demo/testing interface, while `streamlit_app_clean.py` provides the simplified user-facing chat.

Known improvement area: if the MVP grows, the large Streamlit app should be split into smaller service modules for graph access, query routing, model orchestration, and UI rendering.

### Security and Privacy

Secrets must stay outside Git. Use `.env` for local development and Streamlit secrets for cloud deployment, especially for `GEMINI_API_KEY`.

The project uses synthetic organizational data to reduce GDPR and personal-data risk during development and demonstration. Production use would require access control, audit logging, and validation against approved HR or enterprise data sources.


### Version Control and Maintainability

Generated cache files, local secrets, and temporary render outputs should remain excluded from version control. For production-grade development, future work should use feature branches, pull requests, release tags, and CI checks that run the test suite before deployment.


## Links
- Knowledge Graph: https://phax00.github.io/team_i/
- SkillWiki Chat: https://skillwiki.streamlit.app/

