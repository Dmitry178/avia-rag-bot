# AI-помощник сотрудника аэропорта

[English](README.md) · **Русский**

Учебный проект — RAG-бот для сотрудников аэропорта: ответы на вопросы по внутренней базе знаний (SOP, FAQ, сценарии, decision trees). Интерфейс позволяет вести диалог с ассистентом, управлять списком чатов, настраивать параметры LLM/RAG и (в режиме RAG) наблюдать трассировку пайплайна.

Monorepo: **backend** (FastAPI, индексация, RAG, API чатов) + **frontend** (React SPA). Telegram и Docker — в планах следующих этапов.

## Что умеет приложение

- **Индексация базы знаний** — markdown-документ разбивается на чанки, для каждого строятся embeddings и сохраняются в SQLite + FAISS.
- **Чаты** — создание, выбор, закрытие и удаление диалогов; история сообщений и настройки хранятся на backend.
- **Два режима работы** (переключаются в шапке UI):
  - **LLM** — прямой диалог с языковой моделью без поиска по базе знаний. Панель **Параметры**: история диалога, свой системный промпт (свободный режим без guard).
  - **RAG** — ответы с опорой на проиндексированные документы. Панель **Трассировка**: настройки retrieval и шаги пайплайна.
- **Настройки на уровне чата** — RAG/LLM-параметры сохраняются в чате и снимком попадают в metadata каждого сообщения.
- **Тема оформления** — светлая, тёмная или системная (следует настройкам ОС).
- **Язык интерфейса** — русский и английский; выбор сохраняется между сессиями.

## Стек

| Часть | Технологии |
|-------|------------|
| Backend | Python 3.13, FastAPI, SQLModel, SQLite, FAISS, uv |
| LLM | OpenAI-compatible API (chat + embeddings) |
| Frontend | React 19, TypeScript, Vite, PrimeReact, TanStack Query, Zustand |
| Данные | SQLite (`chunk_meta`, чаты) + FAISS-индекс на диске |

## Структура проекта

```
avia-bot/
├── backend/
│   ├── app/
│   │   ├── api/routers/        # health, etl, chats
│   │   ├── services/           # ETLService, ChatService
│   │   ├── repositories/
│   │   ├── models/
│   │   ├── schemas/            # chat, rag, llm DTO
│   │   ├── rag/                # RAG-пайплайн
│   │   │   ├── pipeline.py
│   │   │   ├── retrieval.py    # FAISS + RRF fusion
│   │   │   └── methods/        # HyDE, Multi-Query, Query Rewriting, Rerank
│   │   ├── llm/                # chat, embeddings, prompts, guard
│   │   ├── core/               # config, faiss_manager, sse_manager
│   │   ├── db/
│   │   └── exceptions/
│   ├── etl/                    # парсер и chunker markdown
│   ├── faiss/                  # faiss.index
│   ├── data/                   # SQLite, manifest, документ
│   ├── scripts/
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/                # layout, провайдеры
│   │   ├── features/
│   │   │   ├── chats/          # список чатов
│   │   │   ├── chat/           # диалог, composer
│   │   │   ├── rag/            # настройки RAG
│   │   │   ├── llm/            # настройки LLM
│   │   │   └── trace/          # панель трассировки (RAG)
│   │   ├── shared/             # API, i18n
│   │   ├── theme/
│   │   └── styles/
│   └── package.json
├── Makefile
├── README.md
└── README_RU.md
```

### Backend (`backend/app/`)

Поток зависимостей: **API → Service → Repository → Model**.  
Внешние интеграции (LLM, FAISS, SSE) — в `llm/`, `core/` и `rag/`.

| Каталог | Назначение |
|---------|------------|
| `api/routers/` | `/api/healthz`, `/api/etl/*`, `/api/chats/*` |
| `services/` | `ETLService`, `ChatService` |
| `rag/` | Модульный RAG: query transform → FAISS → rerank → контекст для LLM |
| `llm/` | Chat completions, embeddings, system prompts, prompt guard |
| `core/` | Конфиг, логирование, `faiss_manager`, `sse_manager` |

### Frontend (`frontend/src/`)

SPA на React + Vite. В dev-режиме запросы к `/api` проксируются на backend (`http://127.0.0.1:8000`).

| Каталог | Назначение |
|---------|------------|
| `features/chats/` | Список чатов, создание, удаление (пустые — без подтверждения) |
| `features/chat/` | Диалог, отправка сообщений, markdown-ответы |
| `features/rag/` | Панель настроек RAG (HyDE, Multi-Query, Query Rewriting, Rerank, история) |
| `features/llm/` | Панель параметров LLM (история, свой системный промпт) |
| `features/trace/` | Трассировка RAG-пайплайна (режим RAG) |
| `shared/api/` | HTTP-клиент для `/api/chats/*` |

## Режимы LLM и RAG

Переключатель в шапке задаёт **режим интерфейса** и тип создаваемых чатов. Списки чатов разделены по режиму.

| Режим | Описание | Правая панель |
|-------|----------|---------------|
| **LLM** | Свободный диалог с LLM. База знаний не используется. Guard и авиационный system prompt — по умолчанию; при включённом **своём системном промпте** guard отключается. | **Параметры** |
| **RAG** | Поиск по FAISS, опциональные методы retrieval, ответ с контекстом из базы знаний. | **Трассировка** (настройки + шаги пайплайна) |

При отправке сообщения frontend передаёт на backend актуальные настройки (`rag_config` / `llm_config`, `use_history`). Backend сохраняет их в чате и в `metadata` user/assistant сообщений.

### Настройки RAG

