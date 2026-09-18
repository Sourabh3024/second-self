# SecondSelf Edge Cases and Corner Scenarios

## 1. Purpose

This document records corner scenarios, failure modes, validation rules, and recovery behavior for the SecondSelf system.

The system must preserve information, fail visibly, avoid duplicate work, and prevent unsupported AI-generated answers. The expected behavior for every edge case is either:

- Reject the input safely and explain why.
- Preserve the input while marking processing as failed.
- Retry a transient operation.
- Skip only the invalid relationship or item and continue the batch.
- Return an honest uncertainty message instead of inventing information.

The main pipeline is:

```text
Capture -> Classify -> Embed -> Auto-link -> Build graph -> Retrieve -> Answer -> Deploy
```

---

## 2. Global Rules

### 2.1 Never Lose Raw Information

- Raw captures are immutable.
- Classification, embedding, linking, and graph generation must never overwrite the original capture content.
- If processing fails, preserve the capture with a failure status and error details.
- File attachments must be copied before downstream processing begins.

### 2.2 Make Operations Idempotent

Running the same command more than once must not:

- Create duplicate captures.
- Create duplicate wiki notes.
- Create duplicate links.
- Add duplicate graph nodes or edges.
- Corrupt existing metadata.

### 2.3 Fail Per Item

A malformed capture, unavailable URL, corrupt document, or failed LLM response must not stop a batch containing otherwise valid items.

### 2.4 Keep External Services Optional Where Possible

- Capture must work without an LLM API key.
- Embeddings should work locally without an external API.
- Graph generation must work without an LLM.
- The application should explain which features are unavailable when configuration is incomplete.

### 2.5 Protect Secrets and Personal Data

- Never write API keys to raw captures, logs, graph data, or error messages.
- Do not include private file paths in public graph output unless explicitly intended.
- Do not expose full note contents in hover tooltips if the deployment is public and the content is private.
- Avoid logging raw personal content by default.

---

# 3. Foundation and Configuration Edge Cases

## EC-F01: Missing Project Directories

**Scenario:** `raw/`, `wiki/`, or `data/` does not exist.

**Expected behavior:** Create required directories during setup or before the first write.

**Failure behavior:** If directory creation fails because of permissions, stop the operation with the exact path and required permission.

## EC-F02: Running From the Wrong Working Directory

**Scenario:** A script is executed from outside the project root.

**Expected behavior:** Resolve paths relative to the project root or clearly require the project root and report the expected location.

**Risk:** Relative paths can write data into an unintended directory.

## EC-F03: Missing Environment File

**Scenario:** `.env` is absent.

**Expected behavior:** Local non-LLM commands continue to work. LLM-dependent commands show a configuration error only when invoked.

## EC-F04: Missing API Key

**Scenario:** `GROQ_API_KEY` is not configured.

**Expected behavior:** Capture, local embedding, and graph generation continue to work. Classification and answer synthesis return an actionable error or use an explicitly configured offline fallback.

**Must not happen:** The application must not display the secret or repeatedly retry a permanently missing key.

## EC-F05: Invalid Configuration Values

**Scenarios:**

- Negative `TOP_K`.
- Similarity threshold outside the range `[-1, 1]`.
- Empty embedding model name.
- Unknown LLM provider.
- Unknown PARA category configuration.

**Expected behavior:** Validate configuration at startup and report all invalid values together.

## EC-F06: Dependency or Model Download Failure

**Scenario:** A package cannot be installed or the embedding model cannot be downloaded.

**Expected behavior:** The application starts in a limited mode where possible and explains the unavailable feature. Do not create a partial or falsely valid embedding index.

## EC-F07: Concurrent Writers

**Scenario:** Two capture commands or processes write to the same directory simultaneously.

**Expected behavior:** Use unique filenames and atomic writes. A partially written JSON or Markdown file must never be treated as complete.

## EC-F08: Interrupted Write

**Scenario:** The process is killed while writing a capture, wiki note, index, or graph.

**Expected behavior:** Write to a temporary file and rename it atomically. On restart, ignore or clean up incomplete temporary files.

## EC-F09: Unsupported File System

**Scenario:** The project is stored on a read-only drive, network drive, synchronized folder, or path with unusual characters.

**Expected behavior:** Validate read/write access at startup and use platform-safe path handling. Report the failing operation without losing source data.

## EC-F10: Path Traversal in Titles or Filenames

**Scenario:** A title or original filename contains `../`, drive prefixes, reserved names, or path separators.

**Expected behavior:** Sanitize generated filenames while preserving the original name only as metadata. Never allow user input to escape the configured storage directories.

---

# 4. Capture Edge Cases

## EC-C01: Empty Note

**Scenario:** The user submits an empty string or whitespace-only note.

**Expected behavior:** Reject it with a validation message. Do not create a zero-content capture.

