# SecondSelf Phase-Wise Implementation Plan

## 1. Purpose

This plan converts the SecondSelf architecture and four-week problem statement into an executable implementation sequence.

The implementation follows this flow:

```text
Capture -> Classify -> Embed -> Auto-link -> Build graph -> Retrieve -> Answer -> Deploy
```

The system should remain local-first, human-readable, repeatable, and testable at every phase.

---

## 2. Delivery Strategy

### Primary Goals

- Capture notes, links, and files from one interface.
- Preserve every raw capture with a timestamp and unique ID.
- Automatically classify captures using PARA.
- Generate tags and summaries with an LLM.
- Compute local embeddings and discover related notes.
- Export the knowledge graph as deterministic JSON.
- Render the graph interactively in Streamlit.
- Answer natural-language questions using retrieved personal knowledge.
- Deploy the working system to a public URL.

### Implementation Principles

- Build each phase on the output of the previous phase.
- Keep raw captures immutable.
- Make processing idempotent.
- Keep LLM providers replaceable.
- Use local embeddings to reduce cost and protect privacy.
- Cite source notes in generated answers.
- Test every milestone with real personal data.
- Record failures instead of silently dropping captures.

---

## 3. Phase Summary

| Phase | Name | Main Result |
|---|---|---|
| 0 | Foundation | Runnable project structure and configuration |
| 1 | The Archivist | Reliable capture pipeline |
| 2 | The Librarian | PARA classification and organized wiki |
| 3 | Connect the Dots | Embeddings and automatic note links |
| 4 | The Cartographer | JSON knowledge graph and interactive visualization |
| 5 | The Oracle | Retrieval-augmented question answering |
| 6 | Product Assembly | Unified Streamlit application |
| 7 | Deployment and Verification | Public release and end-to-end validation |

---

# Phase 0: Foundation

## Objective

Create the project skeleton, configuration, dependency management, and storage directories required by all later phases.

## Tasks

- Create the project directories:
  - `raw/captures/`
  - `raw/attachments/`
  - `wiki/Projects/`
  - `wiki/Areas/`
  - `wiki/Resources/`
  - `wiki/Archives/`
  - `data/embeddings/`
- Create the Python package for reusable logic.
- Create CLI script locations.
- Add `requirements.txt`.
- Add `.env.example`.
- Add `.gitignore`.
- Add a central configuration module.
- Add a README with local setup instructions.
- Verify the project runs with a basic health check.

## Suggested Structure

