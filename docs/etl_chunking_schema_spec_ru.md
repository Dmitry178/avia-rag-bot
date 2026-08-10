# Спецификация ETL Chunking Schema v3 (Черновик)

## 1. Назначение

Документ описывает универсальную JSON-схему для ETL-чанкования markdown-документов базы знаний.

Цели:
- вынести маппинг категорий и правила чанкования из захардкоженного Python-кода в JSON;
- сохранить parity для текущих RU/EN документов (результат должен совпадать с текущим ETL);
- поддержать универсальный CLI-запуск для внешних проектов с изолированными выходными артефактами;
- сделать конфигурируемыми static prompt источники и retrieval lanes.

Вне scope:
- логика генерации финального ответа LLM;
- UI-представление RAG trace;
- конфигурация embedding-провайдера.

---

## 2. Область действия схемы

Схема управляет:
- идентификацией входного документа и путями к нему;
- маршрутами выходных артефактов (chunk meta, FAISS, manifest, optional exports);
- категориями контента и их свойствами;
- правилами классификации глав/подглав;
- стратегиями чанкования и их параметрами;
- источниками static prompt;
- retrieval lanes и квотами выборки.

---

## 3. Версионирование

- `format` — идентификатор схемы и версия контракта; для discovery должен быть `rag.chunking-schema.v3`.

Правила:
- breaking-изменения JSON-контракта или семантики чанкования требуют нового значения `format` (например `rag.chunking-schema.v4`);
- несовместимый `format` требует full reindex;
- при сканировании директории игнорируются `*.json` без поддерживаемого `format`.

---

## 4. Структура schema v3 (верхний уровень)

Обязательные ключи:
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

Обязательные поля:
- `document_id` (стабильный id документа)
- `language_code` (`ru`, `en`, ...)
- `display_name`
- `source_path` (путь к входному markdown, относительно каталога JSON-схемы, если не абсолютный)

### 4.2 `io`

Обязательные поля:
- `output_root`
- `chunk_meta`
- `faiss_index_path`
- `manifest_path`

Ограничения:
- относительные пути резолвятся внутри `output_root`;
- по умолчанию запрещена «тихая» перезапись production-артефактов.

### 4.3 `categories`

Категория содержит:
- `id`
- `description`
- `indexable`
- `allowed_in_static_prompt`
- `labels` (`section`, `type`, `source`, `context`, `question`, `answer`)

### 4.4 `classification_rules`

Правило содержит:
- `id`
- `priority` (меньше число -> выше приоритет)
- `target_category_id`
- `match`

Поддерживаемые матчеры:
- `section_number_in`
- `title_regex`
- `title_keywords_any`
- `path_regex` (расширенный случай)

Обработка:
- правила проверяются по возрастанию `priority`;
- побеждает первое совпадение;
- если совпадений нет, должен быть явный `default_category_id`.

### 4.5 `chunking_policies`

Поддерживаемые `strategy`:
- `whole_section`
- `by_subheading`
- `qa_pairs`
- `qa_by_heading_prefix`
- `regex_split`
- `token_window`

Параметры:
- `by_subheading`: `heading_level`, `include_parent_context`, `overflow_fallback`
- `qa_pairs`: `question_marker`, `answer_marker`
- `qa_by_heading_prefix`: `heading_level`, `question_prefixes`, `question_marker`, `answer_marker`
- `regex_split`: `split_regex`, `title_capture_group`
- `token_window`: `chunk_size`, `overlap`, `separators`

### 4.6 `category_policy_bindings`

Связка:
- `category_id`
- `policy_id`
- `extras` (например, блок embedded FAQ)

Каждая категория должна иметь ровно одну эффективную основную policy.

### 4.7 `static_prompt`

Поля:
- `enabled`
- `blocks` (упорядоченный список)

Блок:
- `id`
- `source` (категории и/или номера секций)
- `title`
- `guidance_text`
- `render_template` (опционально)

### 4.8 `retrieval_lanes`

Lane содержит:
- `id`
- `description`
- `allowed_category_ids`
- `top_k`
- `oversample`
- `min_fetch`
- `min_similarity` (опционально, по умолчанию `0.4`) — отсечение lane-хитов ниже порога vector similarity
- `presentation` (опционально) — RAG-поведение lane:
  - `ui_priority` — чем выше, тем раньше lane обрабатывается для dedicated verification
  - `ui_variant` — ключ для UI-стиля (например `decision_tree`)
  - `exclude_from_generation_context` — при успешной dedicated verification убрать категории lane из общего RAG-контекста
  - `verification_strategy` — `none` или `dedicated_llm`
  - `verification_no_match_token` — кодовое слово отказа dedicated LLM verification
  - `max_verification_candidates` — лимит кандидатов на dedicated verification для lane

