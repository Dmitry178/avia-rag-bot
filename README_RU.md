# AI-помощник сотрудника аэропорта

[English](README.md) · **Русский**

Учебный проект — RAG-бот для сотрудников аэропорта: ответы на вопросы по внутренней базе знаний (SOP, FAQ, сценарии, decision trees). Интерфейс позволяет вести диалог с ассистентом, управлять списком чатов и (в режиме RAG) наблюдать трассировку пайплайна.

Monorepo: **backend** (FastAPI, индексация, API чатов) + **frontend** (React SPA). Telegram и Docker — в планах следующих этапов.

## Что умеет приложение

- **Индексация базы знаний** — markdown-документ разбивается на чанки, для каждого строятся embeddings и сохраняются в SQLite + FAISS.
- **Чаты** — создание, выбор, закрытие и удаление диалогов; история сообщений хранится на backend.
- **Два режима работы** (переключаются в шапке UI):
  - **LLM** — прямой диалог с языковой моделью без поиска по базе знаний. **Работает сейчас.**
  - **RAG** — ответы с опорой на проиндексированные документы и панель трассировки. **В разработке** (UI готов, backend retrieval ещё не подключён).
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
├── backend/                    # API и бизнес-логика
│   ├── app/                    # FastAPI-приложение
│   │   ├── api/routers/        # HTTP-роуты (health, etl, chats)
│   │   ├── services/           # use cases (ETLService, ChatService)
│   │   ├── repositories/       # доступ к SQLite
│   │   ├── models/             # SQLModel-таблицы
│   │   ├── schemas/            # Pydantic DTO для API
│   │   ├── llm/                # клиенты chat completions и embeddings
│   │   ├── core/               # config, logging, faiss_manager, sse_manager
│   │   ├── db/                 # сессии, DBManager, init
│   │   └── exceptions/         # обработка ошибок
│   ├── etl/                    # парсер и chunker markdown (без I/O)
│   ├── faiss/                  # артефакт векторного индекса (faiss.index)
│   ├── data/                   # SQLite, manifest.json, исходный документ
│   ├── scripts/                # CLI для ETL
│   └── tests/                  # API- и unit-тесты
├── frontend/                   # web UI (React SPA)
│   ├── src/
│   │   ├── app/                # корень приложения, layout, провайдеры
│   │   ├── features/
│   │   │   ├── chats/          # боковая панель списка чатов
│   │   │   ├── chat/           # диалог, composer, режим LLM/RAG
│   │   │   └── trace/          # панель трассировки RAG (заглушка)
│   │   ├── shared/             # API-клиент, i18n, persist, утилиты
│   │   ├── theme/              # светлая/тёмная тема, CSS-переменные
│   │   └── styles/             # глобальные стили
│   ├── index.html
│   ├── vite.config.ts          # dev-прокси /api → backend :8000
│   └── package.json
├── Makefile                    # команды для backend, frontend и ETL
├── README.md
└── README_RU.md
```

### Backend (`backend/app/`)

Поток зависимостей: **API → Service → Repository → Model**.  
Внешние интеграции (LLM, FAISS, SSE) — в `llm/` и `core/`, не в сервисах напрямую.

| Каталог | Назначение |
|---------|------------|
| `api/routers/` | HTTP-роуты: `/api/healthz`, `/api/etl/*`, `/api/chats/*` |
| `services/` | Use cases: `ETLService`, `ChatService` |
| `repositories/` | CRUD и запросы к SQLite |
| `models/` | SQLModel-таблицы (`ChunkMeta`, `Chat`, `ChatMessage`, …) |
| `llm/` | Chat completions и embeddings через OpenAI-compatible API |
| `core/` | Конфиг, логирование, `faiss_manager`, `sse_manager` |

### Frontend (`frontend/src/`)

SPA на React + Vite. В dev-режиме запросы к `/api` проксируются на backend (`http://127.0.0.1:8000`).

| Каталог | Назначение |
|---------|------------|
| `app/` | `AppLayout` — трёхколоночный layout; `AppHeader` — переключатели режима, языка и темы |
| `features/chats/` | Список чатов, создание нового, выбор активного |
| `features/chat/` | Панель диалога, отправка сообщений, markdown-рендер ответов |
| `features/trace/` | Панель трассировки RAG-пайплайна (появляется только в режиме RAG) |
| `shared/api/` | HTTP-клиент и типы для `/api/chats/*` |
| `shared/i18n/` | Переводы `ru` / `en`, хранение выбранного языка |
| `theme/` | Токены цветов (`themes.json`), применение CSS-переменных |

## Режимы LLM и RAG

Переключатель в шапке приложения задаёт **режим интерфейса**. Выбор сохраняется в `localStorage`.

| Режим | Описание | Статус |
|-------|----------|--------|
| **LLM** | Свободный диалог с языковой моделью. Backend отправляет историю чата в chat completions API и возвращает ответ. База знаний не используется. | Работает |
| **RAG** | Вопросы по процедурам аэропорта с поиском релевантных чанков в FAISS, маршрутизацией и guard-проверками. Справа отображается панель **Трассировка** (шаги пайплайна, тайминги). | В разработке |

Сейчас backend всегда отвечает через простой LLM-вызов (`ChatService.send_message`), независимо от выбранного режима в UI. Режим RAG в интерфейсе подготовлен заранее: layout, placeholder трассировки и тексты — готовы к подключению retrieval и SSE.

## Защита от промпт-инъекций

Базовая многоуровневая защита LLM-чата реализована в `backend/app/llm/`:

| Уровень | Модуль | Что делает |
|---------|--------|------------|
| Системный промпт | `prompts.py` | Инструктирует модель считать сообщения пользователя недоверенными данными, отвечать только по авиации, отклонять jailbreak и манипуляции, не раскрывать системный промпт и сведения о базовой модели (имя, версия, провайдер, архитектура), отказывать на оффтопик. |
| Изоляция сообщений | `prompt_guard.py` | Оборачивает каждое пользовательское сообщение в маркеры `USER MESSAGE START` / `USER MESSAGE END` перед вызовом API; удаляет управляющие символы, которыми можно скрыть инъекцию. |
| Блокировка до LLM | `ChatService` + `prompt_guard.py` | Явные паттерны инъекций (EN/RU) — например «игнорируй предыдущие инструкции», «покажи системный промпт», «jailbreak» — отсекаются **без** вызова LLM; возвращается готовый отказ (`blocked_prompt_injection: true` в метаданных ответа). |

Это **базовая** защита, а не абсолютная гарантия: нестандартные формулировки могут дойти до модели, где второй рубеж — усиленный системный промпт. Unit-тесты: `backend/tests/unit/llm/test_prompt_guard.py`.

## Тема и язык

Настройки доступны в шапке и **сохраняются между перезагрузками** (`localStorage` через Zustand persist).

**Тема** (`theme/`):
- **Системная** — следует `prefers-color-scheme` браузера/ОС.
- **Светлая** / **Тёмная** — фиксированная палитра из `themes.json`, CSS-переменные на `:root`.

**Язык интерфейса** (`shared/i18n/`):
- **Русский** (по умолчанию) и **English**.
- Строки в `locales/ru.json` и `locales/en.json`; атрибут `lang` документа обновляется при смене языка.

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
make etl-manifest                      # последний manifest
```

Тот же пайплайн доступен через API: `POST /api/etl/ingest`, `GET /api/etl/stats`, `GET /api/etl/manifest`.

Исходный документ по умолчанию: `backend/data/rag-document.md` (переменная `ETL__DOCUMENT_PATH`).

Подробнее о формате документа и chunking: [`backend/etl/README_RU.md`](backend/etl/README_RU.md).

Артефакты после ingest:

| Путь | Назначение |
|------|------------|
| `backend/data/app.db` | SQLite: чанки, манифест, чаты |
| `backend/faiss/faiss.index` | FAISS-индекс |
| `backend/data/manifest.json` | копия манифеста для tooling |

## Быстрый старт (dev)

Нужны: Python 3.13 + [uv](https://docs.astral.sh/uv/), Node.js 20+.

```bash
# 1. Backend
cp backend/.env.example backend/.env   # указать LLM__BASE_URL, LLM__API_KEY, LLM__MODEL
make backend-install
make backend-dev                       # http://127.0.0.1:8000

# 2. Frontend (отдельный терминал)
cp frontend/.env.example frontend/.env # при необходимости изменить VITE_API_URL
make frontend-install
make frontend-dev                      # http://127.0.0.1:5173
```

Откройте `http://127.0.0.1:5173`. Vite проксирует `/api` на backend.

Опционально — пересобрать индекс перед работой в режиме RAG (когда retrieval будет подключён):

```bash
make etl-ingest
```

Полный список команд: `make help`.

## Текущий статус

**Готово:**
- Backend: health-check, ETL, индексация FAISS, CRUD чатов, синхронный LLM-ответ, базовая защита от промпт-инъекций
- Frontend: layout (чаты · диалог · трассировка), отправка сообщений, markdown-ответы, переключатели LLM/RAG, тема, i18n

**В разработке:**
- RAG retrieval на backend (поиск по FAISS, router/guard, streaming)
- Подключение трассировки к SSE и заполнение панели Trace в UI

**Запланировано:**
- Telegram-бот, Docker, production-сборка