```text
secondself/
├── raw/
│   ├── captures/
│   └── attachments/
├── wiki/
│   ├── Projects/
│   ├── Areas/
│   ├── Resources/
│   └── Archives/
├── data/
│   └── embeddings/
├── scripts/
├── secondself/
├── tests/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Configuration

Define configurable values for:

```text
RAW_DIR
WIKI_DIR
DATA_DIR
EMBEDDING_MODEL
SIMILARITY_THRESHOLD
TOP_K
LLM_PROVIDER
LLM_MODEL
```

Recommended initial values:

```text
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
SIMILARITY_THRESHOLD=0.68
TOP_K=5
LLM_PROVIDER=groq
LLM_MODEL=llama-3.1-8b-instant
```

## Exit Criteria

- The project directories exist.
- Dependencies install successfully.
- Configuration loads without an API key.
- A basic Python command runs from the project root.
- No secrets are committed.

---

# Phase 1: The Archivist

## Objective

Build one capture command that saves notes, links, and files into `raw/` without losing original content.

## Main Component

```text
scripts/capture.py
```

## Capture Commands

```bash
python scripts/capture.py note "An idea about building a personal knowledge graph"
python scripts/capture.py link "https://example.com/article" --title "Useful article"
python scripts/capture.py file "C:\Users\Name\Documents\paper.pdf"
```

Optional modes:

```bash
python scripts/capture.py note --stdin
python scripts/capture.py note --file note.txt
```

## Raw Capture Contract

Each capture should contain:

```json
{
  "id": "cap_20260918_7f3a2c",
  "captured_at": "2026-09-18T14:32:10Z",
  "type": "note",
  "source": "cli",
  "title": "Learning about vector search",
  "content": "Vector search finds semantically similar content...",
  "url": null,
  "file_path": null,
  "status": "unprocessed"
}
```

## Implementation Tasks

- Create a timestamp-based ID with a UUID fragment.
- Store all timestamps in UTC.
- Validate note text is not empty.
- Validate links use a supported URL format.
- Copy files into `raw/attachments/` using collision-safe names.
- Preserve the original filename and file type.
- Store structured metadata as JSON.
- Store human-readable content where useful.
- Print the generated capture ID after success.
- Return a non-zero exit code for invalid input.

## Tests

- Capture a plain note.
- Capture a note from a file.
- Capture a note from standard input.
- Capture a link with and without a custom title.
- Capture a PDF or other real file.
- Capture two items quickly and confirm IDs differ.
- Confirm timestamps are present and parseable.
- Confirm file content is copied and the original metadata is preserved.

## Real Data Milestone

Capture at least 10 real items:

- Notes and ideas.
- Useful links or bookmarks.
- Documents, PDFs, or other files.

Do not use only synthetic test data for this milestone.

## Exit Criteria

- `raw/` and `wiki/` exist.
- One command supports notes, links, and files.
- Every capture has a unique ID and timestamp.
- At least 10 real captures are stored.
- Raw captures are not overwritten by later processing.

**Milestone:** The Archivist

---

# Phase 2: The Librarian

## Objective

Transform raw captures into structured, human-readable wiki notes using PARA classification, tags, summaries, and titles.

## Main Components

```text
scripts/classify.py
secondself/llm.py
secondself/models.py
secondself/storage.py
```

## Classification Contract

```json
{
  "category": "Projects",
  "tags": ["secondself", "architecture", "ai"],
  "summary": "Architecture notes for building the SecondSelf knowledge system.",
  "title": "SecondSelf Architecture"
}
```

## PARA Rules

- **Projects**: A defined outcome, deliverable, or deadline.
- **Areas**: An ongoing responsibility or domain of attention.
- **Resources**: Useful reference material with no immediate deliverable.
- **Archives**: Inactive, completed, or no-longer-relevant material.

## Implementation Tasks

- Define a provider-neutral `LLMProvider` interface.
- Implement the initial Groq provider.
- Load the API key from environment variables or deployment secrets.
- Send the raw capture content to the classifier.
- Require valid JSON from the model.
- Validate the category against the four PARA values.
- Validate tags and summary lengths.
- Retry malformed JSON once.
- Record `classification_failed` if the retry fails.
- Generate a Markdown wiki note.
- Place the note in the matching PARA directory.
- Preserve the original capture ID.
- Add processing timestamps and model metadata.
- Keep the raw capture unchanged.

## Wiki Note Contract

```markdown
---
id: cap_20260918_7f3a2c
title: Learning about vector search
category: Resources
tags:
  - embeddings
  - retrieval
summary: Vector search retrieves semantically related knowledge.
created_at: 2026-09-18T14:32:10Z
processed_at: 2026-09-18T14:40:00Z
embedding_model: pending
related_notes: []
---

