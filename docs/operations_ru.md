# Руководство по эксплуатации

**Русский** · [English](operations.md)

Эксплуатация **avia-bot**: обслуживание базы знаний, бэкапы, health checks, troubleshooting. Первичное развёртывание — [deployment_ru.md](deployment_ru.md).

---

## Health endpoints

| Endpoint | Назначение | Healthy |
|----------|------------|---------|
| `GET /api/healthz` | Liveness — процесс жив | `200` |
| `GET /api/readyz` | Readiness — БД доступна | `200` при OK БД |

Docker healthcheck backend использует `healthz`.

---

## Операции ETL

### Команды

| Команда | Описание |
|---------|----------|
| `make etl-ingest` | Инкрементальный ingest — все схемы в `backend/data` (по умолчанию `ru` + `en`) |
| `make etl-stats` | Количество чанков по `content_type` (опционально `LANG=ru\|en`) |
| `make etl-manifest` | Последний manifest (опционально `LANG=ru\|en`) |

Свой каталог схем: `ETL_SCHEMAS_DIR=path make etl-ingest` (через `ingest-dir`).

Docker: `make docker-etl-ingest` индексирует все схемы в `backend/data`.

### API-эквиваленты

| Метод | Путь |
|-------|------|
| `POST` | `/api/etl/ingest` — body: `{ "schema_path": "data/chunking-schema-ru.json", "rebuild": false }` |
| `POST` | `/api/etl/ingest-all` — body: `{ "rebuild": false }` |
| `GET` | `/api/etl/stats` — опционально `?language_code=ru` |
| `GET` | `/api/etl/manifest` — `?language_code=ru` |

### Языки базы знаний

Поддерживаемые языки **захардкожены** в `backend/app/core/config.py` (`KB_LANGUAGES`, не в БД):

| Код | Документ | Метка |
|-----|----------|-------|
| `ru` | `backend/data/rag-document-ru.md` | Русский |
| `en` | `backend/data/rag-document-en.md` | English |

В чатах, чанках и manifest используется столбец `language_code` со значениями `ru` или `en`.

### Артефакты на диске

| Файл | Назначение |
|------|------------|
| `backend/data/app.db` | SQLite (чанки, чаты, manifests) |
| `backend/data/faiss-ru.index` | FAISS (русская KB) |
| `backend/data/faiss-en.index` | FAISS (английская KB) |
| `backend/data/manifest-ru.json` | Метаданные последней сборки (ru) |
| `backend/data/manifest-en.json` | Метаданные последней сборки (en) |
| `backend/data/ingest_checkpoint_{lang}.json` | Checkpoint resume (временный; см. ниже) |
| `backend/data/ingest_checkpoint_{lang}.tmp` | Temp при записи checkpoint (временный) |

`id` чанка в SQLite должен совпадать с позицией строки в FAISS **внутри языка** — при полном ingest пересобираются вместе.

### Когда перезапускать ingest

| Событие | Действие |
|---------|----------|
| Изменился контент KB | `make etl-ingest` (инкрементально) |
| Сменилась embedding model | те же цели с `REBUILD=1` |
| Подозрение на рассинхрон FAISS/БД | Остановить backend → бэкап `backend/data/` → полный rebuild |
| Прерванный ingest | Повторить ту же команду — checkpoint продолжит |

### Checkpoint ingest (временные файлы)

Во время embedding ETL сохраняет **состояние для возобновления**, чтобы длинный ingest после сбоя или `Ctrl+C` не пересчитывал уже готовые батчи через API эмбеддингов.

| Файл | Назначение | Срок жизни |
|------|------------|------------|
| `ingest_checkpoint_{lang}.json` | Частичный прогон: `doc_hash`, модель эмбеддингов, `vectors_by_hash` (хеш контента → вектор) | **Временный** — удаляется при успешном ingest |
| `ingest_checkpoint_{lang}.tmp` | Временный файл атомарной записи checkpoint JSON | Удаляется вместе с checkpoint |
| `faiss-{lang}.index.tmp` | Временный файл при записи FAISS | Заменяется при успешном сохранении индекса |

По языкам: `ingest_checkpoint_ru.json`, `ingest_checkpoint_en.json`. Обновляются после каждого батча эмбеддингов.

**При успешном завершении** (`ETLService.ingest_schema`, CLI `ingest-schema` / `ingest-dir`):

1. Сохраняются SQLite + FAISS + manifest.
2. Checkpoint для завершённых языков **удаляется автоматически** (сервис + дополнительная очистка в CLI).

**Если ingest прерван** (код выхода `130`, ошибка API, убит процесс):

