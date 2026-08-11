# ETL Chunking Schema v3 Specification (Draft)

## 1. Purpose

This document defines a universal JSON schema for ETL chunking of markdown knowledge-base documents.

Goals:
- move category mapping and chunking behavior from hardcoded Python logic into JSON;
- preserve current chunking output for existing RU/EN documents (parity mode);
- support reusable CLI execution for other projects with isolated output artifacts;
- keep retrieval lanes and static prompt sources configurable from schema.

Non-goals:
- this schema does not define LLM answer generation logic;
- this schema does not define UI trace rendering;
- this schema does not replace embedding provider configuration.

---

## 2. Scope

Schema controls:
- input document identity and path;
- output artifact routes (chunk metadata, FAISS index, manifest, optional exports);
- categories and category properties;
- section/subsection classification rules;
- chunking strategies and parameters;
- static prompt assembly sources;
- retrieval lanes and lane quotas.

---

## 3. Versioning Model

- `format` — schema identifier and contract version; must be `rag.chunking-schema.v3` for ETL discovery.

Rules:
- breaking JSON contract or chunking semantics requires a new `format` value (for example `rag.chunking-schema.v4`);
- incompatible format requires full reindex;
- ETL directory discovery ignores `*.json` files without the supported `format` value.

---

## 4. Top-Level Structure

Required top-level keys:
- `format`
- `document`
- `io`
- `categories`
- `classification_rules`
- `chunking_policies`
- `category_policy_bindings`
- `static_prompt`
- `retrieval_lanes`

### 4.1 `document`

Required fields:
- `document_id` (string, stable unique id)
- `language_code` (string, e.g. `ru`, `en`)
- `display_name` (string)
- `source_path` (string path to source markdown file, relative to the schema JSON directory unless absolute)

Optional fields:
- `description`
- `owner`

Path resolution:
- `document.source_path` and `io.output_root` are resolved relative to the directory that contains the schema JSON file;
- artifact filenames inside `io` (`faiss_index_path`, `manifest_path`, `chunk_meta.db_path`) are resolved relative to `output_root`.

### 4.2 `io`

Required fields:
- `output_root`
- `chunk_meta` (object with route settings)
- `faiss_index_path`
- `manifest_path`

Optional fields:
- `chunks_export_path`
- `reports_path`

Constraints:
- artifact filenames inside `io` resolve under `output_root`;
- default behavior must prevent silent overwrite of existing production artifacts when `overwrite_policy` is `forbid`.

### 4.3 `categories`

Each category object:
- `id` (stable string id, e.g. `sop`, `faq`, `decision_tree`)
- `description`
- `indexable` (bool)
- `allowed_in_static_prompt` (bool)
- `labels` object for prefix rendering (`section`, `type`, `source`, `context`, `question`, `answer`)

### 4.4 `classification_rules`

Each rule:
- `id`
- `priority` (integer; lower value means higher priority)
- `target_category_id`
- `match` object

`match` supports:
- `section_number_in` (e.g. `["00", "13"]`)
- `title_regex`
- `title_keywords_any`
- `path_regex` (optional advanced matcher)

Rule processing:
- rules are evaluated by ascending priority;
- first matching rule wins;
- if no rule matches, `default_category_id` must be explicitly defined in schema.

### 4.5 `chunking_policies`

Supported `strategy` values:
- `whole_section`
- `by_subheading`
- `qa_pairs`
- `qa_by_heading_prefix`
- `regex_split`
- `token_window`

Common policy fields:
- `id`
- `strategy`
- `params`

`params` by strategy:
- `whole_section`: no required params
- `by_subheading`:
  - `heading_level` (e.g. `2` for `##`, `3` for `###`)
  - `include_parent_context` (bool)
  - `overflow_fallback` (`token_window` or `none`)
- `qa_pairs`:
  - `question_marker`
  - `answer_marker`