Vector search finds semantically similar content...
```

## Tests

- Valid classification response.
- Invalid PARA category.
- Missing summary.
- Malformed JSON response.
- LLM timeout or API error.
- Duplicate processing of the same capture.
- Correct placement in each PARA directory.
- Correct preservation of original content.

## Real Data Milestone

Process the Week 1 captures and reach at least 15 real processed items. Review a sample from every PARA category and correct prompt or validation issues before continuing.

## Exit Criteria

- Any raw capture can become a wiki note.
- Every wiki note has a PARA category, tags, and summary.
- Failed classifications are visible and recoverable.
- Processing is idempotent.
- At least 15 real items exist in `wiki/`.

**Milestone:** The Librarian

---

# Phase 3: Connect the Dots

## Objective

Generate local embeddings for wiki notes and automatically add links between semantically related notes.

## Main Components

```text
scripts/link.py
secondself/embeddings.py
data/embeddings/embeddings.npy
data/embeddings/index.json
```

## Implementation Tasks

- Load `sentence-transformers/all-MiniLM-L6-v2`.
- Define the text used for embedding:
  - Title.
  - Summary.
  - Tags.
  - Main note content.
- Generate one vector per wiki note.
- Store vectors and an ID-to-row index.
- Compute cosine similarity.
- Compare new notes with existing notes.
- Exclude a note from matching against itself.
- Select the top five candidates.
- Apply a configurable similarity threshold.
- Add bidirectional `[[note-id]]` links.
- Add related note IDs to front matter.
- Prevent duplicate links.
- Store the embedding model name and processing time.
- Rebuild the index when notes change.

## Similarity Rules

For vectors $a$ and $b$:

$$
\operatorname{similarity}(a,b)
=
\frac{a \cdot b}{\|a\|\|b\|}
$$

Initial thresholds:

```text
0.78 or higher: strong relationship
0.68 to 0.78: possible relationship
below 0.68: no automatic link
```

The threshold must be configurable and reviewed against real notes.

## Tests

- Embedding generation returns the expected vector shape.
- Identical or near-identical content produces high similarity.
- Clearly unrelated content produces lower similarity.
- A note does not link to itself.
- Reprocessing does not duplicate links.
- Links are bidirectional.
- Existing manual links are preserved.
- Missing or corrupt embedding indexes can be rebuilt.

## Real Data Milestone

Run the linker over at least 15 real wiki notes. Manually inspect several high-similarity pairs and adjust the threshold if the graph is too dense or too sparse.

## Exit Criteria

- Every processed note has an embedding.
- Embeddings can be loaded without recomputing them.
- Related notes receive automatic links.
- Duplicate links are prevented.
- The process is repeatable and recoverable.

**Milestone:** Self-Organizing Wiki

---

# Phase 4: The Cartographer

## Objective

Convert the wiki into a deterministic nodes-and-edges JSON graph and render it as an interactive force-directed visualization.

## Main Components

```text
scripts/build_graph.py
data/graph.json
app.py or secondself/graph_view.py
```

## Graph Node Contract

Each note becomes a node with:

- `id`
- `label`
- `category`
- `tags`
- `summary`
- `content` or a safe content preview

## Graph Edge Contract

Each relationship becomes an edge with:

- `source`
- `target`
- `weight`
- `type`

Supported edge types:

```text
semantic
manual
shared-tag
```

## Implementation Tasks

- Read all Markdown notes from the four PARA directories.
- Parse YAML front matter.
- Extract note IDs and titles.
- Extract `[[note-id]]` references.
- Resolve links only when target notes exist.
- Build nodes in memory.
- Build edges in memory.
- Preserve similarity weights where available.
- Export valid, clean JSON to `data/graph.json`.
- Make graph output deterministic for the same wiki state.
- Add category-based node colors.
- Render a force-directed graph.
- Support hover tooltips with note summaries or content previews.
- Support drag and zoom.
- Show the selected note's full content in the application.

## Visualization Options

Recommended first choice:

- PyVis embedded in Streamlit.

Alternative choices:

- `streamlit-agraph`.
- A custom component using `vis-network`.
- A custom component using Cytoscape.js.

## Tests

- Every wiki note becomes exactly one node.
- Every valid relationship becomes an edge.
- Missing targets do not crash graph generation.
- Invalid front matter is reported clearly.
- Output JSON can be parsed.
- Rebuilding the graph produces the same output for unchanged input.
- The rendered graph supports hover, drag, and zoom.

## Exit Criteria

- `data/graph.json` contains the real wiki nodes and edges.
- The Streamlit graph renders without dummy data.
- Hover reveals note information.
- Drag and zoom work.
- Nodes are visually distinguishable by PARA category.

**Milestone:** The Cartographer

---

# Phase 5: The Oracle

## Objective

Answer natural-language questions using relevant notes retrieved from the local embedding index and an LLM for synthesis.

## Main Components

```text
secondself/retrieval.py
secondself/ask.py
secondself/llm.py
```

## Retrieval Flow

```text
question
  -> question embedding
  -> nearest wiki notes
  -> optional one-hop graph expansion
  -> context assembly
  -> LLM synthesis
  -> answer with sources
