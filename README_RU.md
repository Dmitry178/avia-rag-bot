# AI-помощник сотрудника аэропорта

[English](README.md) · **Русский**

Учебный RAG-бот для сотрудников аэропорта: ответы на вопросы по внутренней базе знаний (SOP, FAQ, сценарии, decision trees).  
Monorepo: backend (FastAPI) + web UI (React, в разработке). Telegram и Docker — в планах следующих этапов.

## Стек

| Часть | Технологии |
|-------|------------|
| Backend | Python 3.13, FastAPI, SQLModel, SQLite, FAISS, uv |
| LLM | OpenAI-compatible API (chat + embeddings) |
| Frontend | React, TypeScript, Vite, PrimeReact |
| Данные | SQLite (`chunk_meta`, чаты) + FAISS-индекс на диске |

## Структура проекта

```
avia-bot/
├── backend/          # API и бизнес-логика
│   ├── app/          # FastAPI-приложение (слои api → services → repositories)
│   ├── etl/          # парсер и chunker markdown-документа (без I/O)
│   ├── faiss/        # каталог артефакта векторного индекса (faiss.index)
│   ├── data/         # SQLite, manifest.json, исходный документ
│   └── scripts/      # CLI для ETL
├── frontend/         # web UI — в разработке, пока не в репозитории
├── Makefile          # команды для backend, frontend и ETL
├── README.md
└── README_RU.md
```

### Backend (`backend/app/`)

- **`api/`** — HTTP-роуты (`/api/healthz`, `/api/etl/*`, `/api/chats/*`)
- **`services/`** — use cases (`ETLService`, `ChatService`)
- **`repositories/`** — доступ к SQLite
- **`models/`** — SQLModel-таблицы
- **`llm/`** — клиенты chat completions и embeddings
- **`core/`** — config, logging, `faiss_manager`, `sse_manager`

Поток зависимостей: **API → Service → Repository → Model**.  
Внешние интеграции (LLM, FAISS, SSE) — в `llm/` и `core/`, не в сервисах напрямую.

### Frontend

**Статус: в разработке.** Каталог `frontend/`.

Планируется SPA на React + Vite: прокси `/api` → backend `:8000`, темы (светлая/тёмная), i18n (ru/en), трёхколоночный layout (чаты, диалог, трассировка).

## ETL

Пайплайн индексации базы знаний:

1. **Парсинг** markdown → дерево разделов (`etl/parser.py`)
2. **Chunking** с учётом типа контента (`etl/chunker.py`)
3. **Embeddings** через LLM-провайдер
4. **Сохранение** метаданных в SQLite + векторов в FAISS

Запуск (из корня репозитория):

```bash
cp backend/.env.example backend/.env   # заполнить LLM__*
make backend-install
make etl-ingest                        # полная пересборка индекса
make etl-stats                         # статистика чанков
make etl-manifest                      # последний манифest
```

Тот же пайплайн доступен через API: `POST /api/etl/ingest`, `GET /api/etl/stats`, `GET /api/etl/manifest`.

Исходный документ по умолчанию: `backend/data/rag-document.md` (переменная `ETL__DOCUMENT_PATH`).

Артефакты после ingest:

| Путь | Назначение |
|------|------------|
| `backend/data/app.db` | SQLite: чанки, манифест, чаты |
| `backend/faiss/faiss.index` | FAISS-индекс |
| `backend/data/manifest.json` | копия манифеста для tooling |

## Быстрый старт (dev)

```bash
# Backend
cp backend/.env.example backend/.env
make backend-install
make backend-dev          # http://127.0.0.1:8000
```

Frontend — в разработке.

Полный список команд: `make help`.

## Текущий статус

**Готово (backend, в репозитории):**
- health-check, ETL, индексация, API чатов (синхронный LLM)

**В разработке:**
- web UI (`frontend/`): чаты, диалог, trace-панель

**Запланировано:**
- RAG retrieval, router/guard, streaming, Telegram, Docker
