# Glossary

**English** · [Русский](glossary_ru.md)

Terms used across **avia-bot** product and engineering documentation.

---

## Product

| Term | Definition |
|------|------------|
| **Avia-bot** | AI assistant for airport staff — answers from internal regulations (SOP, FAQ, scenarios). |
| **KB / Knowledge base** | Markdown document (`rag-document.md`) with operational procedures. |
| **SOP** | Standard Operating Procedure — step-by-step official instructions (chapters 01–12). |
| **FAQ** | Frequently asked questions — short Q&A (chapter 14 + per-chapter blocks). |
| **Decision tree** | Branching procedure for non-standard situations (chapter 16). |
| **Scenario** | Narrative example of a situation and response (chapter 17). |
| **Operational procedure card** | UI block showing decision-tree walkthrough above the main RAG answer. |
| **Pilot** | Limited deployment with real KB and measured KPIs (roadmap phase 1). |

---

## Modes

| Term | Definition |
|------|------------|
| **LLM mode** | Direct chat with the language model; no knowledge base retrieval. |
| **RAG mode** | Retrieval-augmented generation — answer grounded in indexed chunks. |
| **Guard** | Prompt injection and off-topic protection layer. |
| **Custom system prompt** | User-defined LLM instructions; disables guards in LLM mode. |

---

## RAG pipeline

| Term | Definition |
|------|------------|
| **Chunk** | Text segment indexed for vector search; stored in SQLite + FAISS row. |
| **Lane** | Retrieval corpus filter (`sop`, `faq`, `decision_tree`, `scenario`) with its own top-K quota. |
| **Content type** | Chunk category matching a lane filter. |
| **HyDE** | Hypothetical Document Embeddings — search using an LLM-generated hypothetical answer. |
| **Multi-Query** | Several query variants searched and fused with RRF per lane. |
| **Query Rewriting** | Rewrite user query using conversation history before search. |
| **Rerank** | LLM scoring of candidates after vector retrieval. |
| **RRF** | Reciprocal Rank Fusion — merge ranked lists from multiple searches. |
| **top_chunks** | Number of chunks passed to the generation LLM (3–21). |
| **Trace** | Step-by-step log of RAG pipeline execution (SSE + message metadata). |
| **Static context** | Chapters 00 and 13 injected into system prompt without FAISS search. |

---

## Data and indexing

| Term | Definition |
|------|------------|
| **ETL** | Extract-transform-load — parse markdown, embed, write SQLite + FAISS. |
| **Ingest** | Run ETL pipeline to build or update the index. |
| **Manifest** | Metadata of latest index build (hash, model, chunk count, timestamp). |
| **FAISS** | Vector index library for similarity search (`IndexFlatIP`). |
| **Incremental ingest** | Re-embed only changed chunks; reuse unchanged vectors. |
| **Rebuild** | Force full re-embed of all chunks. |
| **Checkpoint** | Saved progress during ingest for resume after interrupt. |

---

## Engineering

| Term | Definition |
|------|------------|
| **Monorepo** | Single repository with `backend/` and `frontend/`. |
| **SSE** | Server-Sent Events — sideband channel for trace and async notifications. |
| **client_id** | Frontend-generated UUID correlating SSE subscription and message POST. |
| **Soft delete** | `is_deleted` flag; record hidden from API, not physically removed. |
| **DBManager** | Per-request database access facade for repositories. |

---

## Related documentation

| Document | Content |
|----------|---------|
| [architecture.md](architecture.md) | Technical detail |
| [prd.md](prd.md) | Business personas and scope |
