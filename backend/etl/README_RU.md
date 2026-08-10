# ETL (Schema-Driven)

[English](README.md) · **Русский**

`backend/etl/` — пакет schema-driven чанкования. Он разбивает markdown-документы в `ChunkDraft` только через JSON schema v3.

Единственный runtime-путь:

1. Загрузка схемы (`chunking_schema.py`)
2. Построение чанков (`universal_chunker.py`)
3. Сохранение/индексация в сервисном слое (`app/services/etl.py` или `app/services/schema_etl.py`)

## Основные файлы

- `chunking_schema.py` — pydantic-модели схемы, загрузчик, резолв путей, валидация связей.
- `universal_chunker.py` — классификация + стратегии чанкования (`whole_section`, `by_subheading`, `qa_pairs`, `qa_by_heading_prefix`, `regex_split`, `token_window`).
- `faq_regex.py` — helper для regex-извлечения FAQ-пар.
- `types.py` — общий ETL-датакласс (`ChunkDraft`).

## Точки входа

- Основной ingest KB: `app/services/etl.py`
- Универсальный schema-ingest для внешних документов: `app/services/schema_etl.py`
- CLI: `backend/scripts/run_etl.py` (`ingest`, `stats`, `manifest`, `schema-ingest`, интерактивный режим без аргументов)

## Схемы и документация

- Runtime-схемы: `backend/data/chunking-schema-ru.json`, `backend/data/chunking-schema-en.json`
- Спецификация: `docs/etl_chunking_schema_spec_ru.md`
- Шаблоны: `docs/examples/chunking-schema-template-*.json`

## Тесты

Запуск unit-тестов ETL из `backend/`:

```bash
uv run pytest tests/unit/etl -v
```
