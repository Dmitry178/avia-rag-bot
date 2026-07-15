# Documentation index

**English** · [Русский](README_RU.md)

Central index for **avia-bot** documentation. For quick start and screenshots see [README.md](../README.md).

## By audience

| Audience | Start here |
|----------|------------|
| **Product / business** | [PRD.md](PRD.md) · [roadmap.md](roadmap.md) · [glossary.md](glossary.md) |
| **Developers** | [ARCHITECTURE.md](ARCHITECTURE.md) · [api.md](api.md) · [frontend.md](frontend.md) |
| **DevOps / SRE** | [deployment.md](deployment.md) · [operations.md](operations.md) · [configuration.md](configuration.md) |
| **Security / compliance** | [security.md](security.md) · [privacy.md](privacy.md) |
| **Knowledge base owners** | [knowledge_base.md](knowledge_base.md) · [rag_evaluation.md](rag_evaluation.md) |
| **QA / RAG tuning** | [rag_evaluation.md](rag_evaluation.md) · [api.md](api.md) (SSE trace) |

## Full catalog

| Document | Description |
|----------|-------------|
| [PRD.md](PRD.md) | Product requirements (business view) |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical architecture, data flows, RAG pipeline |
| [roadmap.md](roadmap.md) | Phases from demo MVP to production |
| [api.md](api.md) | HTTP API reference, error codes, SSE events |
| [configuration.md](configuration.md) | Environment variables and settings |
| [deployment.md](deployment.md) | Local dev and Docker Compose runbook |
| [operations.md](operations.md) | ETL, backups, monitoring, troubleshooting |
| [knowledge_base.md](knowledge_base.md) | Authoring and updating `rag-document.md` |
| [rag_evaluation.md](rag_evaluation.md) | Quality evaluation methodology |
| [security.md](security.md) | Threat model, guards, deployment hardening |
| [privacy.md](privacy.md) | Data handling and compliance notes |
| [frontend.md](frontend.md) | React SPA structure and state management |
| [glossary.md](glossary.md) | Terms used across product and engineering |
| [adr/](adr/) | Architecture Decision Records |

## Package-level docs (outside `docs/`)

| Document | Description |
|----------|-------------|
| [backend/etl/README.md](../backend/etl/README.md) | Parser and chunker internals |
| [backend/tests/README.md](../backend/tests/README.md) | Test layout and commands |

## Naming convention

| Files | Case |
|-------|------|
| `README.md`, `README_RU.md`, `PRD.md`, `PRD_RU.md`, `ARCHITECTURE.md`, `ARCHITECTURE_RU.md` | **UPPERCASE** |
| All other files in `docs/` (e.g. `api.md`, `roadmap.md`, `adr/`) | lowercase |

## Language versions

Most documents exist in **English** and **Russian** (`*_ru.md`). Cross-links at the top of each file point to the alternate language.

## Interactive API docs

When the backend is running, OpenAPI UI is available at:

- `http://127.0.0.1:8000/docs` (local dev)
- `http://localhost:8080/api/docs` (Docker, via Nginx proxy — if exposed)

The [api.md](api.md) document is the stable human-readable contract; generated OpenAPI may include additional schema detail.