## EC-C02: Very Large Note

**Scenario:** A note is larger than the model context, storage expectation, or application input limit.

**Expected behavior:** Preserve the full raw content. For classification and embedding, use a documented truncation or chunking strategy and record that processing was chunked.

**Must not happen:** Silently discard the end of the note.

## EC-C03: Very Long Single Line

**Scenario:** Content contains a huge unbroken line.

**Expected behavior:** Store it safely and wrap or truncate only in display components. Do not let it break the Markdown renderer or graph tooltip.

## EC-C04: Unicode and Non-ASCII Content

**Scenario:** The note contains Hindi, emoji, accented characters, right-to-left text, or mixed scripts.

**Expected behavior:** Preserve UTF-8 content. Use Unicode-safe file and JSON handling. Display content without encoding errors.

## EC-C05: Null Bytes or Control Characters

**Scenario:** Text contains binary nulls or unsupported control characters.

**Expected behavior:** Reject unsafe text characters or encode them safely. Preserve the original file separately if the source is binary.

## EC-C06: Duplicate Note Submission

**Scenario:** The same note is captured twice intentionally or because the user retries after a timeout.

**Expected behavior:** Each explicit capture may receive its own unique ID, but the system should optionally detect likely duplicates and mark them as duplicates without deleting either raw item.

## EC-C07: Duplicate IDs

**Scenario:** A generated ID collides with an existing ID.

**Expected behavior:** Check for collision and regenerate the UUID fragment. Never overwrite the existing capture.

## EC-C08: Clock Problems

**Scenario:** The system clock changes, the local timezone is invalid, or two captures have the same timestamp.

**Expected behavior:** Store UTC timestamps and use UUID entropy for uniqueness. Do not rely on timestamp alone.

## EC-C09: Link With Invalid URL

**Scenario:** The URL is missing a scheme, contains spaces, is malformed, or uses an unsupported scheme.

**Expected behavior:** Reject unsupported URLs or normalize only safe schemes such as `http` and `https`.

## EC-C10: Link Is Unreachable

**Scenario:** The URL returns a timeout, DNS error, authentication page, rate limit, or server error.

**Expected behavior:** Capture the URL and user-provided title regardless of fetch failure. Mark optional metadata retrieval as failed; do not lose the link capture.

## EC-C11: Link Redirects or Changes Domain

**Scenario:** A URL redirects to another URL or a shortened URL resolves elsewhere.

**Expected behavior:** Preserve the original URL and optionally store the final resolved URL separately. Do not follow untrusted redirects indefinitely.

## EC-C12: Link Contains Sensitive Query Parameters

**Scenario:** A URL contains tokens, session IDs, email addresses, or other secrets in query parameters.

**Expected behavior:** Warn before storing or redact known sensitive parameters. Never expose such URLs in public graph output.

## EC-C13: Missing Link Title

**Scenario:** No title is provided and the page title cannot be fetched.

**Expected behavior:** Generate a safe fallback title from the hostname or URL path.

## EC-C14: File Does Not Exist

**Scenario:** The supplied file path is missing or points to a directory.

**Expected behavior:** Reject the capture before writing metadata.

## EC-C15: File Permission Denied

**Scenario:** The file exists but cannot be read.

**Expected behavior:** Report the permission error and do not create a misleading successful capture.

## EC-C16: File Changes During Copy

**Scenario:** A file is edited while it is being copied.

**Expected behavior:** Capture file size and checksum where practical. If the copy is inconsistent, mark it incomplete and allow retry.

## EC-C17: Unsupported or Unknown File Type

**Scenario:** The file extension is unknown or the file has no extension.

**Expected behavior:** Preserve the original file as an attachment. Mark text extraction as unsupported rather than treating binary bytes as text.

## EC-C18: Corrupt PDF or Document

**Scenario:** A file cannot be parsed.

**Expected behavior:** Preserve the attachment, record extraction failure, and allow the user to add a manual note or retry with another parser.

## EC-C19: Oversized File

**Scenario:** The file exceeds configured storage or processing limits.

**Expected behavior:** Capture metadata and either preserve the file without processing or reject it before copying, according to the configured policy. Report the limit clearly.

## EC-C20: Filename Collision

**Scenario:** Two files have the same original filename.

**Expected behavior:** Store each using the capture ID or a collision-safe suffix. Preserve the original filename in metadata.

## EC-C21: Symbolic Link or Special File

**Scenario:** The supplied path is a symbolic link, device, socket, or other special file.

**Expected behavior:** Reject special files unless explicitly supported. Resolve symlinks safely and prevent access outside allowed directories where required.

## EC-C22: Interrupted File Copy

**Scenario:** The process stops during attachment copying.

**Expected behavior:** Remove or mark the partial destination file. The capture must not reference a complete attachment unless the copy succeeded.

