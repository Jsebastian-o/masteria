# CAG Estimator

A conversational project estimation tool powered by Claude. Users paste meeting transcripts and attach supporting documents; the LLM produces effort estimates broken down by phase, line item, or narrative — depending on the requested output format.

---

## Overview

CAG Estimator combines a **FastAPI backend** with a **Streamlit chat frontend**. The user opens a session, pastes a requirements transcript, optionally attaches documentation (PDFs, images, text files), and receives a streamed estimation response. The system maintains a sliding-window conversation history so follow-up questions refine the estimate without starting over.

Key capabilities:

- **Streaming estimates** — responses stream token by token via Server-Sent Events so the user sees output immediately.
- **Multi-turn sessions** — each session keeps a windowed history (configurable max turns) and automatically extracts project metadata (name, team size, tech stack, agreed scope) after each turn.
- **File attachments** — PDFs, images, and text documents can be attached alongside any transcript.
- **Prompt versioning** — system and user prompts are Jinja2 templates stored under `app/prompts/`, versioned by folder (`v1`, `v2`, …).

---

## Architecture

```
streamlit_app.py          ←  browser UI (Streamlit)
        │  HTTP (multipart form + streaming)
        ▼
app/routers/sessions.py   ←  session lifecycle & estimation endpoint
app/services/llm_service.py  ←  Anthropic client wrapper (non-session path)
app/services/sessions.py  ←  in-memory SessionStore + ConversationHistory
app/services/metadata_extractor.py  ←  extracts ProjectMetadata from each turn
app/prompts/              ←  Jinja2 prompt templates (estimation/ and session/)
```

The backend exposes two routers under `/api/v1`:

| Endpoint | Purpose |
|---|---|
| `POST /sessions` | Create a new session |
| `POST /sessions/{id}/estimate` | Submit transcript + attachments, stream the response |
| `POST /estimate/stream` | Stateless single-turn estimation (no session) |

---

## Document Handling — Why We Send Files Directly to the LLM

Early in the project we considered a RAG (Retrieval-Augmented Generation) approach: chunk uploaded documents, embed them into a vector store, and retrieve the most relevant passages to inject into the prompt at query time.

**We decided against it and send documents directly to the LLM instead**, using Anthropic's [Files API](https://docs.anthropic.com/en/docs/files). The reasons:

- **Simpler pipeline.** RAG requires an embedding model, a vector database, a retrieval step, and careful chunking logic — all of which add failure modes and operational overhead. Sending the file directly eliminates all of that.
- **No information loss.** Chunking and retrieval can miss relevant context that appears in different parts of the document. Passing the full document ensures the model sees everything.
- **Estimation documents are small.** Requirements specs, call transcripts, and design docs are typically a few pages at most — well within the context window. There is no practical need to pre-filter.
- **Straightforward implementation.** The Files API lets us upload a file once, reference it by ID in the message content, and delete it after the turn. The code is a simple loop — no vector math, no index management.

The trade-off is higher token usage per turn when large documents are attached, but for the document sizes typical in estimation workflows this is acceptable.

## Project Metadata — Why We Update It Incrementally

After each estimation turn the system updates a `ProjectMetadata` object (project name, team size, tech stack, agreed scope) that feeds back into the system prompt for the next turn.

We considered two approaches:

1. **Full re-extraction** — after every turn, send the entire conversation history to the LLM and ask it to re-derive all metadata from scratch.
2. **Incremental merge** — send only the latest exchange (user transcript + assistant response) and ask the LLM to extend the *already-known* facts with anything new it finds.

**We chose the incremental approach** because it is significantly more economical:

- The extraction call is capped at **256 output tokens** and receives only the new exchange, not the full history — keeping input tokens low regardless of how long the conversation grows.
- Re-extracting from the full history would scale linearly with turn count and re-process context the model has already seen.
- Metadata fields are **additive** by design: technologies accumulate across turns, known values are never overwritten with null. This makes incremental merging safe — a single turn does not need to see the whole picture to produce a correct result.
- The call runs **best-effort** (failures are silently swallowed) so a metadata hiccup never interrupts the user-facing stream.

The trade-off is that a late-turn correction (e.g. "actually the team is 4, not 3") may not immediately evict the old value if the LLM returns null for that field. For estimation purposes this is acceptable.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI + Uvicorn |
| LLM | Anthropic Claude (configurable via `LLM_MODEL` env var) |
| Prompt templates | Jinja2 |
| Validation | Pydantic v2 |
| Tests | pytest |

---

## Getting Started

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Set ANTHROPIC_API_KEY and LLM_MODEL in .env
```

### 3. Run

```bash
# Terminal 1 — API server
./run.sh

# Terminal 2 — Streamlit UI
streamlit run streamlit_app.py
```

The UI will be available at `http://localhost:8501` and the API at `http://localhost:8000`.

### 4. Run tests

```bash
./test.sh
```
