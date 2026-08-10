# Knowledge base authoring guide

**English** · [Русский](knowledge_base_ru.md)

How to structure, write, and update the markdown knowledge base for **avia-bot**. Technical parsing details: [backend/etl/README.md](../backend/etl/README.md). **Schema-driven ETL mapping:** [etl_chunking_schema_spec.md](etl_chunking_schema_spec.md).

---

## Source file

| Item | Value |
|------|-------|
| Default paths | `backend/data/rag-document-ru.md`, `backend/data/rag-document-en.md` (see `KB_LANGUAGES` in `config.py`) |
| ETL schema | `backend/data/chunking-schema-{ru,en}.json` — see [etl_chunking_schema_spec.md](etl_chunking_schema_spec.md) |
| After edits | Run `make etl-ingest-all` |

---

## Document structure (chapters)

The parser expects numbered chapters (`## 01. …`, `## 14. …`, etc.).

| Chapters | Role | Indexed in FAISS | Runtime use |
|----------|------|------------------|-------------|
| **00** | Meta-policy, disclaimer | No | Injected into RAG system prompt |
| **01–12** | Operational SOPs | Yes (`sop`) | Vector search |
| **13** | Out-of-scope rules | No | Injected into RAG system prompt |
| **14** | Central FAQ | Yes (`faq`) | Vector search |
| **15** | Glossary | No (disabled in MVP) | — |
| **16** | Decision trees | Yes (`decision_tree`) | Vector search + walkthrough |
| **17** | Scenarios | Yes (`scenario`) | Vector search |

### FAQ extraction

FAQ chunks come from:

1. **Chapter 14** — dedicated FAQ section.
2. **Per-chapter FAQ blocks** at the end of SOP sections (01–12).

Use language-consistent Q/A markers (configured in the ETL chunking schema):

| Language | Question | Answer |
|----------|----------|--------|
| Russian | `**Вопрос:**` | `**Ответ:**` |
| English | `**Question:**` | `**Answer:**` |

Each FAQ chunk includes source metadata (`[Источник: …]` / `[Source: …]`) for trace display.

---

## Content type guidelines

### SOP (chapters 01–12)

- One procedure per logical section.
- Use clear headings (`###` for steps).
- Keep steps actionable ("do X, then Y").
- Add FAQ subsection at chapter end when common questions repeat.

### FAQ

- Question–answer pairs.
- Short, direct answers referencing SOP where needed.
- Avoid duplicate questions across chapters — prefer ch. 14 for cross-cutting FAQ.

### Decision trees (chapter 16)

- Binary or multi-branch structure with explicit conditions.
- Include safety-critical branches and escalation paths.
- When similarity ≥ 0.30 at retrieval, the system triggers a **separate operational walkthrough** — write trees as step-by-step algorithms.

### Scenarios (chapter 17)

- Narrative "what happened → what to do" examples.
- Link to relevant SOP sections conceptually (same terminology).

---

## Writing style

| Do | Avoid |
|----|-------|
| Official, consistent terminology | Contradictory rules across chapters |
| Explicit escalation ("call supervisor") | Vague "use judgment" without criteria |
| Current version dates in chapter headers | Outdated airline-specific codes without context |
| Russian (demo KB language) | Mixed languages in the same chunk without reason |

When authoring **English** KB content, mirror the Russian structure and use English markers defined in [etl_chunking_schema_spec.md](etl_chunking_schema_spec.md).

The UI supports RU/EN interface; KB content language is independent.

---

## Chapters 00 and 13 (static context)

These chapters are **never indexed**. They are loaded at runtime and appended to the RAG system prompt:

- **00** — product principles, advisory nature, liability framing.
- **13** — topics the bot must refuse or redirect (HR, legal, passenger-facing-only, etc.).

Keep them concise but complete — full text is sent on every RAG request (no summarization in MVP).

---

## Update workflow

```mermaid
flowchart LR
    A["Edit rag-document.md"] --> B["Review in git PR"]
    B --> C["make etl-ingest"]
    C --> D["make etl-stats"]
    D --> E["Smoke-test in RAG mode"]
    E --> F["Update golden set if needed"]
```

| Step | Owner | Action |
|------|-------|--------|
| 1 | KB owner | Edit markdown; compliance review for real KB |
| 2 | Developer / CI | Run ingest (incremental by default) |
| 3 | QA | Run [rag_evaluation.md](rag_evaluation.md) golden questions |
| 4 | Ops | Backup `backend/data/` before major rewrites |

### Incremental vs full rebuild

| Change | Command |
|--------|---------|
| Text edits, new sections | `make etl-ingest` |
| Embedding model change | `make etl-ingest` with `rebuild=true` |
| Chunker logic change (code deploy) | Full rebuild after deploy |

---

## Quality checklist (before pilot)

| # | Criterion |
|---|-----------|
| 1 | Every indexed chapter has clear `## NN.` heading |
| 2 | No contradictory procedures between chapters |
| 3 | Out-of-scope topics covered in ch. 13 |
| 4 | Decision trees tested with sample queries |
| 5 | FAQ does not duplicate SOP verbatim (summarize + link conceptually) |
| 6 | Version/date in document header updated |

---

## Related documentation

| Document | Content |
|----------|---------|
| [rag_evaluation.md](rag_evaluation.md) | Quality testing |
| [operations.md](operations.md) | ETL commands |
| [backend/etl/README.md](../backend/etl/README.md) | Parser/chunker rules |
| [etl_chunking_schema_spec.md](etl_chunking_schema_spec.md) | Schema v3 ETL contract |
