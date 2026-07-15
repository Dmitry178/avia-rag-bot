# Справочник конфигурации

**Русский** · [English](configuration.md)

Все настройки backend загружаются через **pydantic-settings** из `backend/.env` и переменных окружения. Вложенные ключи разделяются двойным подчёркиванием (`__`).

Пример: `LLM__BASE_URL` → `settings.llm.base_url`.

См. также: [deployment_ru.md](deployment_ru.md), [ARCHITECTURE_RU.md](ARCHITECTURE_RU.md).

---

## Быстрый старт

```bash
cp backend/.env.example backend/.env
# Укажите LLM__BASE_URL, LLM__API_KEY, LLM__MODEL, LLM__EMBEDDING_MODEL
```

Frontend (опционально): `cp frontend/.env.example frontend/.env` — только при переопределении `VITE_API_URL`.

---

## Приложение (`APP__`)

| Переменная | Тип | По умолчанию | Описание |
|------------|-----|--------------|----------|
| `APP__TITLE` | string | `Avia Bot API` | Заголовок OpenAPI |
| `APP__DESCRIPTION` | string | `RAG assistant for airport staff` | Описание OpenAPI |
| `APP__CORS_ORIGINS` | JSON-массив | `["http://localhost:5173"]` | Разрешённые origins браузера |

**Docker:** `docker-compose.yml` переопределяет CORS на `http://localhost:8080`.

---

## Логирование (`LOG__`)

| Переменная | Тип | По умолчанию | Значения |
|------------|-----|--------------|----------|
| `LOG__NAME` | string | `avia-bot-api` | Имя логгера |
| `LOG__LEVEL` | string | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `FATAL`, `CRITICAL` |
| `LOG__FORMAT` | string | `TEXT` | `TEXT`, `JSON` |

В продакшене используйте `LOG__FORMAT=JSON` для агрегации логов.

---

## База данных (`DB__`)

| Переменная | Тип | По умолчанию | Описание |
|------------|-----|--------------|----------|
| `DB__URL` | string | `sqlite:///./data/app.db` | URL SQLAlchemy; пути относительно `backend/` |

SQLite автоматически преобразуется в async (`sqlite+aiosqlite`) при старте.

---

## Каталог данных (`DATA__`)

| Переменная | Тип | По умолчанию | Описание |
|------------|-----|--------------|----------|
| `DATA__DIR` | string | `./data` | Артефакты: SQLite, manifest JSON, checkpoint ingest |

Создаётся при старте, если отсутствует.

---

## FAISS (`FAISS__`)

| Переменная | Тип | По умолчанию | Описание |
|------------|-----|--------------|----------|
| `FAISS__DIR` | string | `./data` | Каталог файла векторного индекса |
| `FAISS__INDEX_FILE` | string | `faiss.index` | Имя файла индекса в `FAISS__DIR` |

---

## ETL (`ETL__`)

| Переменная | Тип | По умолчанию | Описание |
|------------|-----|--------------|----------|
| `ETL__DOCUMENT_PATH` | string | `data/rag-document.md` | Markdown базы знаний (относительно `backend/` или абсолютный) |

Переопределение на ingest: API `source_path` или CLI `--source`.

---

## LLM-провайдер (`LLM__`)

| Переменная | Обязательна | Описание |
|------------|-------------|----------|
| `LLM__BASE_URL` | **Да** (для chat/RAG/ETL) | Базовый URL OpenAI-совместимого API |
| `LLM__API_KEY` | Зависит от провайдера | Bearer-токен; может быть пустым для локальных шлюзов |
| `LLM__MODEL` | **Да** | Модель chat completion (ответы RAG, HyDE, rerank, заголовки) |
| `LLM__SUMMARIZATION_MODEL` | Нет | Зарезервировано; может совпадать с `LLM__MODEL` |
| `LLM__EMBEDDING_MODEL` | **Да** (для ETL/RAG) | Модель эмбеддингов |

**Важно:** смена `LLM__EMBEDDING_MODEL` требует полного re-ingest (`rebuild=true`). Модель фиксируется в manifest; несовпадение даёт `etl_embedding_mismatch`.

---

## Frontend (`VITE_*`)

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `VITE_API_URL` | `""` | Базовый URL API; пусто = относительный `/api` (dev proxy / Docker Nginx) |

---

## Переопределения Docker Compose

`docker-compose.yml` задаёт:

```yaml
DATA__DIR: ./data
DB__URL: sqlite:///./data/app.db
FAISS__DIR: ./data
ETL__DOCUMENT_PATH: data/rag-document.md
APP__CORS_ORIGINS: '["http://localhost:8080","http://127.0.0.1:8080"]'
```

Порт на хосте: `FRONTEND_PORT` (по умолчанию `8080`). Bind-mount: `./backend/data:/app/data`.

---

## Константы RAG (код, не env)

В `backend/app/core/rag_constants.py`; для изменения нужен деплой кода:

| Константа | По умолчанию | Назначение |
|-----------|--------------|------------|
| `RETRIEVAL_TOP_K` | 30 | Oversampling FAISS на поиск |
| `RERANK_TOP_N` | 5 | Кандидаты для LLM rerank |
| `MULTI_QUERY_COUNT` | 3 | Варианты Multi-Query |
| `DEFAULT_TOP_CHUNKS` | 5 | Чанки в контексте генерации |
| `DECISION_TREE_MIN_SIMILARITY` | 0.30 | Порог walkthrough decision tree |

Переопределение на запрос: `rag_config.top_chunks` (3–21) через API/UI.

---

## Связанная документация

| Документ | Содержание |
|----------|------------|
| [deployment_ru.md](deployment_ru.md) | Настройки по окружениям |
| [operations_ru.md](operations_ru.md) | ETL после смены конфигурации |
| [security_ru.md](security_ru.md) | Работа с секретами |