- Checkpoint **остаётся на диске** — повторите **ту же** команду (`make etl-ingest` и т.д.); совместимый checkpoint подхватится.
- Не удаляйте checkpoint вручную, если хотите продолжить с места остановки.

Файлы в `backend/data/.gitignore` — в git не коммитятся.

При `Ctrl+C` CLI выводит инструкцию по resume (`exit code 130`).

---

## Резервное копирование

### Что бэкапить

Минимум для восстановления RAG:

```
backend/data/app.db
backend/data/faiss-ru.index
backend/data/faiss-en.index
backend/data/manifest-ru.json
backend/data/manifest-en.json
backend/data/rag-document-ru.md
backend/data/rag-document-en.md
```

### Процедура

1. Остановить backend (или убедиться, что ingest не идёт).
2. Скопировать каталог `backend/data/` с меткой времени.
3. Секреты `.env` хранить отдельно (не в git).

### Восстановление

1. Остановить backend.
2. Заменить `backend/data/` из бэкапа.
3. Проверить совпадение `embedding_model` в manifest с `LLM__EMBEDDING_MODEL`.
4. Запустить backend; выполнить `make etl-stats`.

---

## Логирование

| Настройка | Рекомендация |
|-----------|--------------|
| `LOG__LEVEL=INFO` | Продакшен по умолчанию |
| `LOG__FORMAT=JSON` | Структурированные логи |
| `LOG__LEVEL=DEBUG` | Кратковременная отладка |

Ключевые события: `etl_ingest_*`, `sse_subscribed`, `llm_api_error`, `rag_index_missing`.

---

## Чеклист мониторинга

| Сигнал | Как проверить |
|--------|---------------|
| API жив | `/api/healthz` |
| БД готова | `/api/readyz` |
| Индекс есть | `/api/etl/manifest` или `make etl-manifest` |
| Распределение чанков | `make etl-stats` |
| Связь с LLM | Тестовое сообщение в режиме LLM |
| RAG pipeline | Сообщение в RAG + trace panel |

---

## Troubleshooting

### `503 rag_index_missing`

**Причина:** нет FAISS-индекса или manifest.

**Решение:** `make etl-ingest` (или цель для конкретного языка). Проверить `backend/data/faiss-ru.index` и `faiss-en.index`.

### `503 rag_chunks_missing`

**Причина:** индекс есть, но таблица `chunk_meta` пуста или рассинхронизирована.

**Решение:** полный re-ingest с `rebuild=true`.

### `etl_embedding_mismatch`

**Причина:** `LLM__EMBEDDING_MODEL` не совпадает с manifest.

**Решение:** re-ingest с `rebuild=true` или вернуть модель из manifest.

### `embedding_api_error` / `llm_api_error`

**Причина:** сбой внешнего LLM API, таймаут, неверная конфигурация.

**Решение:** проверить `LLM__BASE_URL`, `LLM__API_KEY`, имена моделей, квоты провайдера.

### `etl_source_not_found`

**Причина:** путь в `KB_LANGUAGES` или `source_path` при ingest указывает на несуществующий файл.

**Решение:** путь относительно `backend/` или абсолютный.

### Медленные ответы RAG

**Причины:** несколько вызовов LLM (HyDE + rerank + decision tree), большой `top_chunks`, медленный провайдер.

**Смягчение:** отключить опциональные методы; уменьшить `top_chunks`; быстрые модели для пилота.

### Trace по SSE не приходит

**Причины:** несовпадение `client_id` между SSE и `POST /messages`; обрыв соединения.

**Решение:** frontend открывает SSE до отправки; тот же `client_id` в body. Проверить `/api/chats/events` в Network.

### Docker: UI грузится, API не работает

**Причины:** backend unhealthy; нет `.env`; CORS (редко при same-origin).

**Решение:** `make docker-logs`; healthcheck; `.env` в корне репо.

---

## Ёмкость (MVP)

| Ресурс | Типичная нагрузка демо |
|--------|------------------------|
| SQLite | Один writer; пилот < 100 одновременных пользователей |
| FAISS | CPU-поиск в процессе; latency растёт с размером индекса |
| SSE | In-memory на процесс; один экземпляр backend |

Масштабирование — [roadmap_ru.md](roadmap_ru.md) и ADR [001](adr/001-sqlite-faiss-on-disk.md).

---

## Связанная документация

| Документ | Содержание |
|----------|------------|
| [knowledge_base_ru.md](knowledge_base_ru.md) | Авторинг KB |
| [configuration_ru.md](configuration_ru.md) | Переменные env |
| [operations_ru.md](operations_ru.md) | Этот документ |
