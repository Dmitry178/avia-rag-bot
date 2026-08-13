# mcp-rag

[English](README.md) · **Русский**

Канонический пакет RAG + ETL для avia-bot. Backend использует его так:

- **`runtime=embed`** — ленивый in-process импорт `src.rag` (`EmbedRagClient`)
- **`runtime=mcp`** — MCP-сервер по stdio (`McpRagClient`)

## Запуск (stdio)

Из этой директории:

```bash
uv sync
uv run python -m src.server
```

Сервер говорит по MCP через stdin/stdout. Подключайтесь MCP-клиентом (Cursor, backend `McpRagClient` или официальный SDK `mcp`).

## Том данных

Артефакты KB лежат в **`data/`** в корне репозитория:

| Путь | Назначение |
|------|------------|
| `data/kb.db` | `chunk_meta`, `index_manifest` |
| `data/faiss-{lang}.index` | FAISS-векторы |
| `data/rag-document-{lang}.md` | Исходный markdown |
| `data/chunking-schema-{lang}.json` | ETL-схема v3 |

Чаты остаются в `backend/data/app.db` (только backend).

## Индексация

```bash
make etl-ingest          # из корня репозитория
# или
make -C mcp-rag etl-ingest
uv run python scripts/run_etl.py ingest-dir --dir ../data
```

## Переменные окружения

| Переменная | По умолчанию | Назначение |
|------------|--------------|------------|
| `MCP_RAG__SCHEMAS_DIR` | `../data` | Корень тома KB |
| `MCP_RAG__DB__URL` | `sqlite:///./data/kb.db` | SQLite чанков/manifest (в общем env предпочтительнее `MCP_RAG__DB__URL`, а не `DB__URL` backend) |
| `LLM__API_KEY`, `LLM__BASE_URL`, `LLM__MODEL`, `LLM__EMBEDDING_MODEL` | — | LLM / embeddings |

## Проверка импортов

```bash
uv run pytest tests/test_import_smoke.py -v
```

## Инструменты MCP

| Инструмент | Назначение |
|------------|------------|
| `retrieve` | Полный RAG-пайплайн (`RagPipeline.run`) |
| `ingest_schema` | Индексация одного JSON chunking-schema |
| `ingest_directory` | Индексация всех схем в каталоге |
| `ingest_all` | Индексация каталога KB по умолчанию |
| `index_status` | Manifest + наличие файлов FAISS/manifest |
| `stats` | Количество чанков по content type |

Обработчики: `src/mcp/handlers.py`; регистрация: `src/mcp/register.py`.

Полный playbook миграции: `docs/mcp_rag_migration_agent.md` ([русская выжимка](../docs/mcp_rag_migration_agent_ru.md)).
