# Deployment Plan for SecondSelf on Streamlit

## Goal

Deploy the SecondSelf project as a public Streamlit application that lets a user:

- capture notes and links from the browser
- process raw captures into PARA-organized wiki notes
- rebuild the graph and visualize knowledge connections
- ask plain-English questions over the stored notes

The deployment should be simple, low-cost, and easy to maintain while keeping the app functional in a hosted environment.

---

## 1. Deployment Target

Use Streamlit Community Cloud as the primary deployment target because it is:

- free for small apps and demos
- works well with GitHub-based repos
- supports environment secrets such as `GROQ_API_KEY`
- straightforward to configure for a Python app with `app.py` as the entry point

Alternative options:

- Hugging Face Spaces
- Railway
- Render
- self-hosted container on a VPS

Streamlit Community Cloud is the best fit for this project because the repo is already organized around a single `app.py` entry point and Python dependencies.

---

## 2. Deployment Requirements

### Required files

The app will require the following project files in the repo root:

- `app.py`
- `requirements.txt`
- `.env.example` (for local setup only)
- `secondself/` package
- `wiki/` data
- `data/graph.json`
- `data/embeddings/` if precomputed
- `README.md`

### Required secrets

Set the following secret in the Streamlit Cloud dashboard:

- `GROQ_API_KEY`

Optional values for future flexibility:

- `LLM_MODEL`
- `EMBEDDING_MODEL`
- `SIMILARITY_THRESHOLD`
- `TOP_K`

---

## 3. Deployment Architecture

### Runtime flow

1. Streamlit app loads `app.py`
2. `load_graph()` reads `data/graph.json` or rebuilds it from `wiki/`
3. User enters a new note or link in the app sidebar
4. The app stores the capture in `raw/`
5. The user clicks Refresh Graph
6. The app runs `Classifier.process_all()` and `link_all()`
7. The app builds a fresh graph JSON from the wiki
8. The user asks a question through the ask bar
9. The app retrieves the most similar notes and calls the LLM for synthesis

### Hosted behavior

Because Streamlit Cloud runs ephemeral app instances, the app should be designed to:

- rebuild graph data on demand
- avoid requiring a persistent local filesystem beyond the repo checkout
- work with data that is committed into the repo for demo use
- gracefully handle missing API keys or missing data

---

## 4. Data Strategy for Deployment

### Local-first project behavior

This project is local-first, but public deployment still needs a stable, demo-friendly dataset.

Recommended approach:

- keep the repo committed with a small but meaningful sample of `wiki/` content
- keep `data/graph.json` checked in for immediate graph rendering
- keep embeddings or allow the app to rebuild them at runtime if no key is available
- keep the public app focused on a curated or demo-safe knowledge base

### Security note

If this will be public, avoid storing private or sensitive notes in the repo and in the deployed branch. Use only safe demo content or a sanitized knowledge base.

---

## 5. Pre-deployment Checklist

Before pushing to GitHub and connecting Streamlit Cloud, confirm the following:

- [ ] `app.py` runs without import errors
- [ ] `requirements.txt` includes all necessary dependencies
- [ ] `README.md` explains setup and usage
- [ ] `wiki/` contains valid Markdown notes
- [ ] `data/graph.json` exists and is valid JSON
- [ ] `GROQ_API_KEY` is configured locally for testing
- [ ] The app handles missing or empty data gracefully
- [ ] The UI loads without crashing
- [ ] The answer flow returns a result from notes or an informative fallback

---

## 6. Deployment Steps

### Step 1: Prepare the repository

1. Commit the final app and supporting files
2. Ensure `.gitignore` excludes local virtual environment and temporary files
3. Keep the repo clean and production-focused
4. Make sure `app.py` is at the root

### Step 2: Ensure the app runs locally

Use:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m streamlit run app.py
```

Check:

- the app loads
- graph renders
- ask flow works
- no fatal errors appear in the logs

### Step 3: Provide demo data

Because the deployment environment is public and may be reset, commit a small valid dataset:

- demo wiki notes under `wiki/`
- a valid `data/graph.json`
- any required embeddings or regeneration logic

### Step 4: Push to GitHub

1. Create a public GitHub repository
2. Commit all source files
3. Push to the default branch

### Step 5: Connect to Streamlit Community Cloud

In Streamlit Cloud:

1. Select New app
2. Choose the GitHub repo
3. Set the app file to `app.py`
4. Set the Python version compatible with the project
5. Add the secret `GROQ_API_KEY`
6. Deploy the app

### Step 6: Validate the deployment

Open the deployed URL and verify:

- the title loads
- the graph renders
- the Q&A input responds
- the capture button works in the browser
- full app startup does not crash

---

## 7. Production Considerations

### 1. API failures

The app should catch missing or invalid API responses and show a helpful fallback message instead of crashing.

Recommended behavior:

- if `GROQ_API_KEY` is missing, show a warning in the UI
- if the LLM call fails, answer from cached fallback logic or state: “I don’t have notes about that.”

### 2. Cold starts

Streamlit Cloud may start the app in a clean environment.

Mitigation:

- include demo data in the repo
- avoid requiring a long upfront model download on every cold start
- keep the initial graph and note set lightweight

### 3. Large graphs

If the wiki grows large, the graph may become visually noisy.

Mitigation:

- cap edges or visible note count
- limit node rendering on large datasets
- allow filtering by PARA category

### 4. Public exposure

This app answers from personal knowledge notes. If this repo is public, avoid committing private content.

---

## 8. Recommended Deployment Command Sequence

```bash
# local validation
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m streamlit run app.py

# before deployment
python -m pytest -q
python -c "import app; print('app import ok')"
```

---

## 9. Final Deployment Goal

The final deployed app should:

- start successfully on Streamlit Cloud
- load a graph from the repo data
- support plain-English Q&A over the knowledge base
- provide a usable interface for note capture and refresh
- be public and easy to share

---

## 10. Deliverables

The deployment phase should produce:

- a public GitHub repository
- a working Streamlit app on the cloud
- environment variable setup for `GROQ_API_KEY`
- a stable README with running instructions
- a verified app URL that loads successfully

---

## 11. Recommended Next Step

Once the project is validated locally, the next step is to:

1. push to GitHub
2. connect the repo to Streamlit Community Cloud
3. set the app file to `app.py`
4. add `GROQ_API_KEY`
5. deploy and test the public URL

This is the standard path for shipping the SecondSelf project as a public knowledge app.
