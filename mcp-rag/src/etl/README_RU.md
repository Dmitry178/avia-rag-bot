# ETL (Schema-Driven)

[English](README.md) · **Русский**

`mcp-rag/src/etl/` — пакет schema-driven чанкования. Он разбивает markdown-документы в `ChunkDraft` только через JSON schema v3.

Единый runtime-путь:

1. Загрузка схемы (`chunking_schema.py`)
2. Сборка чанков (`universal_chunker.py`)
3. Сохранение/индексация в сервисном слое (`src/services/etl.py` или `src/services/schema_etl.py`)

## Ключевые файлы

- `chunking_schema.py` — pydantic-модели схемы, loader, разрешение путей, валидация ссылок.
- `universal_chunker.py` — классификация + выполнение policy (`whole_section`, `by_subheading`, `qa_pairs`, `qa_by_heading_prefix`, `regex_split`, `token_window`).
- `faq_regex.py` — helper для извлечения FAQ по regex.
- `types.py` — общий ETL dataclass (`ChunkDraft`).

## Точки входа

- Основной ingest KB: `src/services/etl.py`
- Универсальный schema ingest для внешних документов: `src/services/schema_etl.py`
- CLI: `mcp-rag/scripts/run_etl.py` (`ingest-all`, `ingest-dir`, `ingest-schema`, `stats`, `manifest`, `schema-ingest`, интерактивный режим без аргументов)
- Makefile: `make -C mcp-rag etl-ingest` (или `make etl-ingest` из корня репо)

## Схемы и документация

- Runtime-схемы: `data/chunking-schema-ru.json`, `data/chunking-schema-en.json` (корень репо)
- Спецификация: `docs/etl_chunking_schema_spec_ru.md`
- Шаблоны: `docs/examples/chunking-schema-template-*.json`

## Тесты

ETL unit-тесты из `mcp-rag/`:

```bash
uv run pytest tests/unit/etl -v
```