## EC-C23: Duplicate File Content

**Scenario:** The same file is captured under different names.

**Expected behavior:** Use a checksum to detect likely duplicates and warn or link them, while preserving the separate capture records.

---

# 5. Classification and LLM Edge Cases

## EC-L01: Provider Timeout

**Scenario:** The LLM request times out.

**Expected behavior:** Retry only transient failures with bounded backoff. After retry exhaustion, mark the item `classification_failed` and continue the batch.

## EC-L02: Rate Limit

**Scenario:** The provider returns a rate-limit response.

**Expected behavior:** Respect the provider retry interval when available. Do not launch unlimited retries. Report how many items were deferred.

## EC-L03: Provider Outage

**Scenario:** The LLM service is unavailable.

**Expected behavior:** Preserve all raw captures and allow local capture, embedding, and graph operations to continue. Provide a resume command for classification.

## EC-L04: Empty LLM Response

**Scenario:** The provider returns no content.

**Expected behavior:** Treat it as a failed classification, not as a valid empty result.

## EC-L05: Malformed JSON

**Scenario:** The model returns Markdown, commentary, partial JSON, or invalid JSON.

**Expected behavior:** Attempt one constrained repair or retry. Validate the repaired response before writing a wiki note.

## EC-L06: Extra or Missing Fields

**Scenario:** The response omits `summary`, uses a wrong field name, or includes unexpected fields.

**Expected behavior:** Reject or normalize only fields covered by an explicit schema. Required fields must not be guessed silently.

## EC-L07: Invalid PARA Category

**Scenario:** The model returns `Ideas`, `Miscellaneous`, or a misspelled category.

**Expected behavior:** Reject the response and retry with the allowed category list. Never create a directory from arbitrary model output.

## EC-L08: Multiple PARA Categories

**Scenario:** The model returns multiple categories for one item.

**Expected behavior:** Require exactly one primary category. Store secondary concepts as tags if appropriate, but do not create multiple copies of the note.

## EC-L09: Excessive Tags

**Scenario:** The model returns dozens of tags, duplicate tags, empty tags, or tags containing unsafe path characters.

**Expected behavior:** Normalize, deduplicate, cap the number of tags, and keep tags out of filenames and paths.

## EC-L10: Empty or Overlong Summary

**Scenario:** The summary is missing, only whitespace, or longer than the configured limit.

**Expected behavior:** Retry or reject the response. A summary should be concise and based only on the capture.

## EC-L11: Hallucinated Classification

**Scenario:** The model invents context not present in the capture.

**Expected behavior:** Preserve the raw content, flag the classification for review, and avoid treating the invented metadata as verified fact.

## EC-L12: Prompt Injection in Captured Content

**Scenario:** A note or linked page contains instructions such as “ignore previous instructions” or asks the model to reveal secrets.

**Expected behavior:** Treat captured content as untrusted data. The classifier must follow the system schema and must not execute instructions from the content.

## EC-L13: Sensitive Content Sent to Provider

**Scenario:** A capture contains passwords, API keys, health data, financial data, or private documents.

**Expected behavior:** Provide a configurable redaction or local-only mode. Warn users before sending content to an external LLM.

## EC-L14: Non-English or Mixed-Language Capture

**Scenario:** The content uses a language different from the prompt language.

**Expected behavior:** Preserve the original content. Classification should either support the language or mark confidence as uncertain; it must not translate away the source content.

## EC-L15: LLM Model Deprecation

**Scenario:** The configured model is unavailable or renamed.

**Expected behavior:** Fail with a clear configuration message and allow a replacement model without changing stored raw content.

## EC-L16: Duplicate Processing

**Scenario:** A capture is processed while a previous attempt is still running.

**Expected behavior:** Use a processing lock or status check. Avoid writing two wiki notes for the same capture.

## EC-L17: Partial Classification Output

**Scenario:** The process writes a wiki note before all metadata is validated.

**Expected behavior:** Validate the complete response first, then perform one atomic wiki write.

---

# 6. Wiki and Markdown Storage Edge Cases

## EC-W01: Invalid Front Matter

**Scenario:** YAML is malformed, missing delimiters, or has invalid types.

**Expected behavior:** Report the affected note, skip it during indexing or graph generation, and do not crash the entire batch.

## EC-W02: Duplicate Note IDs

**Scenario:** Two wiki files contain the same `id`.

**Expected behavior:** Treat the graph and index as invalid for those IDs, report both file paths, and require conflict resolution before linking them.

## EC-W03: Filename and ID Disagree

**Scenario:** A note filename changes but the front-matter ID remains stable.

**Expected behavior:** Use the front-matter ID as the canonical identity. Links must continue to work.

## EC-W04: Missing Required Metadata

**Scenario:** A note lacks `id`, `title`, `category`, or `summary`.

