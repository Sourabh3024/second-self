# SecondSelf

SecondSelf is a local-first personal knowledge system that captures notes, links, and files, organizes them with PARA, connects related knowledge, renders an interactive graph, and answers questions from the user's own notes.

## Phase 0 Status

The project foundation is ready:

- Raw capture directories exist.
- PARA wiki directories exist.
- Embedding storage is reserved.
- Central configuration is available through `secondself/config.py`.
- A Streamlit entry point is available for later phases.
- A dependency manifest and environment template are included.
- A foundation health check and configuration tests are included.

## Local Setup

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

### Verify the Foundation

Run from the project root:

```powershell
python scripts/healthcheck.py
pytest -q
```

The health check does not require an LLM API key. Later phases will use `GROQ_API_KEY` for classification and answer synthesis.

## Capture a Raw Item

Phase 1 supports notes, links, and files from one command:

```powershell
python scripts/capture.py note "An idea about building a personal knowledge graph"
python scripts/capture.py note --file .\my-note.txt
python scripts/capture.py note --stdin
python scripts/capture.py link "https://example.com/article" --title "Useful article"
python scripts/capture.py file "C:\Users\Name\Documents\paper.pdf"
```

Each successful capture creates an immutable JSON record in `raw/captures/` with a UTC timestamp, unique ID, original content or URL, and `unprocessed` status. File captures are copied into `raw/attachments/` and include their original filename, size, and SHA-256 checksum.

## Project Layout

```text
raw/                  Immutable captures and file attachments
wiki/                 PARA-organized Markdown notes
data/                 Derived indexes and graph data
secondself/           Reusable application logic
scripts/              Command-line entry points
tests/                Automated tests
app.py                Streamlit application entry point
```

## Planned Workflow

```text
Capture -> Classify -> Embed -> Auto-link -> Build graph -> Retrieve -> Answer -> Deploy
```

Implementation details are documented in [architecture.md](architecture.md) and [implementation-plan.md](implementation-plan.md).