```

## Implementation Tasks

- Embed the user's question with the same model used for notes.
- Search the embedding index.
- Return the top five relevant notes.
- Apply a minimum retrieval similarity threshold.
- Optionally add directly linked neighbors.
- Remove duplicate notes from context.
- Enforce a context-size limit.
- Build a source-aware prompt.
- Call the configured LLM provider.
- Require the answer to use only supplied context.
- Return source note IDs and titles.
- Explain when the notes do not contain enough information.
- Separate evidence from inference where appropriate.

## Answer Contract

```python
{
    "answer": "...",
    "sources": [
        {
            "id": "cap_20260918_7f3a2c",
            "title": "Learning about vector search",
            "similarity": 0.84
        }
    ]
}
```

## Suggested Defaults

```text
top_k = 5
retrieval_threshold = 0.60
neighbor_expansion = 1 graph hop
```

## Tests

- A question retrieves a known relevant note.
- An unrelated question does not receive fabricated information.
- The answer includes source notes.
- Empty indexes produce a clear response.
- Missing API keys produce an actionable error.
- LLM failures do not expose secrets.
- Context is limited to the configured size.
- Retrieval uses the same embedding model as indexing.

## Real Data Milestone

Create at least five real questions whose answers exist in the captured knowledge. Record whether the correct notes were retrieved and whether the final answer was grounded in those notes.

## Exit Criteria

- `ask()` returns synthesized answers.
- Answers are grounded in retrieved notes.
- Sources are visible to the user.
- Unknown questions are handled honestly.
- Retrieval and synthesis can be tested independently.

**Milestone:** The Oracle

---

# Phase 6: Product Assembly

## Objective

Combine capture, graph exploration, and question answering into one Streamlit application.

## Main Component

```text
app.py
```

## Application Views

### Ask View

- Question input.
- Submit action.
- Answer display.
- Source note list.
- Similarity scores.
- Expandable source content.

### Brain View

- Interactive force-directed graph.
- Category-based node styling.
- Hover summaries.
- Drag and zoom.
- Selected-note content panel.

### Capture View

- Note input.
- URL input.
- File uploader.
- Capture action.
- Generated ID.
- Processing status.

## Implementation Tasks

- Add sidebar navigation.
- Load graph data from `data/graph.json`.
- Load retrieval index and wiki notes.
- Connect the ask view to `ask()`.
- Connect the graph view to the graph renderer.
- Connect the capture view to the capture pipeline.
- Display clear errors for missing data or secrets.
- Add loading indicators for embedding and LLM operations.
- Prevent accidental duplicate submissions.
- Keep the public app usable when write persistence is unavailable.
- Add a read-only mode for deployment if needed.

## Local Run Command

```bash
streamlit run app.py
```

## Exit Criteria

- One Streamlit app contains the graph and ask interface.
- The app can display real wiki data.
- Questions return grounded answers and sources.
- The graph is interactive.
- Capture behavior is clearly reported.
- The app handles empty or incomplete data without crashing.

---

# Phase 7: Deployment and Verification

## Objective

Deploy the complete system publicly and verify the complete flow from capture through answer generation.

## Recommended Platform

Use Streamlit Community Cloud for the first release.

## Deployment Tasks

- Create or prepare the GitHub repository.
- Add `requirements.txt`.
- Add Streamlit configuration if needed.
- Commit curated `wiki/` and `data/` content.
- Configure `GROQ_API_KEY` as a platform secret.
- Configure other environment variables as deployment secrets or variables.
- Set the Streamlit entry point to `app.py`.
- Deploy the application.
- Open the public URL in a clean browser session.
- Verify graph rendering.
- Verify question answering.
- Verify source display.
- Verify capture behavior and persistence expectations.
- Document the public URL in the README.

## Persistence Decision

A deployed Streamlit filesystem may not be durable. Select one mode explicitly:

### Mode A: Read-Only Public Demo

- Process notes locally.
- Deploy curated wiki and graph data.
- Disable or clearly limit public capture.

### Mode B: Git-Backed Persistence

- Capture creates repository changes.
- A controlled integration commits changes.
- Reprocessing occurs through a separate workflow.

### Mode C: External Persistence

- Store captures and metadata in a hosted database or object store.
- Use a background worker for classification and linking.

For the first public milestone, Mode A is the lowest-risk option.

## End-to-End Verification

Run this checklist against the deployed URL:

- [ ] Public URL opens without authentication problems.
- [ ] Graph loads using real notes.
- [ ] Graph supports hover, drag, and zoom.
- [ ] A graph node reveals its note content.
- [ ] Ask view accepts a natural-language question.
- [ ] Answer is synthesized from personal notes.
- [ ] Answer shows source notes.
- [ ] Unknown information is not fabricated.
- [ ] Capture view accepts a note, link, and file where deployment mode allows it.
- [ ] Errors are understandable to a normal user.
- [ ] README contains setup instructions and public URL.

**Milestone:** SecondSelf deployment

---

# 4. Cross-Phase Quality Gates

## Data Integrity

- Raw captures are immutable.
- No capture loses its original content.
- Every processed note retains its source capture ID.
- File attachments use collision-safe paths.

## Reliability

- Every phase is idempotent.
- One failed item does not stop a batch.
- Failed items include an error status and message.
- Indexes and graph files can be rebuilt.

## AI Safety and Quality

- LLM output is schema-validated.
- PARA categories are restricted to known values.
- Answers are grounded in retrieved context.
- Sources are shown with generated answers.
- Secrets are not logged or committed.

## Reproducibility

- Configuration is documented.
- Model names are stored.
- Dependency versions are pinned or constrained.
- The README explains the complete local workflow.

---

# 5. Suggested Command Sequence

After implementation, the expected local workflow should look like this:

```bash
# Install dependencies
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Capture real information
python scripts/capture.py note "A real idea from my notes"
python scripts/capture.py link "https://example.com" --title "A real reference"
python scripts/capture.py file "C:\Users\Name\Documents\real-document.pdf"