- `qa_by_heading_prefix`:
  - `heading_level`
  - `question_prefixes` (for titles like `Question: ...` / `Вопрос: ...`)
  - `question_marker`
  - `answer_marker`
- `regex_split`:
  - `split_regex`
  - `title_capture_group` (default `1`)
- `token_window`:
  - `chunk_size`
  - `overlap`
  - `separators` (optional)

### 4.6 `category_policy_bindings`

Array of bindings:
- `category_id`
- `policy_id`
- optional `extras` (category-specific behavior, e.g. embedded FAQ extraction block)

Each category must have exactly one effective primary policy.

### 4.7 `static_prompt`

Fields:
- `enabled` (bool)
- `blocks` (ordered array)

Each block:
- `id`
- `source` (by category ids and/or section numbers)
- `title`
- `guidance_text`
- `render_template` (optional)

### 4.8 `retrieval_lanes`

Each lane:
- `id`
- `label` — short localized title for trace UI and chunk citations (per schema language file)
- `description` — optional subtitle or tooltip (shown when different from `label`)
- `allowed_category_ids`
- `top_k`
- `oversample`
- `min_fetch`
- `min_similarity` (optional, default `0.4`) — drop lane hits below this vector-similarity threshold before context assembly
- `presentation` (optional) — RAG UI / verification behavior for this lane:
  - `ui_priority` — higher values are processed first for dedicated verification
  - `ui_variant` — frontend styling key (for example `decision_tree`)
  - `exclude_from_generation_context` — when dedicated verification succeeds, remove this lane's categories from the general RAG context
  - `verification_strategy` — `none` or `dedicated_llm`
  - `verification_no_match_token` — codeword for dedicated LLM verification rejections
  - `max_verification_candidates` — cap dedicated verification attempts for this lane

Constraints:
- lane ids must be unique;
- every indexable category should be reachable from at least one lane.

---

## 5. Validation and Invariants

Hard validation:
- unknown keys can be rejected in strict mode;
- all references (`target_category_id`, `policy_id`, `allowed_category_ids`) must resolve;
- conflicting classification rules with same priority and overlapping matcher must fail schema validation;
- `overlap` must be `< chunk_size` for `token_window`;
- paths in `io` must pass safety checks.

Runtime invariants:
- deterministic chunk ordering;
- stable hash generation from rendered chunk content;
- no mixing of output namespaces between runs unless explicitly requested.

---

## 6. Reference Execution Flow

1. Load and validate schema.
2. Resolve source markdown path and output routes.
3. Parse markdown heading tree (`#`, `##`, `###`).
4. Classify sections by `classification_rules`.
5. Apply category-bound chunking policies.
6. Render prefixes/metadata and compute hashes.
7. Build embedding plan and vectors.
8. Persist chunk metadata + FAISS index + manifest to configured `io` paths.
9. Build static prompt blocks and retrieval lane map from schema.

---

## 7. Current Project Baseline (Parity Contract)

For current project, schema-driven mode must replicate existing behavior for:
- `backend/data/rag-document-ru.md`
- `backend/data/rag-document-en.md`

Baseline category mapping:
- `00 -> meta`
- `01..12 -> sop`
- `13 -> out_of_scope`
- `14 -> faq`
- `15 -> glossary`
- `16 -> decision_tree`
- `17 -> scenario`

Baseline chunking behavior:
- `meta`, `out_of_scope`, `glossary` are non-indexed;
- `faq` is split into Q/A pairs;
- `decision_tree` is split by decision tree heading regex;
- `scenario` is split by scenario heading regex;
- `sop` is chunked by `##` block, with optional split by `###` when oversized; embedded FAQ is extracted into FAQ chunks.

Parity acceptance checks:
- identical chunk count per language;
- identical distribution by category;
- identical or approved-equivalent hash set;
- retrieval smoke checks by lane.

---

## 8. Universal CLI Contract

Primary production command:

```bash
uv run --project backend python backend/scripts/run_etl.py ingest-dir --dir data
```