| Параметр | Группа | Описание |
|----------|--------|----------|
| **HyDE** | Query transform (один из трёх) | LLM генерирует гипотетический ответ; поиск по его embedding |
| **Multi-Query** | Query transform | Несколько вариантов запроса → поиск по каждому → fusion (RRF) |
| **Query Rewriting** | Query transform | Переписывание запроса с учётом истории диалога |
| **Rerank** | Независимо | LLM-реранжирование top-кандидатов после vector search |
| **Использовать историю** | Общее | Влияет на LLM-контекст и query rewriting |

HyDE, Multi-Query и Query Rewriting **взаимоисключающие** (в UI может быть включён только один). **Rerank** можно совмещать с любым из них.

Если query transform не выбран — прямой vector search по вопросу пользователя.

### Настройки LLM

| Параметр | Описание |
|----------|----------|
| **Использовать историю** | Передавать ли предыдущие сообщения в LLM (по умолчанию включено) |
| **Свой системный промпт** | Кастомный system prompt; guard отключается. Пустой промпт = без system prompt |

### RAG-пайплайн (backend)

```
[HyDE | Multi-Query | Query Rewriting | прямой запрос]
        → embed → FAISS search (top-30)
        → [optional Rerank → top-5]
        → контекст в system prompt → LLM → ответ
```

Классы методов: `backend/app/rag/methods/` (`HyDEQueryMethod`, `MultiQueryMethod`, `QueryRewritingMethod`, `LlmRerankMethod`). Оркестратор: `RagPipeline` в `rag/pipeline.py`.

Шаги трассировки публикуются через SSE (`GET /api/chats/events?client_id=…`, event `trace`) и сохраняются в `metadata.rag_trace` ответа ассистента.

**Требование:** перед использованием RAG нужен построенный индекс (`make etl-ingest`). Без индекса API вернёт `503 rag_index_missing`.

## Защита от промпт-инъекций

Реализована в `backend/app/llm/` для режимов **LLM** (по умолчанию) и **RAG**:

| Уровень | Модуль | Что делает |
|---------|--------|------------|
| Системный промпт | `prompts.py` | Авиационная тематика, отказ от jailbreak, не раскрывать промпт и модель |
| Изоляция сообщений | `prompt_guard.py` | Маркеры `<<USER>>` / `<</USER>>`, санитизация |
| Блокировка до LLM | `ChatService` | Явные паттерны инъекций и оффтопик — без вызова LLM |

**Не применяется**, когда в режиме LLM включён **свой системный промпт** (свободный режим).

Unit-тесты: `backend/tests/unit/llm/test_prompt_guard.py`.

## Тема и язык

Настройки в шапке, **сохраняются в `localStorage`**.

- **Тема:** системная / светлая / тёмная (`theme/themes.json`)
- **Язык:** русский (по умолчанию) / English (`shared/i18n/locales/`)

Справка по методам RAG: `rag-methods.ru.json` / `rag-methods.en.json`.

## ETL

1. **Парсинг** markdown → дерево разделов
2. **Chunking** с учётом типа контента
3. **Embeddings** через LLM-провайдер
4. **Сохранение** в SQLite + FAISS

```bash
cp backend/.env.example backend/.env   # заполнить LLM__*
make backend-install
make etl-ingest                        # обязательно для RAG
make etl-stats
make etl-manifest
```

API: `POST /api/etl/ingest`, `GET /api/etl/stats`, `GET /api/etl/manifest`.

Документ по умолчанию: `backend/data/rag-document.md` (`ETL__DOCUMENT_PATH`).  
Подробнее: [`backend/etl/README_RU.md`](backend/etl/README_RU.md).

| Путь | Назначение |
|------|------------|
| `backend/data/app.db` | SQLite: чанки, манифест, чаты |
| `backend/faiss/faiss.index` | FAISS-индекс |
| `backend/data/manifest.json` | копия манифеста |

## API чатов (кратко)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/chats?chat_type=rag\|llm` | Список чатов |
| POST | `/api/chats` | Создать чат (с начальными настройками) |
| PATCH | `/api/chats/{id}` | Обновить `rag_config` / `llm_config` / `use_history` |
| POST | `/api/chats/{id}/messages` | Отправить сообщение (+ настройки в body) |
| GET | `/api/chats/events?client_id=…` | SSE: ошибки и trace |

## Быстрый старт (dev)

Нужны: Python 3.13 + [uv](https://docs.astral.sh/uv/), Node.js 20+.

```bash
# 1. Backend
cp backend/.env.example backend/.env
# LLM__BASE_URL, LLM__API_KEY, LLM__MODEL, LLM__EMBEDDING_MODEL
make backend-install
make etl-ingest                        # для режима RAG
make backend-dev                       # http://127.0.0.1:8000

# 2. Frontend (отдельный терминал)
cp frontend/.env.example frontend/.env
make frontend-install
make frontend-dev                      # http://127.0.0.1:5173
```

Откройте `http://127.0.0.1:5173`. Vite проксирует `/api` на backend.

Полный список команд: `make help`.

## Текущий статус

**Готово:**
- Backend: ETL, FAISS, модульный RAG-пайплайн, CRUD чатов, LLM/RAG ответы, настройки в чате и metadata, SSE trace events
- Frontend: layout (чаты · диалог · трассировка/параметры), настройки RAG/LLM, отправка настроек с сообщением, i18n, тема

**В разработке:**
- Подписка frontend на SSE trace stream (шаги сейчас в metadata; панель Trace — placeholder до подключения EventSource)
- Streaming ответов

**Запланировано:**
- Telegram-бот, Docker, production-сборка