# Process the knowledge base
python scripts/classify.py process-all
python scripts/link.py rebuild
python scripts/build_graph.py

# Run the application
streamlit run app.py
```

The exact command names may be consolidated into a single pipeline CLI, but each operation should remain independently testable.

---

# 6. Final Deliverables Checklist

## Repository

- [ ] Clean GitHub repository.
- [ ] README with setup instructions.
- [ ] `requirements.txt`.
- [ ] `.env.example`.
- [ ] No committed secrets.

## Week 1

- [ ] `raw/` and `wiki/` folders exist.
- [ ] Note capture works.
- [ ] Link capture works.
- [ ] File capture works.
- [ ] At least 10 real captures exist.

## Week 2

- [ ] PARA classification works.
- [ ] Tags and summaries are generated.
- [ ] At least 15 real wiki notes exist.
- [ ] Embeddings are generated.
- [ ] Related notes are automatically linked.

## Week 3

- [ ] Graph JSON is generated.
- [ ] Every note becomes a graph node.
- [ ] Relationships become graph edges.
- [ ] Interactive graph renders.
- [ ] Hover, drag, and zoom work.

## Week 4

- [ ] `ask()` retrieves relevant notes.
- [ ] LLM synthesizes grounded answers.
- [ ] Answers include sources.
- [ ] Streamlit contains graph and ask views.
- [ ] Application is deployed publicly.
- [ ] End-to-end flow is verified.

---

# 7. Definition of Done

SecondSelf is complete when a user can:

1. Capture a note, link, or file.
2. See the item preserved in `raw/`.
3. Process it into the correct PARA location.
4. See tags and a summary generated automatically.
5. See related notes linked through embeddings.
6. Explore all notes in an interactive graph.
7. Ask a natural-language question.
8. Receive an answer grounded in their own notes.
9. Inspect the sources used for that answer.
10. Open the same experience through a public URL.

This is the final end-to-end acceptance condition for the SecondSelf system.
