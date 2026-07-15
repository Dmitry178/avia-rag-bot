# Security

**English** · [Русский](security_ru.md)

Threat model, implemented controls, and deployment hardening for **avia-bot** MVP. For data handling see [privacy.md](privacy.md).

---

## Scope and assumptions

| Aspect | MVP state |
|--------|-----------|
| Deployment | Internal demo / pilot in trusted network |
| Authentication | **Not implemented** — any client can call the API |
| Authorization | No per-user or per-role access control |
| Data classification | Operational procedures (non-passenger PII in demo KB) |
| LLM provider | External OpenAI-compatible API (data leaves the perimeter) |

Treat the current build as a **demonstration system**, not production-ready for open networks.

---

## Threat model

| Threat | Risk | Mitigation (current) | Gap |
|--------|------|----------------------|-----|
| Prompt injection / jailbreak | High | System prompt, delimiters, regex pre-flight guard | Not foolproof; custom LLM prompt disables guards |
| Data exfiltration via LLM | Medium | Scope limits in prompts; aviation-only policy | User text still sent to external API |
| Unauthorized API access | High | None in MVP | Network isolation; add SSO/API keys in pilot |
| KB poisoning | Medium | Controlled ingest path; no user-uploaded docs | No signed content pipeline |
| SSE eavesdropping | Low | Same-origin in prod; HTTPS recommended | No per-event auth |
| SQLite file theft | Medium | Filesystem permissions | Encrypt at rest in production |

---

## Implemented controls

### 1. Prompt injection protection

Active in **LLM** and **RAG** modes unless **custom system prompt** is enabled (`llm_config.use_custom_prompt=true`).

| Layer | Module | Behavior |
|-------|--------|----------|
| System prompt | `app/llm/prompts.py` | Aviation scope; refuse jailbreaks and off-topic requests |
| Message hardening | `app/llm/prompt_guard.py` | `<<USER>>` … `<</USER>>` delimiters; content sanitization |
| Pre-flight block | `ChatService` | Regex patterns for obvious injection / off-topic |

Blocked messages return a polite refusal as assistant text (`metadata.guard_refusal`), not an HTTP error.

### 2. RAG grounding

- Answers in RAG mode use retrieved chunks + static policy chapters (00, 13).
- Trace panel exposes sources for human verification.
- Out-of-scope rules (ch. 13) injected into system prompt.

### 3. Advisory disclaimer

Knowledge base chapter 00 states the bot is a **support tool**, not a replacement for staff judgment.

### 4. Error handling

Structured `error_code` in API responses — no stack traces to clients in production (`LOG__LEVEL` controls server-side detail).

### 5. CORS

`APP__CORS_ORIGINS` restricts browser origins. Does not protect direct API calls (curl, bots).

---

## Secrets management

| Secret | Location | Guidance |
|--------|----------|----------|
| `LLM__API_KEY` | `backend/.env` or root `.env` (Docker) | Never commit; use secret manager in production |

`.env` files are gitignored. Use `.env.example` as template without real values.

---

## Hardening checklist (pilot / production)

| # | Control | Priority |
|---|---------|----------|
| 1 | Deploy behind corporate VPN or SSO gateway | Critical |
| 2 | Use private / on-prem LLM endpoint | High |
| 3 | Enable HTTPS (TLS termination at Nginx/ingress) | Critical |
| 4 | Implement authentication and audit log | Critical |
| 5 | Restrict ETL ingest to admin role | High |
| 6 | `LOG__FORMAT=JSON` + centralized logging | Medium |
| 7 | Filesystem permissions on `backend/data/` | Medium |
| 8 | Rate limiting on `/api/chats/*/messages` | Medium |
| 9 | Regular dependency updates (`uv`, `npm audit`) | Medium |
| 10 | Security review of real KB before pilot | High |

---

## LLM provider considerations

Data sent to the provider on each RAG request may include:

- User question and chat history (if enabled)
- Retrieved knowledge base chunks
- Static policy text (chapters 00, 13)
- Intermediate prompts (HyDE, multi-query, rerank, decision tree)

**Recommendations:**

- Choose providers with DPA / data residency options.
- Avoid pasting passenger PII into queries.
- Prefer on-prem models for regulated environments.

---

## Incident response (minimal)

| Event | Action |
|-------|--------|
| API key leak | Rotate key; review provider usage logs |
| Suspected prompt injection bypass | Capture message + trace; update guard patterns |
| Incorrect safety-critical answer | Escalate to KB owner; disable feature if needed |
| Data breach (DB stolen) | Rotate credentials; assess KB sensitivity |

---

## Related documentation

| Document | Content |
|----------|---------|
| [privacy.md](privacy.md) | Personal data handling |
| [roadmap.md](roadmap.md) | Auth and HA in later phases |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Guard and RAG design |