**Expected behavior:** Mark it invalid for automated processing, preserve it, and report the missing fields.

## EC-W05: Unknown Category Directory

**Scenario:** A note is found outside the four PARA directories or in an unknown directory.

**Expected behavior:** Include it only after validating its front matter, or report it as misplaced. Never infer a category solely from the directory name.

## EC-W06: Broken Wiki Link

**Scenario:** `[[unknown-id]]` references a note that does not exist.

**Expected behavior:** Preserve the text, omit the unresolved graph edge, and report the broken link.

## EC-W07: Self-Link

**Scenario:** A note links to itself.

**Expected behavior:** Ignore or remove the self-edge during graph generation and report it for cleanup.

## EC-W08: Duplicate Wiki Links

**Scenario:** The same target appears more than once in front matter or body content.

**Expected behavior:** Store one graph edge per source-target pair unless repeated links intentionally carry different types or weights.

## EC-W09: Circular Links

**Scenario:** Note A links to B and B links to A.

**Expected behavior:** Treat the relationship as one undirected relationship for visualization unless direction is explicitly needed. Do not recurse indefinitely.

## EC-W10: Manual Link Conflicts With Semantic Link

**Scenario:** Two notes have both a manual and semantic relationship.

**Expected behavior:** Merge the relationship into one edge or store a normalized edge with multiple relationship types. Do not draw confusing duplicate edges by default.

## EC-W11: Markdown Rendering Hazards

**Scenario:** Content contains raw HTML, scripts, malformed Markdown, or very large code blocks.

**Expected behavior:** Sanitize rendered public HTML where appropriate and keep raw content available in a controlled detail view.

## EC-W12: Content Encoding Changes

**Scenario:** A note is edited in a different encoding.

**Expected behavior:** Require UTF-8 for generated files and report decoding failures rather than replacing characters silently.

## EC-W13: Renamed or Deleted Note

**Scenario:** A wiki file is moved or deleted manually.

**Expected behavior:** Rebuild indexes and graph data from the current wiki. Report links pointing to the missing note.

## EC-W14: Note Edited After Embedding

**Scenario:** Content changes after its embedding was generated.

**Expected behavior:** Detect content or metadata changes using a hash and mark the embedding stale.

---

# 7. Embedding and Auto-Linking Edge Cases

## EC-E01: Empty Embedding Text

**Scenario:** A note has no usable title, summary, tags, or content.

**Expected behavior:** Do not generate a meaningless vector. Mark the note as needing content review.

## EC-E02: Embedding Model Unavailable

**Scenario:** The local model cannot load or its files are missing.

**Expected behavior:** Do not create a partial index. Keep existing valid indexes intact and report the unavailable model.

## EC-E03: Model Version Changes

**Scenario:** The embedding model is changed.

**Expected behavior:** Rebuild all embeddings. Never compare vectors produced by incompatible models without an explicit migration strategy.

## EC-E04: Dimension Mismatch

**Scenario:** A new vector has a different dimension from the stored index.

**Expected behavior:** Reject the vector for the current index and require a full rebuild.

## EC-E05: NaN or Infinite Vector Values

**Scenario:** An embedding contains invalid numeric values.

**Expected behavior:** Reject the vector and record an embedding failure. Do not write it into the index.

## EC-E06: Zero-Norm Vector

**Scenario:** A vector has a norm of zero, making cosine similarity undefined.

**Expected behavior:** Treat its similarity as unavailable and do not create automatic links from it.

## EC-E07: Too Few Notes

**Scenario:** There is only one note or no existing comparison note.

**Expected behavior:** Generate the embedding and index entry but create no relationship.

## EC-E08: Similarity Threshold Too Low

**Scenario:** Almost every note links to every other note.

**Expected behavior:** Provide diagnostics such as edge count and average degree. Allow threshold adjustment and rebuild without rewriting raw captures.

## EC-E09: Similarity Threshold Too High

**Scenario:** No notes are linked despite obvious relationships.

**Expected behavior:** Report zero-link statistics and allow threshold tuning. Do not add manual links automatically to compensate.

## EC-E10: Top-K Larger Than Dataset

**Scenario:** `TOP_K` is greater than the number of notes.

**Expected behavior:** Return all available candidates without error.

## EC-E11: Ties in Similarity

**Scenario:** Multiple notes have identical similarity scores.

**Expected behavior:** Use deterministic tie-breaking, such as stable note ID ordering.

## EC-E12: Duplicate or Near-Duplicate Notes

**Scenario:** Several captures contain the same content.

**Expected behavior:** Link or flag them as duplicates, but preserve each raw capture. Avoid allowing duplicates to dominate retrieval results.

## EC-E13: Link Explosion

**Scenario:** A batch creates too many semantic links.

