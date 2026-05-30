# Graph Viewer Deployment

The static viewer lives in [docs/index.html](/C:/Users/vikip/Downloads/VSE/ADA/02_semester/Proj/docs/index.html) and reads graph JSON files from `docs/data/`.

Current datasets:

- `knowledge_graph_core.json`
- `knowledge_graph_school_mvp.json`

## Update the data

Whenever the core graph changes, run:

```powershell
python generate_core_knowledge_graph.py
```

Whenever the school MVP graph changes, run:

```powershell
python generate_school_mvp_graph.py
```

Then rebuild the static viewer assets:

```powershell
python build_graph_viewer_assets.py
```

That copies the current graph into `docs/data/` so the static app can serve it.

## Local preview

Run a simple HTTP server from the project root:

```powershell
python -m http.server 8000
```

Then open:

```text
http://127.0.0.1:8000/docs/
```

`file://` preview is not recommended because browser fetch rules may block JSON loading.

## GitHub Pages

Use the `docs/` folder as the publish source.

Typical flow:

1. Push the repository to GitHub.
2. In repository settings, open `Pages`.
3. Choose `Deploy from a branch`.
4. Select your branch and folder `docs`.
5. Save.

The viewer will be served directly from the repo without any backend.

## Vercel

Create a new project from the GitHub repository and set:

- Framework preset: `Other`
- Root directory: project root
- Output/public directory: `docs`

No build command is required if `docs/data/knowledge_graph_core.json` is already committed.

## Netlify

Create a new site from Git and set:

- Base directory: empty
- Publish directory: `docs`
- Build command: empty

## Recommended workflow

1. Regenerate the graph if needed.
2. Run `python build_graph_viewer_assets.py`.
3. Commit the updated files in `docs/`.
4. Push to GitHub.
5. GitHub Pages, Vercel, or Netlify will serve the same static viewer.