---

## 5. Валидация и инварианты

Строгая валидация:
- все ссылки должны резолвиться (`category_id`, `policy_id`, `allowed_category_ids`);
- конфликтующие правила классификации должны приводить к ошибке;
- для `token_window`: `overlap < chunk_size`;
- `io` пути должны проходить safety-check.

Runtime-инварианты:
- детерминированный порядок чанков;
- стабильное хеширование контента;
- отсутствие смешивания output namespace между запусками по умолчанию.

---

## 6. Эталонный порядок исполнения

1. Загрузить и валидировать schema.
2. Разрешить входной путь и output маршруты.
3. Построить дерево заголовков markdown (`#`, `##`, `###`).
4. Классифицировать секции по `classification_rules`.
5. Применить category-bound `chunking_policies`.
6. Отрендерить префиксы, собрать метаданные, вычислить hash.
7. Подготовить embedding plan и вектора.
8. Сохранить chunk meta + FAISS + manifest в пути из `io`.
9. Построить static prompt и retrieval lanes из schema.

---

## 7. Baseline parity для текущего проекта

Входы:
- `backend/data/rag-document-ru.md`
- `backend/data/rag-document-en.md`

Категоризация глав:
- `00 -> meta`
- `01..12 -> sop`
- `13 -> out_of_scope`
- `14 -> faq`
- `15 -> glossary`
- `16 -> decision_tree`
- `17 -> scenario`

Фактическое чанкование baseline:
- `meta`, `out_of_scope`, `glossary` не индексируются;
- `faq` режется на пары вопрос/ответ;
- `decision_tree` режется по regex заголовков деревьев;
- `scenario` режется по regex заголовков сценариев;
- `sop` формируется по `##`-блокам, а при переполнении режется по `###`; embedded FAQ выделяется в FAQ-чанки.

Проверки parity:
- совпадает `chunk_count` по языкам;
- совпадает распределение по категориям;
- совпадает (или согласованно эквивалентен) набор hash;
- retrieval smoke checks по lane.

---

## 8. Контракт универсального CLI

Основная production-команда:

```bash
uv run --project backend python backend/scripts/run_etl.py ingest-dir --dir data
```

`ingest-dir`:
- сканирует каталог на `*.json`;
- оставляет только файлы с `format: "rag.chunking-schema.v3"`;
- проверяет поддерживаемое значение `format`;
- для каждой схемы пишет SQLite (`io.chunk_meta.db_path` под `output_root`) и FAISS.

Дополнительные аргументы:
- `--schema <path>` (`schema-ingest`, без записи в app DB)
- `--source <path>` (опциональный override)
- `--output-root <path>`
- `--run-id <string>` (опционально)
- `--no-embed`
- `--allow-overwrite`
- legacy `--lang <code>` (`ingest`, одна схема из KB config)

Обязательное поведение:
- не перезаписывать production FAISS по умолчанию при `overwrite_policy: forbid`;
- разрешать пути относительно каталога JSON-схемы;
- работать с markdown из внешних проектов через `--dir`.
- при наличии `run_id` писать артефакты в `output_root/<run_id>/...`;
- если в схеме задано `io.protected_production_targets.require_explicit_override=true`, блокировать запись в эти пути без флага `--allow-overwrite`.

### Интерактивный режим

Если CLI запускается без аргументов, должен запускаться интерактивный сценарий на `input()`:

```bash
uv run --project backend python backend/scripts/run_etl.py
```

Сценарий опроса:
1. Запрос каталога со схемами (по умолчанию: `data`).
2. Автопоиск `*.json` с `format: rag.chunking-schema.v3` и инкрементальный ingest для каждой схемы.

Для `--rebuild` и других команд используйте явные аргументы CLI.

---

## 9. Обязательные результаты миграции

- финализированная спецификация schema v3;
- `chunking-schema-ru.json` с parity к текущему baseline;
- `chunking-schema-en.json` с parity к текущему baseline;
- parity test suite (`old-vs-new`);
- migration runbook (cutover + rollback);
- универсальная CLI-точка входа schema-driven ETL.

## 10. Готовые шаблоны

- Минимальный runtime-совместимый шаблон: `docs/examples/chunking-schema-template-minimal.json`
- Расширенный шаблон с дополнительной категорией и token-window policy: `docs/examples/chunking-schema-template-extended.json`
- EN-first шаблон для внешних проектов (нейтральные категории + английские маркеры): `docs/examples/chunking-schema-template-external-en.json`