**Expected behavior:** Enforce top-K and threshold limits. Optionally cap maximum degree per note and report discarded candidates.

## EC-E14: One-Way Link Update Failure

**Scenario:** The source note is updated but the target note fails to update.

**Expected behavior:** Use a transactional or repairable linking process. Run a consistency check that restores bidirectional links.

## EC-E15: Stale Index

**Scenario:** Wiki notes changed after the index was built.

**Expected behavior:** Compare stored note hashes with current hashes. Refuse retrieval or warn clearly until the index is rebuilt.

## EC-E16: Corrupt Index Files

**Scenario:** `embeddings.npy` or `index.json` is truncated or unreadable.

**Expected behavior:** Preserve the corrupt files for diagnosis, rebuild to temporary files, validate them, and replace the index atomically.

## EC-E17: Memory Pressure

**Scenario:** The wiki grows beyond the memory available for loading all vectors.

**Expected behavior:** Use batching or a vector database. Do not crash the Streamlit process without a useful message.

---

# 8. Graph Generation and Visualization Edge Cases

## EC-G01: Empty Wiki

**Scenario:** No valid wiki notes exist.

**Expected behavior:** Generate an empty graph with valid `nodes` and `edges` arrays. The UI should show an onboarding or empty-state message.

## EC-G02: One-Node Graph

**Scenario:** The graph contains one note and no edges.

**Expected behavior:** Render the node without requiring a force simulation relationship.

## EC-G03: Disconnected Components

**Scenario:** The graph contains several groups with no relationships between them.

**Expected behavior:** Render all components and optionally show component statistics. Do not hide isolated notes.

## EC-G04: Extremely Dense Graph

**Scenario:** Too many edges make the graph unreadable or slow.

**Expected behavior:** Apply edge filtering, clustering, or a maximum visible edge count while keeping the full graph JSON available.

## EC-G05: Invalid JSON Output

**Scenario:** Graph writing is interrupted or content contains unserializable values.

**Expected behavior:** Validate JSON before replacing the existing graph file. Keep the last known valid graph if rebuilding fails.

## EC-G06: Duplicate Nodes

**Scenario:** Duplicate IDs are discovered during graph construction.

**Expected behavior:** Fail graph validation for the conflicting IDs and report their source files.

## EC-G07: Orphaned Edges

**Scenario:** An edge references a missing source or target node.

**Expected behavior:** Omit the edge from the exported graph and report it as an unresolved relationship.

## EC-G08: Unsafe Tooltip Content

**Scenario:** A note contains HTML or script content that is inserted into a tooltip.

**Expected behavior:** Escape or sanitize tooltip content. Never inject raw note content into browser HTML without protection.

## EC-G09: Very Long Tooltip Content

**Scenario:** A note contains thousands of characters.

**Expected behavior:** Use a bounded preview in hover content and show the full note in a separate detail panel.

## EC-G10: Missing Browser Features

**Scenario:** The deployed browser blocks scripts, iframes, or required visualization behavior.

**Expected behavior:** Show a textual note list fallback and an explanation that interactive rendering is unavailable.

## EC-G11: Graph Library Failure

**Scenario:** The selected graph component fails to load.

**Expected behavior:** Keep the Ask view usable and show the graph data as a table or note list.

## EC-G12: Graph Data and Wiki Drift

**Scenario:** `graph.json` was generated before the latest wiki changes.

**Expected behavior:** Display a stale-data warning or rebuild graph data before rendering.

---

# 9. Retrieval and Q&A Edge Cases

## EC-Q01: Empty Question

**Scenario:** The user submits an empty or whitespace-only question.

**Expected behavior:** Reject it without performing embedding or LLM calls.

## EC-Q02: Very Long Question

**Scenario:** The question exceeds the embedding or LLM context limits.

**Expected behavior:** Reject with a length message or safely summarize locally before retrieval. Preserve the user's original question in the session only as needed.

## EC-Q03: No Relevant Notes

**Scenario:** All retrieved similarities are below the threshold.

**Expected behavior:** Say that the knowledge base does not contain enough relevant information. Do not call synthesis with unrelated context unless explicitly configured.

## EC-Q04: Empty Knowledge Base

**Scenario:** No embeddings or wiki notes exist.

**Expected behavior:** Return an onboarding message rather than an answer based on general model knowledge.

## EC-Q05: Retrieval Index Missing

**Scenario:** Wiki notes exist but the embedding index does not.

**Expected behavior:** Offer or trigger a rebuild in local mode. In public read-only mode, show that search is temporarily unavailable.

## EC-Q06: Retrieval Index Stale

**Scenario:** The index does not include recently changed notes.

**Expected behavior:** Warn clearly and rebuild before answering, or answer only from the known indexed snapshot with a stale-data notice.

## EC-Q07: Question Embedding Failure

**Scenario:** The embedding model fails for the question.

