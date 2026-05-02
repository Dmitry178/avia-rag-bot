# Тесты backend

Набор тестов для `avia-bot-backend`. Разделён на два слоя:

| Слой | Каталог | Что проверяет |
|------|---------|---------------|
| **API** (интеграционные) | `tests/api/` | HTTP-эндпоинты FastAPI через `httpx.AsyncClient` |
| **Unit** (модульные) | `tests/unit/` | Бизнес-логика без HTTP: парсеры, чанкеры, сервисы и т.д. |

Стек: **pytest**, **pytest-asyncio** (режим `auto`), **httpx** (ASGI-транспорт).

## Дерево каталогов

```
tests/
├── README_RU.md          # этот файл
├── paths.py              # общие пути к тестовым данным
├── api/
│   ├── conftest.py       # фикстура client (lifespan + AsyncClient)
│   ├── test_chat.py      # CRUD чатов
│   ├── test_etl.py       # ETL-эндпоинты
│   └── test_health.py    # healthz / readyz
└── unit/
    └── etl/
        └── test_chunker.py   # parser + chunker
```

## Запуск

Из корня репозитория (через Makefile):

```bash
make backend-test          # все тесты
make backend-test-api      # только tests/api/
make backend-test-unit     # только tests/unit/
```

Из каталога `backend/`:

```bash
uv run pytest                    # все
uv run pytest tests/api          # API
uv run pytest tests/unit         # unit
uv run pytest tests/api/test_chat.py -v   # один файл
uv run pytest -k "soft_delete"   # по имени теста
```

Конфигурация pytest — в `pyproject.toml` (`testpaths = ["tests"]`, `asyncio_mode = "auto"`).

## API-тесты (`tests/api/`)

Поднимают полное приложение (`app.main:app`) с инициализацией lifespan (БД, зависимости). Запросы идут через in-process ASGI — отдельный сервер не нужен.

### Общая фикстура

`api/conftest.py` — асинхронная фикстура `client`:

- запускает `lifespan(app)`;
- отдаёт `httpx.AsyncClient` с `ASGITransport`;
- базовый URL: `http://test`.

### Покрытие

| Файл | Эндпоинты | Тесты |
|------|-----------|-------|
| `test_health.py` | `GET /api/healthz`, `GET /api/readyz` | liveness и readiness возвращают `{"status": "ok"}` |
| `test_chat.py` | `POST/GET/DELETE /api/chats` | создание и листинг; детали нового чата с пустыми сообщениями; soft-delete → 404 |
| `test_etl.py` | `GET /api/etl/stats`, `GET /api/etl/manifest` | статистика чанков; manifest без индекса → 404 |

## Unit-тесты (`tests/unit/`)

Вызывают функции и классы напрямую, без HTTP-слоя. Быстрые, не требуют поднятия FastAPI.

### `unit/etl/test_chunker.py`

Проверяет пайплайн разбора RAG-документа (`etl/parser.py`, `etl/chunker.py`) на реальном файле `backend/data/rag-document.md`:

| Тест | Проверка |
|------|----------|
| `test_parse_markdown_finds_all_main_sections` | парсер находит вводный раздел, FAQ и глоссарий |
| `test_chunk_document_produces_expected_types` | чанкер выдаёт SOP, FAQ, GLOSSARY, DECISION_TREE, SCENARIO; ≥ 200 чанков |
| `test_chunks_have_retrieval_prefix` | у каждого чанка есть префиксы `[Раздел:` и `[Тип:` |

## Общие модули

### `paths.py`

Константы путей к тестовым данным:

- `BACKEND_ROOT` — корень `backend/`;
- `RAG_DOCUMENT` — `backend/data/rag-document.md`.

Используйте при добавлении unit-тестов, которым нужны файлы с диска.

## Соглашения

1. **Именование файлов** — `test_<модуль>.py`; функции — `test_<поведение>`.
2. **Docstrings** — на английском, кратко описывают ожидаемое поведение (см. существующие тесты).
3. **API-тесты** — только в `tests/api/`; общие фикстуры — в `tests/api/conftest.py`.
4. **Unit-тесты** — зеркалят структуру кода: `app/services/chat.py` → `tests/unit/services/test_chat.py`, `etl/parser.py` → `tests/unit/etl/test_parser.py`.
5. **Новые API-роутеры** — добавляйте `tests/api/test_<router>.py`, не смешивайте с unit.
6. **Асинхронность** — API-тесты помечайте `@pytest.mark.asyncio` (или полагайтесь на `asyncio_mode = "auto"`).

## Что добавить дальше

По мере развития проекта:

- `tests/unit/services/` — сервисный слой (моки репозиториев);
- `tests/unit/etl/test_parser.py` — отдельные кейсы парсера на синтетическом markdown;
- `tests/api/test_chat_message.py` — отправка сообщений и RAG-ответов, когда появится эндпоинт.

## Маркеры pytest

В `pyproject.toml` зарегистрированы маркеры `api` и `unit` — при необходимости можно помечать тесты и фильтровать:

```bash
uv run pytest -m api
uv run pytest -m unit
```

Сейчас маркеры не проставлены на тестах; разделение по каталогам достаточно для запуска через Makefile.
