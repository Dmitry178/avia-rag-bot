# Справочник конфигурации

**Русский** · [English](configuration.md)

Backend: **pydantic-settings** из `backend/.env` (`app/core/config.py`).  
KB / индексация: **`mcp-rag/.env`** (`mcp-rag/src/core/config.py`).  
Вложенные ключи через `__` (например `LLM__BASE_URL`).

См. также: [deployment_ru.md](deployment_ru.md), [ARCHITECTURE_RU.md](ARCHITECTURE_RU.md).

---

## Быстрый старт

```bash
cp backend/.env.example backend/.env
cp backend/.env mcp-rag/.env
make etl-ingest    # data/kb.db + FAISS в data/ (корень репо)
```

---

## Тома данных (после этапа 9)

| Том | Владелец | Содержимое |
|-----|----------|------------|
| **`data/`** (корень репо) | **mcp-rag** | Исходники KB, `kb.db`, FAISS, manifest, checkpoint ingest |
| **`backend/data/`** | **backend** | Только **`app.db`** — чаты |

Оба runtime читают KB из **`data/`**:

```
embed  →  backend/data/app.db  +  data/kb.db  +  data/faiss-*
mcp    →                        data/kb.db  +  data/faiss-*
```

---

## Backend: `APP__`, `LOG__`, `DB__`

| `DB__URL` | По умолчанию | Описание |
|-----------|--------------|----------|
| | `sqlite:///./data/app.db` | Только чаты; путь относительно `backend/` |

KB-таблиц в этом файле нет.

---

## LLM (`LLM__`) — backend и mcp-rag

Одинаковые переменные в `backend/.env` и `mcp-rag/.env`: `BASE_URL`, `API_KEY`, `MODEL`, `EMBEDDING_MODEL`.

Смена `LLM__EMBEDDING_MODEL` → полный re-ingest (`REBUILD=1`).

---

## Языки KB (код)

**`mcp-rag/src/core/config.py`** → `KB_LANGUAGES` (пути от **корня репо**):

| Код | Документ | Схема |
|-----|----------|-------|
| `ru` | `data/rag-document-ru.md` | `data/chunking-schema-ru.json` |
| `en` | `data/rag-document-en.md` | `data/chunking-schema-en.json` |

Переопределение markdown: CLI `--source` у `ingest-schema`. HTTP `/api/etl/*` на backend **удалён**.

## Docker Compose

Два mount в Compose:

| Хост | Контейнер | Назначение |
|------|-----------|------------|
| `./backend/data` | `/app/data` | Чаты (`app.db`) |
| `./data` | `/data` | KB (`kb.db`, FAISS, markdown, схемы) |

В образ backend входит `mcp-rag` (`/mcp-rag`). Не задавайте один `DB__URL` в Compose для обоих пакетов.

Ingest в контейнере: `make docker-etl-ingest`. См. [deployment_ru.md](deployment_ru.md).

---

## mcp-rag / `kb.db`

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `MCP_RAG__SCHEMAS_DIR` | `../data` | Том KB (от cwd `mcp-rag/`) |
| `MCP_RAG__LANGUAGE` | `en` | Язык по умолчанию |
| `MCP_RAG__DB__URL` | `sqlite:///./data/kb.db` | → `data/kb.db` в корне репо |

MCP JSON в UI: `python -m src.server`, `cwd: ../mcp-rag`.

---

## Embed

Опциональный extra **`rag`** ставит **`mcp-rag`** (`uv sync --extra rag`). Dev-группа включает `mcp-rag` по умолчанию. `runtime=embed` импортирует `src.rag` (lazy); без пакета — **503** `rag_embed_not_installed`.

---

## Индексация

| Команда | Описание |
|---------|----------|
| `make etl-ingest` | Делегирует в `mcp-rag/Makefile` |
| MCP tools | `ingest_schema`, `ingest_all`, `stats`, `index_status` |

---

## Parity-тесты

```bash
cd backend && uv run pytest tests/parity --run-parity -v
```

Один том `data/`; сравнение embed vs MCP stdio. Нужны ingest + `LLM__*`.

---

## Константы RAG

В **`mcp-rag/src/core/rag_constants.py`** (см. [configuration.md](configuration.md)).

---

## Связанная документация

| Документ | Содержание |
|----------|------------|
| [operations_ru.md](operations_ru.md) | ETL, бэкапы |
| [ARCHITECTURE_RU.md](ARCHITECTURE_RU.md) | Архитектура |