`ingest-dir` behavior:
- scan the given directory for `*.json` files;
- keep only files with `format: "rag.chunking-schema.v3"`;
- validate the supported `format` value;
- ingest each schema sequentially into SQLite (`io.chunk_meta.db_path` under `output_root`) and FAISS (`io.faiss_index_path`).

CLI must also support:
- `ingest-schema --schema <path>` — one schema into app SQLite + FAISS
- `ingest-dir --dir <path>` / `ingest-all` — every supported schema in a directory
- `schema-ingest --schema <path>` — isolated export without app DB writes
- `--source <path>` (optional override)
- `--output-root <path>` (`schema-ingest` only)
- `--run-id <string>` (optional namespace isolation, `schema-ingest`)
- `--no-embed` (`schema-ingest`)
- `--allow-overwrite` (`schema-ingest`)

Required behavior:
- by default, do not overwrite active production FAISS artifacts when `overwrite_policy` is `forbid`;
- write artifacts relative to each schema file directory unless paths are absolute;
- support execution against markdown files from other projects by pointing `--dir` at any schema directory.
- when `run_id` is provided, write artifacts into `output_root/<run_id>/...`;
- if schema contains `io.protected_production_targets.require_explicit_override=true`, reject writes to those paths unless `--allow-overwrite` is passed.

### Interactive mode

If CLI is started without arguments, it must open an interactive prompt and collect inputs via `input()`:

```bash
uv run --project backend python backend/scripts/run_etl.py
```

Prompt flow:
1. Ask for schemas directory (default: `data`).
2. Discover supported schema JSON files and run incremental ingest for each.

For rebuild or other commands, pass CLI arguments explicitly (`ingest-dir --dir ... --rebuild`, `stats`, `manifest`, etc.).

---

## 9. Example: RU Schema Skeleton

```json
{
  "format": "rag.chunking-schema.v3",
  "document": {
    "document_id": "avia-kb-ru",
    "language_code": "ru",
    "display_name": "Russian KB",
    "source_path": "rag-document-ru.md"
  },
  "io": {
    "output_root": ".",
    "chunk_meta": {
      "kind": "sqlite",
      "db_path": "app.db"
    },
    "faiss_index_path": "faiss-ru.index",
    "manifest_path": "manifest-ru.json"
  },
  "categories": [],
  "classification_rules": [],
  "chunking_policies": [],
  "category_policy_bindings": [],
  "static_prompt": {
    "enabled": true,
    "blocks": []
  },
  "retrieval_lanes": []
}
```

## 10. Example: EN Schema Skeleton

```json
{
  "format": "rag.chunking-schema.v3",
  "document": {
    "document_id": "avia-kb-en",
    "language_code": "en",
    "display_name": "English KB",
    "source_path": "rag-document-en.md"
  },
  "io": {
    "output_root": ".",
    "chunk_meta": {
      "kind": "sqlite",
      "db_path": "app.db"
    },
    "faiss_index_path": "faiss-en.index",
    "manifest_path": "manifest-en.json"
  },
  "categories": [],
  "classification_rules": [],
  "chunking_policies": [],
  "category_policy_bindings": [],
  "static_prompt": {
    "enabled": true,
    "blocks": []
  },
  "retrieval_lanes": []
}
```

---

## 11. Deliverables

Mandatory deliverables for migration:
- finalized specification document (this file, promoted from draft);
- `chunking-schema-ru.json` with baseline parity;
- `chunking-schema-en.json` with baseline parity;
- parity test suite (`old-vs-new`);
- migration runbook with cutover and rollback steps;
- universal CLI entrypoint for schema-driven ETL.

## 12. Ready-to-use templates

- Minimal runtime-compatible template: `docs/examples/chunking-schema-template-minimal.json`
- Extended template with additional category and token-window policy: `docs/examples/chunking-schema-template-extended.json`
- External EN-first template (neutral categories + English markers): `docs/examples/chunking-schema-template-external-en.json`
