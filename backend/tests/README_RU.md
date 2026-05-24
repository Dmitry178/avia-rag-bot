# Тесты backend

[English](README.md) · **Русский**

Набор тестов для `avia-bot-backend`. Разделён на два слоя:

| Слой | Каталог | Что проверяет |
|------|---------|---------------|
| **API** (интеграционные) | `tests/api/` | HTTP-эндпоинты FastAPI через `httpx.AsyncClient` |
| **Unit** (модульные) | `tests/unit/` | Бизнес-логика без HTTP: парсеры, чанкеры, RAG-хелперы, сервисы и т.д. |

Стек: **pytest**, **pytest-asyncio** (режим `auto`), **httpx** (ASGI-транспорт).

Сейчас **65 тестов** в обоих слоях.

## Дерево каталогов

```
tests/
├── README.md           # English version
├── README_RU.md        # этот файл
├── conftest.py         # изоляция БД для API-тестов (см. ниже)
├── paths.py            # общие пути к тестовым данным
├── api/
│   ├── conftest.py     # фикстура client (lifespan + AsyncClient)
│   ├── test_chat.py    # CRUD чатов, настройки, сообщения, guards
│   ├── test_etl.py     # ETL-эндпоинты
│   └── test_health.py  # healthz / readyz
└── unit/
    ├── etl/
    │   └── test_chunker.py       # parser + chunker
    ├── llm/
    │   ├── test_prompts.py       # сборка system prompt
    │   └── test_prompt_guard.py  # защита от injection / off-topic
    ├── rag/
    │   └── test_pipeline.py      # RRF, registry query-transform / rerank
    └── services/
        ├── test_etl_plan.py      # планирование инкрементального ingest
        └── test_etl_progress.py   # хелперы прогресса ETL
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

## Изоляция базы данных

Тесты **не используют** dev-базу `data/app.db`. Перед импортом приложения `tests/conftest.py`:

1. задаёт `DB__URL` на отдельный файл `tests/.pytest_app.db`;
2. удаляет его в начале сессии (если остался от прошлого прогона);
3. проверяет, что async engine указывает на этот файл, до запуска тестов;
4. закрывает engine и удаляет файл после завершения всех тестов.

Это касается и API-тестов, и unit-тестов, которые открывают сессию БД (например `tests/unit/services/test_chat_title_service.py`).

Engine создаётся лениво при первом обращении, поэтому `DB__URL` нужно выставить до импорта `app.db.session`. Pytest загружает `tests/conftest.py` первым; ad-hoc скрипты и `python -c` — нет, для них задайте `DB__URL` вручную или запускайте код через pytest.

Это важно: раньше тесты писали в `data/app.db`, и после `make backend-test` / `uv run pytest` в dev-окружении появлялись «лишние» чаты (`Test chat`, `Empty`, `LLM chat` и т.д.).

Файл `tests/.pytest_app.db` добавлен в `.gitignore`.

## API-тесты (`tests/api/`)

Поднимают полное приложение (`app.main:app`) с инициализацией lifespan (создание таблиц, зависимости). Запросы идут через in-process ASGI — отдельный сервер не нужен.

### Общая фикстура

`api/conftest.py` — асинхронная фикстура `client`:

- запускает `lifespan(app)`;
- отдаёт `httpx.AsyncClient` с `ASGITransport`;
- базовый URL: `http://test`.

### Покрытие

| Файл | Эндпоинты | Тесты |
|------|-----------|-------|
| `test_health.py` | `GET /api/healthz`, `GET /api/readyz` | liveness и readiness возвращают `{"status": "ok"}` |
| `test_chat.py` | `POST/GET/PATCH/DELETE /api/chats`, `POST/DELETE /api/chats/{id}/messages` | создание, листинг, фильтр по `chat_type`; `rag_config` / `llm_config` / `use_history` при создании и PATCH; пустые сообщения у нового чата; отправка LLM-сообщения (мок `ChatCompletionClient`) в режиме custom prompt без guards; отправка RAG-сообщения (мок `RagPipeline`) с сохранением metadata, trace и `message_count`; soft-delete чата и сообщения; prompt injection закрывает чат → 409 на follow-up; off-topic блокируется без закрытия |
| `test_etl.py` | `GET /api/etl/stats`, `GET /api/etl/manifest` | статистика чанков; manifest без индекса → 404 |

Тесты сообщений патчат внешний I/O (`ChatCompletionClient.complete`, `RagPipeline`) — LLM и FAISS-индекс не нужны.

## Unit-тесты (`tests/unit/`)

Вызывают функции и классы напрямую, без HTTP-слоя. Быстрые, не требуют поднятия FastAPI.

### `unit/etl/test_chunker.py`

Проверяет пайплайн разбора RAG-документа (`etl/parser.py`, `etl/chunker.py`) на реальном файле `backend/data/rag-document.md`:

| Тест | Проверка |
|------|----------|
| `test_parse_markdown_finds_all_main_sections` | парсер находит вводный раздел, FAQ и глоссарий |
| `test_chunk_document_produces_expected_types` | чанкер выдаёт SOP, FAQ, GLOSSARY, DECISION_TREE, SCENARIO; ≥ 200 чанков |
| `test_chunks_have_retrieval_prefix` | у каждого чанка есть префиксы `[Раздел:` и `[Тип:` |

### `unit/services/test_etl_plan.py`

Планирование инкрементального ingest (`app/services/etl_plan.py`):

| Тест | Проверка |
|------|----------|
| `test_plan_reuses_unchanged_chunks_from_faiss` | неизменённые чанки переиспользуют векторы из FAISS |
| `test_plan_embeds_changed_and_new_chunks` | изменение content-hash запускает переэмбеддинг |
| `test_plan_marks_removed_chunks` | чанки, отсутствующие в источнике, помечаются как removed |
| `test_plan_uses_checkpoint_vectors_before_existing` | checkpoint-векторы приоритетнее FAISS |
| `test_plan_rebuild_embeds_everything` | режим rebuild переиспользует только checkpoint-векторы |

### `unit/services/test_etl_progress.py`

| Тест | Проверка |
|------|----------|
| `test_chunk_progress_context_returns_section_counters` | `_chunk_progress_context` отдаёт имя H1-секции и счётчики прогресса по секции |

### `unit/rag/test_pipeline.py`

| Тест | Проверка |
|------|----------|
| `test_reciprocal_rank_fusion_merges_ranked_lists` | RRF повышает score чанков из нескольких списков |
| `test_resolve_exclusive_query_method_prefers_first_enabled_flag` | активен только один query-transform (HyDE важнее multi-query / rewriting) |
| `test_resolve_rerank_method_when_enabled` | rerank резолвится независимо от query-transform |

### `unit/llm/test_prompts.py`

| Тест | Проверка |
|------|----------|
| `test_build_system_prompt_adds_russian_language_hint` | добавляется подсказка отвечать по-русски |
| `test_build_system_prompt_adds_english_language_hint` | добавляется подсказка отвечать по-английски |
| `test_build_system_prompt_without_language_returns_base` | без `reply_language` подсказка не добавляется |

### `unit/llm/test_prompt_guard.py`

Параметризованные тесты детекции prompt-injection и off-topic (`app/llm/prompt_guard.py`), плюс:

| Тест | Проверка |
|------|----------|
| `test_evaluate_user_message_prioritizes_injection_over_off_topic` | injection проверяется раньше off-topic |
| `test_wrap_user_message_adds_boundaries` | разделители `<<USER>>` / `<</USER>>` |
| `test_harden_messages_for_llm_wraps_only_latest_user_message` | оборачивается только последний user-turn |
| `test_reply_language_for_user_text` | кириллица → `ru`, латиница → `en` |
| `test_blocked_refusal_matches_user_language` | текст отказа совпадает с языком пользователя |

## Общие модули

### `paths.py`

Константы путей к тестовым данным:

- `BACKEND_ROOT` — корень `backend/`;
- `RAG_DOCUMENT` — `backend/data/rag-document.md`.

Используйте при добавлении unit-тестов, которым нужны файлы с диска.

## Соглашения

1. **Именование файлов** — `test_<модуль>.py`; функции — `test_<поведение>`.
2. **Docstrings** — на английском, кратко описывают ожидаемое поведение (см. существующие тесты).
3. **API-тесты** — только в `tests/api/`; HTTP-фикстуры — в `tests/api/conftest.py`; изоляция БД — в корневом `tests/conftest.py`.
4. **Unit-тесты** — зеркалят структуру кода: `app/services/chat.py` → `tests/unit/services/test_chat.py`, `etl/parser.py` → `tests/unit/etl/test_parser.py`.
5. **Новые API-роутеры** — добавляйте `tests/api/test_<router>.py`, не смешивайте с unit.
6. **Асинхронность** — API-тесты помечайте `@pytest.mark.asyncio` (или полагайтесь на `asyncio_mode = "auto"`).
7. **Внешний I/O в API-тестах** — патчите LLM, RAG и FAISS на границе сервиса (`unittest.mock.patch`), чтобы тесты оставались быстрыми и офлайн.

## Что добавить дальше

По мере развития проекта:

- `tests/unit/etl/test_parser.py` — отдельные кейсы парсера на синтетическом markdown;
- `tests/unit/services/test_chat.py` — chat service с моками репозиториев;
- `tests/api/test_rag.py` — отдельные RAG-эндпоинты, когда появятся.

## Маркеры pytest

В `pyproject.toml` зарегистрированы маркеры `api` и `unit` — при необходимости можно помечать тесты и фильтровать:

```bash
uv run pytest -m api
uv run pytest -m unit
```

Сейчас маркеры не проставлены на тестах; разделение по каталогам достаточно для запуска через Makefile.