**Expected behavior:** Return a recoverable error. Do not fall back to an ungrounded LLM answer.

## EC-Q08: Context Overflow

**Scenario:** Retrieved notes exceed the LLM context window.

**Expected behavior:** Truncate or rank context according to a documented policy. Prefer complete high-ranked notes over arbitrary character truncation.

## EC-Q09: Duplicate Retrieved Notes

**Scenario:** The same note is retrieved through semantic search and graph-neighbor expansion.

**Expected behavior:** Include it once and retain the strongest relevance score.

## EC-Q10: Conflicting Notes

**Scenario:** Retrieved notes contain contradictory statements.

**Expected behavior:** Ask the LLM to identify the conflict, cite both sources, and avoid presenting one as certain without evidence.

## EC-Q11: Prompt Injection in Retrieved Notes

**Scenario:** A retrieved note contains instructions aimed at controlling the answer model.

**Expected behavior:** Treat all retrieved notes as untrusted reference content. The answer prompt must preserve the system instruction hierarchy.

## EC-Q12: Hallucinated Answer

**Scenario:** The model adds details absent from retrieved notes.

**Expected behavior:** Strengthen the grounded prompt, validate source presence, and flag or reject answers that lack supporting sources.

## EC-Q13: Answer Without Sources

**Scenario:** The provider returns an answer but no source references.

**Expected behavior:** Return the answer only if the application can attach the retrieved sources itself. Otherwise mark the response incomplete.

## EC-Q14: LLM Answer Timeout

**Scenario:** Retrieval succeeds but synthesis times out.

**Expected behavior:** Show retrieved source notes and a retry action. Do not pretend that synthesis completed.

## EC-Q15: Provider Refuses or Filters Content

**Scenario:** The external provider refuses to process a question or note.

**Expected behavior:** Explain that synthesis is unavailable for that request while keeping local retrieval available.

## EC-Q16: Ambiguous Question

**Scenario:** A question has multiple plausible meanings.

**Expected behavior:** Answer only what the retrieved context supports and state the ambiguity, or ask a clarifying question if the interface supports it.

## EC-Q17: Source Note Deleted After Retrieval

**Scenario:** A note disappears between retrieval and display.

**Expected behavior:** Show the source ID and available snapshot metadata. Do not crash while trying to render the source.

## EC-Q18: Cross-Language Question and Notes

**Scenario:** The question and notes use different languages.

**Expected behavior:** Preserve source text and use a multilingual model only if configured. Otherwise report lower confidence or limited support.

## EC-Q19: General Knowledge Leakage

**Scenario:** The model answers from its pretrained knowledge instead of the personal wiki.

**Expected behavior:** Require explicit context-only behavior and return “not found in your notes” when evidence is missing.

## EC-Q20: Repeated Expensive Questions

**Scenario:** A user submits the same question repeatedly.

**Expected behavior:** Optionally cache retrieval and answer results for a bounded period, while ensuring cache invalidation after wiki or index changes.

---

# 10. Streamlit Application Edge Cases

## EC-U01: Missing Graph File at Startup

**Scenario:** `data/graph.json` does not exist.

**Expected behavior:** The app starts and shows a graph rebuild or empty-state message. Ask and capture views should remain available where possible.

## EC-U02: Missing Wiki Directory

**Scenario:** The application is deployed without the wiki data.

**Expected behavior:** Start in setup or empty mode with a clear message. Do not display fake sample data as if it were user knowledge.

## EC-U03: Session State Reset

**Scenario:** Streamlit reruns and loses temporary state.

**Expected behavior:** Do not rely on session state for durable captures, indexes, or graph data. Persist durable results to storage before reporting success.

## EC-U04: Double-Click Submission

**Scenario:** A user clicks Capture or Ask more than once.

**Expected behavior:** Disable or deduplicate active submissions and prevent duplicate writes or duplicate LLM calls.

## EC-U05: Upload Cancelled

**Scenario:** The user opens the uploader but cancels without selecting a file.

**Expected behavior:** Treat it as no input, not as an error requiring a stack trace.

## EC-U06: Upload Size Limit

**Scenario:** The uploaded file exceeds the platform limit.

**Expected behavior:** Show the limit and reject before processing. Do not claim the file was captured.

## EC-U07: Public App Exposes Private Notes

**Scenario:** A public URL serves personal content unintentionally.

**Expected behavior:** Decide explicitly whether the deployment is private, sanitized, or read-only. Use authentication or a curated dataset when personal data must not be public.

## EC-U08: Concurrent Public Users

**Scenario:** Multiple users submit questions or captures simultaneously.

**Expected behavior:** Keep user session state isolated. Protect shared index and file writes with locks or disable public writes.

## EC-U09: Slow First Load

**Scenario:** The embedding model or graph library loads slowly.

