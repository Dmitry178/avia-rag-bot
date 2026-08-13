# AI-помощник сотрудника аэропорта

[English](README.md) · **Русский**

**Avia-bot** — демонстрационное чат-приложение для сотрудников аэропорта. **Индексация базы знаний (ETL)** и **RAG** вынесены в отдельный пакет **`mcp-rag`** — [MCP](https://modelcontextprotocol.io)-сервер по stdio (`retrieve`, `ingest_schema`, `stats`, …). FastAPI-backend отвечает за чаты, LLM-guards и SSE-трассировку; к `mcp-rag` он обращается **in-process** (`runtime=embed`, по умолчанию) или через **MCP subprocess** (`runtime=mcp`). Индексация не на HTTP API — `make etl-ingest`, CLI `mcp-rag` или MCP tools.

В UI — диалог, сравнение методов RAG (HyDE, Multi-Query, Query Rewriting, Rerank), трассировка пайплайна. Параллельно режим **только LLM** без базы знаний.

Monorepo: **`backend/`** (FastAPI, чаты) · **`mcp-rag/`** (канонический RAG + ETL, MCP stdio) · **`frontend/`** (React SPA) · **`data/`** (том KB: markdown, `kb.db`, FAISS).

## Что умеет приложение

- **Индексация базы знаний** — `mcp-rag` парсит markdown, чанкует по схеме, строит embeddings и сохраняет в `data/kb.db` + FAISS (не через HTTP backend).
- **Чаты** — создание, выбор, закрытие и удаление диалогов; история сообщений и настройки хранятся на backend.
- **Два режима работы** (переключаются в шапке UI):
  - **LLM** — прямой диалог с языковой моделью без поиска по базе знаний. Панель **Параметры**: история диалога, свой системный промпт (свободный режим без guard).
  - **RAG** — ответы с опорой на проиндексированные документы. Панель **Трассировка**: настройки RAG, снимок настроек для ответа, hits по корпусам (lane) и использованные чанки.
- **Настройки на уровне чата** — RAG/LLM-параметры сохраняются в чате и снимком попадают в metadata каждого сообщения.
- **Тема оформления** — светлая, тёмная или системная (следует настройкам ОС).
- **Язык интерфейса** — русский и английский; выбор сохраняется между сессиями.

## Скриншоты интерфейса

**Режим RAG** — ответ с цитатами и трассировка пайплайна:

![Режим RAG — панель трассировки](images/rag-ru.png)

**Режим LLM** — ассистент по умолчанию и свой системный промпт:

![Режим LLM — настройки по умолчанию](images/llm-1-ru.png)

![Режим LLM — свой системный промпт](images/llm-2-ru.png)

## Стек

| Часть | Технологии |
|-------|------------|
| Backend | Python 3.13, FastAPI, SQLModel, uv |
| **mcp-rag** | RAG-пайплайн, ETL, FAISS, MCP stdio (FastMCP) |
| LLM | OpenAI-compatible API (chat + embeddings) |
| Frontend | React 19, TypeScript, Vite, PrimeReact, TanStack Query, Zustand |
| Данные | `backend/data/app.db` (чаты) + `data/kb.db` + FAISS (KB) |

## Структура проекта

```
avia-bot/
├── backend/                 # FastAPI — чаты, SSE, RAG-адаптеры
│   ├── app/
│   │   ├── api/routers/     # health, chats (без HTTP ETL)
│   │   ├── services/        # ChatService, …
│   │   ├── rag/             # EmbedRagClient, McpRagClient, src_bridge
│   │   ├── llm/             # чат, guards
│   │   └── …
│   ├── data/                # app.db (только чаты)
│   └── tests/
├── mcp-rag/                 # Канонический RAG + ETL + MCP-сервер
│   ├── src/                 # пакет `src` (RagPipeline, ETLService, …)
│   ├── scripts/run_etl.py
│   └── Makefile             # etl-ingest, etl-stats, etl-manifest
├── data/                    # Том KB (git-источники + kb.db, FAISS)
├── frontend/
├── docs/
└── Makefile                 # делегирует etl-* в mcp-rag
```

### Backend (`backend/app/`)

Поток зависимостей: **API → Service → Repository → Model**.  
Реализация RAG/ETL: **`mcp-rag/src/`**; в `backend/app/rag/` — только тонкие адаптеры.

| Каталог | Назначение |
|---------|------------|
| `api/routers/` | HTTP: health, chats (без `/api/etl`) |
| `services/` | Оркестрация чатов, guards, заголовки |
| `rag/` | `EmbedRagClient`, `McpRagClient`, lazy-импорты `src` |
| `llm/` | Вызов LLM, промпты, фильтрация запросов |

### mcp-rag (`mcp-rag/src/`)

| Область | Назначение |
|---------|------------|
| `rag/` | `RagPipeline`, multi-lane retrieval, HyDE / rerank |
| `etl/` | Schema-driven чанкование markdown |
| `services/` | `ETLService`, планирование ingest |
| `mcp/` | MCP tools (`retrieve`, `ingest_*`, `stats`) |

Запуск: `python -m src.server` (stdio). Индексация: `make etl-ingest` или `scripts/run_etl.py`.

### Frontend (`frontend/src/`)

SPA на React + Vite. В dev-режиме запросы к `/api` проксируются на backend (`http://127.0.0.1:8000`).

| Каталог | Назначение |
|---------|------------|
| `features/chats/` | Список чатов, создание, удаление (пустые — без подтверждения) |
| `features/chat/` | Диалог, отправка сообщений, markdown-ответы |
| `features/rag/` | Панель настроек RAG (HyDE, Multi-Query, Query Rewriting, Rerank, история) |
| `features/llm/` | Панель параметров LLM (история, свой системный промпт) |
| `features/trace/` | Трассировка RAG: применённые настройки, запросы, hits по корпусу (lane), чанки в ответе |
| `shared/api/` | HTTP-клиент для `/api/chats/*` |

## Режимы LLM и RAG

Переключатель в шапке задаёт **режим интерфейса** и тип создаваемых чатов. Списки чатов разделены по режиму.

| Режим | Описание | Правая панель |
|-------|----------|---------------|
| **LLM** | Свободный диалог с LLM. База знаний не используется. Guard и авиационный system prompt — по умолчанию; при включённом **своём системном промпте** guard отключается. | **Параметры** |
| **RAG** | Multi-lane поиск по FAISS с разделением по корпусам, опциональные методы retrieval, ответ с контекстом из базы знаний. | **Трассировка** (настройки + trace по ответу) |

При отправке сообщения frontend передаёт на backend актуальные настройки (`rag_config` / `llm_config`, `use_history`). Backend сохраняет их в чате и в `metadata` user/assistant сообщений.

### Настройки RAG

| Параметр | Группа | Описание |
|----------|--------|----------|
| **HyDE** | Query transform (один из трёх) | LLM генерирует гипотетический ответ; поиск по его embedding |
| **Multi-Query** | Query transform | Несколько вариантов запроса → поиск в каждом корпусе → RRF **внутри каждого lane** |
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

### RAG-пайплайн (`mcp-rag/src/rag/`)

```
[HyDE | Multi-Query | Query Rewriting | прямой запрос]
        → параллельные lane (фильтр по content_type):
            SOP гл.01–12 (8) | FAQ (5) | деревья решений (3) | сценарии (3)
        → dedupe → [опциональный Rerank → top_chunks]
        → статические гл.00 + гл.13 в system prompt + контекст из retrieval → LLM (общий ответ)
        → [если совпадение в lane decision_tree ≥ 0.30] отдельная проработка дерева → карточка в UI
```

**Деревья решений (гл. 16):** при достаточно релевантном чанке из lane `decision_tree` запускается **отдельная проработка** (`src/rag/decision_tree.py`). Frontend показывает карточку **«Оперативный алгоритм»** (`metadata.decision_tree_guidance`).

| Lane | Источник | Квота |
|------|----------|-------|
| `sop` | Главы 01–12 | 8 |
| `faq` | Глава 14 + FAQ по главам | 5 |
| `decision_tree` | Глава 16 | 3 |
| `scenario` | Глава 17 | 3 |

Lane выполняются параллельно (`src/rag/retrieval_lanes.py`). Один FAISS-индекс на язык; каждый lane фильтрует по `content_type`. Оркестратор: `RagPipeline` в `src/rag/pipeline.py`. Backend вызывает через `EmbedRagClient` или `McpRagClient`.

Трассировка (SSE + `metadata.rag_trace`): снимок `rag_config`, шаг query transform, `retrieval` с `lanes[]` и объединёнными hits, опциональный `rerank`, опциональные `decision_tree` / `decision_tree_generation`. У каждого чанка — `retrieval_lane` и глава в `section`.

Полная документация: [docs/README_RU.md](docs/README_RU.md). Архитектура: [ARCHITECTURE_RU.md](docs/ARCHITECTURE_RU.md). Продуктовые требования: [PRD_RU.md](docs/PRD_RU.md).

**Требование:** перед использованием RAG нужны построенные индексы (`make etl-ingest`). Без индекса API вернёт `503 rag_index_missing`.

## Защита от промпт-инъекций

Реализована в `backend/app/llm/` для режимов **LLM** (по умолчанию) и **RAG**:

| Уровень | Модуль | Что делает |
|---------|--------|------------|
| Системный промпт | `prompts.py` | Авиационная тематика, отказ от jailbreak, не раскрывать промпт и модель |
| Изоляция сообщений | `prompt_guard.py` | Маркеры `<<USER>>` / `<</USER>>`, санитизация |
| Блокировка до LLM | `ChatService` | Явные паттерны инъекций и оффтопик — без вызова LLM |

**Не применяется**, когда в режиме LLM включён **свой системный промпт** (свободный режим).

Unit-тесты: `backend/tests/unit/llm/test_prompt_guard.py`.  
Полный набор тестов (API + unit): [`backend/tests/README_RU.md`](backend/tests/README_RU.md).

## Тема и язык

Настройки в шапке, **сохраняются в `localStorage`**.

- **Тема:** системная / светлая / тёмная (`theme/themes.json`)
- **Язык:** русский (по умолчанию) / English (`shared/i18n/locales/`)

Справка по методам RAG: `rag-methods.ru.json` / `rag-methods.en.json`.

## ETL

1. **Парсинг** markdown → дерево разделов
2. **Chunking** с учётом типа контента (см. [База знаний](#база-знаний))
3. **Embeddings** через LLM-провайдер
4. **Сохранение** в SQLite + FAISS

```bash
cp backend/.env.example backend/.env   # заполнить LLM__*
make backend-install
make etl-ingest                    # обязательно для RAG (все схемы в data/)
make etl-stats
make etl-manifest
```

Индексация **не** на backend HTTP. Makefile, `mcp-rag/scripts/run_etl.py` или MCP tools. См. [operations_ru.md](docs/operations_ru.md).

**FAISS / AVX:** пакет `faiss-cpu` с PyPI поставляется с generic-сборкой. При старте могут появляться INFO-сообщения об отсутствии модулей AVX512/AVX2; затем FAISS загружает стандартную библиотеку (`Successfully loaded faiss.`). Это нормально, ничего делать не нужно. Шум `faiss.loader` подавлен до уровня WARNING в настройках логирования.

**Прерывание ingest:** `Ctrl+C` во время ingest сохраняет checkpoint после последнего завершённого batch и завершает процесс с кодом 130. Повторный запуск той же цели продолжит с места остановки.

Документы по умолчанию: `data/rag-document-{ru,en}.md`.  
Детали модуля ETL: [`mcp-rag/src/etl/README_RU.md`](mcp-rag/src/etl/README_RU.md).

| Путь | Назначение |
|------|------------|
| `backend/data/app.db` | SQLite: только чаты |
| `data/kb.db` | SQLite: чанки, манифесты |
| `data/faiss-ru.index`, `faiss-en.index` | FAISS-индексы по языкам |
| `data/manifest-ru.json`, `manifest-en.json` | копии манифестов |
| `data/rag-document-{ru,en}.md` | исходный markdown для ETL |

## База знаний

Источники RAG — два markdown-файла по языкам: [`data/rag-document-ru.md`](data/rag-document-ru.md) и [`data/rag-document-en.md`](data/rag-document-en.md). Каждый разбит на пронумерованные главы (H1) и намеренно неоднороден: процедуры, FAQ, деревья решений и сценарии относятся к разным группам глав и чанкуются по разным правилам.

### Группы глав

| Главы | Назначение | Индексируется для RAG |
|-------|------------|------------------------|
| **00** | Описание проекта: назначение, возможности, ограничения, scope, политика использования | **Нет** — попадает в системный промпт RAG |
| **01–12** | Операционные SOP (обслуживание, регистрация, багаж, безопасность и т.д.) | **Да** — чанки `sop` |
| **13** | Out of scope: на что отвечает / не отвечает бот, как отказывать и перенаправлять | **Нет** — попадает в системный промпт RAG |
| **14** | Общий FAQ (пары вопрос/ответ) | **Да** — чанки `faq` |
| **15** | Глоссарий авиационных терминов | **Нет** — отключён в MVP |
| **16** | Деревья решений (пошаговая обработка кейсов) | **Да** — чанки `decision_tree` |
| **17** | Практические сценарии (разобранные примеры) | **Да** — чанки `scenario` |

### Правила чанкования (ETL)

| Контент | Единица чанка | Примечания |
|---------|---------------|------------|
| SOP (гл. 01–12) | Один раздел `##` = один чанк; при > ~800 токенов — split по `###` с контекстом родительского `##` | Хвостовые блоки `**FAQ**` в конце главы **вырезаются** из SOP-текста |
| FAQ (все источники) | Одна пара вопрос/ответ = один чанк | FAQ из гл. 01–12 и гл. 14 объединяются как `faq`; в каждом чанке метаданные `[Источник: <глава>]` |
| Деревья решений (гл. 16) | Одно дерево (`## 16.X. …`) = один чанк | Тело дерева не режется |
| Сценарии (гл. 17) | Один сценарий (`## Сценарий N: …`) = один чанк | Тело сценария сохраняется целиком |
| Глоссарий (гл. 15) | — | Не чанкуется и не векторизуется в MVP |
| Главы 00, 13 | — | Не чанкуются и не векторизуются; см. ниже |

Каждый индексируемый чанк получает prefix для retrieval: `[Раздел: …]`, `[Тип: …]`, для FAQ — также метаданные источника.

### Главы 00 и 13 в системном промпте (MVP)

Главы **00** и **13** — мета-политика, а не операционные знания. Они загружаются из исходного документа при ответе в режиме RAG и добавляются в **системный промпт** (с краткими пояснениями для LLM на английском), минуя FAISS.

На этапе MVP в промпт попадает **полный текст** глав без суммаризации, чтобы scope и правила отказа всегда были доступны. Сжатие текста можно добавить позже.

Реализация: schema-driven выбор статических блоков в `etl/universal_chunker.py` + `app/llm/kb_static_context.py`, затем инъекция в `RagPipeline.build_generation_prompt()`.

### Глоссарий отключён (MVP)

Глава **15** парсится, но **не индексируется**. Терминологические вопросы на данном этапе закрываются через SOP и FAQ. Подключение глоссария (embedding или keyword lookup) — в следующих итерациях.

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
make etl-ingest                    # для режима RAG
make backend-dev                       # http://127.0.0.1:8000

# 2. Frontend (отдельный терминал)
cp frontend/.env.example frontend/.env
make frontend-install
make frontend-dev                      # http://127.0.0.1:5173
```

Откройте `http://127.0.0.1:5173`. Vite проксирует `/api` на backend.

Полный список команд: `make help`.

## Запуск в Docker

Нужны: [Docker](https://docs.docker.com/get-docker/) и Docker Compose v2.

```bash
# 1. Переменные окружения (LLM-ключи и модели)
cp .env.docker.example .env
# отредактируйте LLM__BASE_URL, LLM__API_KEY, LLM__MODEL, LLM__EMBEDDING_MODEL

# 2. Сборка и запуск
make docker-up                       # http://127.0.0.1:8080

# 3. Индексация базы знаний (для RAG; один раз или после смены документа)
make docker-etl-ingest
```

Откройте `http://127.0.0.1:8080`. Nginx отдаёт frontend и проксирует `/api` на backend.  
Чаты — в `backend/data/app.db`; артефакты KB (`kb.db`, FAISS, markdown) — в `data/` в корне репо (bind mount — см. [deployment_ru.md](docs/deployment_ru.md)).

Полезные команды:

```bash
make docker-logs      # логи сервисов
make docker-down      # остановить
make docker-build     # только пересобрать образы
```

Порт UI можно переопределить в `.env`: `FRONTEND_PORT=8080`.

## Текущий статус

**Готово:**
- **mcp-rag:** ETL (инкрементальный ingest, resume по checkpoint), FAISS, multi-lane RAG, MCP stdio tools
- Backend: CRUD чатов, адаптеры embed/MCP RAG, LLM guards, SSE trace
- Frontend: layout (чаты · диалог · трассировка/параметры), настройки RAG/LLM, переключатель runtime (embed/mcp), trace viewer, i18n, theme
- Docker: nginx + backend; чаты в `backend/data/`, KB в `data/`
