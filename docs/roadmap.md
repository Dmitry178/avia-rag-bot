# Product roadmap

**English** · [Русский](roadmap_ru.md)

Phased plan from demonstration MVP to production deployment. Business context: [PRD.md](PRD.md) §13–16.

**Last updated:** July 2026

---

## Phase 0 — Demo (current)

**Goal:** Prove RAG viability and compare retrieval methods for stakeholders.

| Area | Status |
|------|--------|
| Multi-lane RAG (SOP, FAQ, decision trees, scenarios) | Done |
| Query transforms (HyDE, Multi-Query, Rewriting) + Rerank | Done |
| Pipeline trace (SSE + UI) | Done |
| LLM-only mode + guards | Done |
| ETL incremental ingest + checkpoint | Done |
| Docker Compose deployment | Done |
| Educational KB (~6800 lines) | Done |
| Authentication | Not started |

**Exit criteria:** stakeholder demo completed; RAG config chosen for pilot test set.

---

## Phase 1 — Pilot

**Goal:** Measurable KPIs with real airport KB on a limited user group (20–50 staff).

| Workstream | Deliverables |
|------------|--------------|
| **Knowledge base** | Real SOP/FAQ for one service area; KB owner process |
| **Quality** | Golden set ≥ 50 questions; [rag_evaluation.md](rag_evaluation.md) baseline |
| **Security** | SSO or API gateway auth; basic audit log |
| **Compliance** | DPO/legal sign-off; [privacy.md](privacy.md) policy |
| **Operations** | Backup schedule; ingest runbook for KB updates |
| **Metrics** | Time-to-answer, escalation rate, user satisfaction |

**Go/No-Go criteria** (from PRD):

1. Real KB loaded for at least one operational area
2. Test set passed with compliance review
3. Authentication and audit implemented
4. Data handling policy agreed
5. KB owner and update process defined
6. Production RAG configuration selected from A/B results
7. Training plan for pilot group

---

## Phase 2 — Expansion

**Goal:** Scale across airport services.

| Feature | Description |
|---------|-------------|
| Full KB coverage | All frontline services |
| Glossary (ch. 15) | Re-enable indexing if needed |
| Role-based access | Different sections per role (check-in vs security) |
| Feedback loop | Incorrect-answer reports → KB tickets |
| Analytics dashboard | Usage, top queries, retrieval quality |
| PostgreSQL | Replace SQLite for concurrency |
| External vector DB | Optional — if FAISS limits hit |

---

## Phase 3 — Channels

**Goal:** Access at the counter and in the field.

| Channel | Notes |
|---------|-------|
| Mobile-friendly web | Responsive UI improvements |
| Integrations | Flight ops systems (evaluate scope per airport) |

---

## Phase 4 — Production operations

**Goal:** SLA-backed production service.

| Capability | Target |
|------------|--------|
| High availability | Multiple backend replicas |
| Shared SSE / events | Redis pub/sub |
| Monitoring | Prometheus metrics, alerting |
| KB versioning | Git-backed docs + signed releases |
| CI/CD | Automated test + ingest on KB PRs |
| Token streaming | SSE or WebSocket for LLM output |

---

## Technical debt register

| Item | Phase | ADR |
|------|-------|-----|
| SQLite single-writer | 2 | [001](adr/001-sqlite-faiss-on-disk.md) |
| Single FAISS index, lane filter at query time | 2 | [002](adr/002-multi-lane-single-index.md) |
| Synchronous POST + sideband SSE | 4 | [003](adr/003-sse-sideband-not-streaming.md) |
| In-memory SSE manager | 4 | [003](adr/003-sse-sideband-not-streaming.md) |
| No auth on API | 1 | — |

---

## Open business questions

1. Corporate web only, or also mobile browser for frontline staff?
2. Cloud vs on-prem LLM?
3. Feedback ownership and KB SLA?
4. Role-based KB sections?
5. Flight status integration in v1?
6. Pilot KPIs (2–3 critical metrics)?
7. Tone: official regulation vs friendly assistant?

---

## Related documentation

| Document | Content |
|----------|---------|
| [PRD.md](PRD.md) | Full product requirements |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Current technical design |
| [adr/](adr/) | Architecture decisions |