**Expected behavior:** Cache expensive read-only resources and show a loading state. Avoid loading the model repeatedly on every rerun.

## EC-U10: Browser Refresh During Processing

**Scenario:** The user refreshes while a classification or indexing task is running.

**Expected behavior:** Durable status records should make the task resumable or clearly report whether it completed. Do not create a second processing job blindly.

## EC-U11: Component Not Supported on Mobile

**Scenario:** The graph is difficult to use on a small screen.

**Expected behavior:** Provide a note list, search, or selected-node detail fallback. Ensure graph controls do not block access to the Ask view.

## EC-U12: Accessibility Failure

**Scenario:** Important information is available only through hover or visual graph interactions.

**Expected behavior:** Provide text alternatives for nodes, sources, statuses, errors, and note content.

## EC-U13: Stale Cached Data

**Scenario:** Streamlit cache returns an old graph or embedding index.

**Expected behavior:** Include data fingerprints or explicit cache invalidation when files change.

---

# 11. Deployment and Persistence Edge Cases

## EC-D01: Ephemeral File System

**Scenario:** The hosting platform resets local files after restart or redeployment.

**Expected behavior:** Treat deployed files as read-only unless durable storage is configured. Document capture persistence accurately.

## EC-D02: Missing Deployment Secret

**Scenario:** The public app is deployed without `GROQ_API_KEY`.

**Expected behavior:** Graph and local data views remain available. Ask and classification show a configuration error rather than crashing the app.

## EC-D03: Dependency Build Failure

**Scenario:** A package with native dependencies fails during cloud deployment.

**Expected behavior:** Pin compatible versions, select a simpler library, or provide a fallback implementation. Keep the deployment log actionable.

## EC-D04: Cold Start Timeout

**Scenario:** Loading the embedding model takes longer than the platform startup limit.

**Expected behavior:** Use caching, a smaller model, prebuilt indexes, or a platform with more suitable resources.

## EC-D05: Public URL Changes

**Scenario:** The deployment URL changes after redeployment.

**Expected behavior:** Keep the README and final deliverables updated with the current public URL.

## EC-D06: Rate Limits Under Public Use

**Scenario:** Public users exhaust LLM or hosting quotas.

**Expected behavior:** Add request limits, basic abuse protection, caching, and clear quota errors. Never expose provider credentials to clients.

## EC-D07: Public Capture Persistence Failure

**Scenario:** A user sees a successful capture but the deployment loses it after restart.

**Expected behavior:** Do not report durable success unless the storage write is durable. In read-only mode, disable public capture or label it as session-only.

## EC-D08: Git-Backed Write Conflict

**Scenario:** Two online captures attempt to commit at the same time.

**Expected behavior:** Serialize writes, retry conflicts safely, and never overwrite unrelated repository changes.

## EC-D09: External Storage Outage

**Scenario:** The database, object store, or Git provider is unavailable.

**Expected behavior:** Allow read-only operation from the last valid snapshot and queue or reject writes with a visible status.

## EC-D10: Secret Leakage in Deployment Logs

**Scenario:** An exception includes environment variables or request headers.

**Expected behavior:** Sanitize exceptions and logs. Review deployment logs before public release.

## EC-D11: Public Dataset Contains Private Source URLs

**Scenario:** Graph nodes expose file paths or private URLs.

**Expected behavior:** Redact or transform sensitive fields before publishing. Keep private metadata separate from public graph metadata.

---

# 12. Batch Processing and Recovery Edge Cases

## EC-B01: Mixed Success Batch

**Scenario:** Some captures classify successfully while others fail.

**Expected behavior:** Complete successful items, mark failures individually, and print a summary with counts and IDs.

## EC-B02: Resume After Failure

**Scenario:** A batch stops halfway through.

**Expected behavior:** Resume only pending or failed items, unless the user explicitly requests a full rebuild.

## EC-B03: Stuck Processing Status

**Scenario:** An item remains `classifying` or `embedding` after a process crash.

**Expected behavior:** Store a start time and worker ID. Allow stale statuses to be reset after a timeout.

## EC-B04: Partial Pipeline Completion

**Scenario:** A wiki note exists but its embedding or graph update failed.

**Expected behavior:** Keep the wiki note, mark its downstream stages stale, and provide a repair command.

## EC-B05: Batch Ordering

**Scenario:** Notes are processed in different orders on different runs.

**Expected behavior:** Use stable sorting by capture ID or timestamp where ordering affects deterministic output.

## EC-B06: Large Batch Memory Use

**Scenario:** Processing many documents exceeds memory.

**Expected behavior:** Process in bounded batches and flush indexes safely. Do not load all raw files or embeddings unnecessarily.

## EC-B07: User Edits During Processing

**Scenario:** A user manually edits a wiki note while the pipeline is updating it.

**Expected behavior:** Detect file modification conflicts and avoid overwriting manual changes. Require a repair or merge step.

## EC-B08: Rebuild During Query

**Scenario:** The embedding index or graph is rebuilt while a user is querying.

**Expected behavior:** Query a consistent snapshot. Replace rebuilt artifacts atomically after validation.

## EC-B09: Backup and Restore

**Scenario:** The project directory is corrupted or restored from an older backup.

**Expected behavior:** Validate IDs, hashes, index compatibility, and graph freshness after restore. Provide rebuild commands for derived artifacts.

---

# 13. Testing Matrix

Every implementation phase should include the following test categories.

| Category | Examples | Expected Result |
|---|---|---|
| Valid input | Normal note, URL, PDF | Successful processing |
| Empty input | Blank note, blank question | Clear validation error |
| Boundary input | Very long note, large file, high `TOP_K` | Bounded and documented behavior |
| Invalid input | Bad URL, malformed YAML, invalid category | Rejected without data loss |
| Failure recovery | Timeout, outage, interrupted write | Retry or resumable failure |
| Duplicate input | Same note, same file, repeated button click | No accidental duplicate work |
| Malicious input | Prompt injection, path traversal, script content | Treated as untrusted and contained |
| Missing dependency | No API key, missing model, missing graph | Limited mode with clear explanation |
| Concurrency | Two writers, rebuild during query | Consistent data and atomic updates |
| Privacy | Private URL, personal document, public deployment | Redacted or access-controlled |

---

# 14. Operational Diagnostics

The system should expose enough metadata to diagnose failures without logging private content.

Recommended diagnostics:

- Capture ID.
- Processing stage.
- Status.
- Started and completed timestamps.
- Error type.
- Safe error message.
- Model name and version.
- Source file checksum where applicable.
- Note content hash.
- Embedding index version.
- Graph generation timestamp.
- Number of nodes and edges.
- Retrieval result count and similarity range.

Recommended batch summary:

```text
Processed: 12
Skipped: 2
Failed: 1
Embeddings rebuilt: 15
Links added: 24
Graph nodes: 15
Graph edges: 24
```

Do not include raw note bodies, API keys, authorization headers, or sensitive file paths in routine logs.

---

# 15. Recovery Commands

The final CLI should provide focused recovery operations similar to:

```bash
# Retry failed classification
python scripts/classify.py retry-failed

# Rebuild all embeddings
python scripts/link.py rebuild

# Check and repair wiki links
python scripts/link.py check-links
python scripts/link.py repair-links

# Rebuild the graph from the wiki
python scripts/build_graph.py

# Validate all project artifacts
python scripts/validate.py

# Reprocess one capture
python scripts/pipeline.py process cap_20260918_7f3a2c
```

Each recovery command should print what it changed and what remains unresolved.

---

# 16. Release Readiness Checklist

## Data and Privacy

- [ ] Raw captures are backed up.
- [ ] Public data has been reviewed for private content.
- [ ] Sensitive URLs and file paths are redacted.
- [ ] No secrets exist in tracked files or graph output.

## Capture

- [ ] Empty, duplicate, oversized, and invalid inputs behave correctly.
- [ ] Note, link, and file captures work.
- [ ] Interrupted writes do not produce false successes.

## AI Processing

- [ ] Malformed LLM output is rejected or repaired safely.
- [ ] Prompt injection content is treated as data.
- [ ] Provider outages leave captures recoverable.
- [ ] Classification is schema-validated.

## Embeddings and Graph

- [ ] Index dimensions and model versions are checked.
- [ ] Stale indexes are detected.
- [ ] Broken links are reported.
- [ ] Empty and dense graphs render safely.
- [ ] Tooltip content is escaped.

## Q&A

- [ ] Empty and unknown questions are handled.
- [ ] Answers include sources.
- [ ] Context limits are enforced.
- [ ] Unsupported answers are not fabricated.

## Application and Deployment

- [ ] Missing files and secrets produce useful UI messages.
- [ ] Public persistence behavior is documented.
- [ ] Concurrent submissions are controlled.
- [ ] The graph has a text fallback.
- [ ] The deployed URL works in a clean browser session.

---

# 17. Definition of Robust Behavior

SecondSelf is robust when:

1. No raw capture is lost because a later AI or deployment step fails.
2. Invalid inputs are rejected before they can corrupt storage.
3. Failed items can be retried without duplicating successful work.
4. Derived files such as embeddings and graph JSON can be rebuilt.
5. Wiki links remain stable when filenames or titles change.
6. Public answers are grounded in retrieved notes and show their sources.
7. Untrusted note content cannot control prompts, paths, HTML, or secrets.
8. The application remains useful in limited mode when external services are unavailable.
9. Personal information is not accidentally exposed by the public deployment.
10. Every failure leaves a clear, actionable diagnostic.
