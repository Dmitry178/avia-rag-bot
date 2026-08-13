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

Канонический код и CLI — в **`mcp-rag/`**. Корневой `Makefile` делегирует в `mcp-rag/Makefile`.

### Команды

| Команда | Описание |
|---------|----------|
| `make etl-ingest` | Инкрементальный ingest — все схемы в `data/` (по умолчанию `ru` + `en`) |
| `make etl-stats` | Количество чанков по `content_type` (опционально `LANG=ru\|en`) |
| `make etl-manifest` | Последний manifest (опционально `LANG=ru\|en`) |

Свой каталог схем: `ETL_SCHEMAS_DIR=path make -C mcp-rag etl-ingest`.

Docker: `make docker-etl-ingest` (нужен mount `data/` — см. [deployment_ru.md](deployment_ru.md)).

### Языки базы знаний

Языки заданы в **`mcp-rag/src/core/config.py`** (`KB_LANGUAGES`):

| Код | Документ | Метка |
|-----|----------|-------|
| `ru` | `data/rag-document-ru.md` | Русский |
| `en` | `data/rag-document-en.md` | English |

В чатах — `language_code` в настройках; чанки/manifest — в `data/kb.db`.

### Артефакты на диске

| Файл | Назначение |
|------|------------|
| `backend/data/app.db` | SQLite — **только чаты** |
| `data/kb.db` | SQLite — `chunk_meta`, `index_manifest` |
| `data/faiss-ru.index` | FAISS (русская KB) |
| `data/faiss-en.index` | FAISS (английская KB) |
| `data/manifest-ru.json` | Метаданные последней сборки (ru) |
| `data/manifest-en.json` | Метаданные последней сборки (en) |
| `data/ingest_checkpoint_{lang}.json` | Checkpoint resume (временный; см. ниже) |
| `data/ingest_checkpoint_{lang}.tmp` | Temp при записи checkpoint (временный) |

`id` чанка в `kb.db` должен совпадать с позицией строки в FAISS **внутри языка** — при полном ingest пересобираются вместе.

### Когда перезапускать ingest

| Событие | Действие |
|---------|----------|
| Изменился контент KB | `make etl-ingest` (инкрементально) |
| Сменилась embedding model | `REBUILD=1 make etl-ingest` |
| Подозрение на рассинхрон FAISS/БД | Остановить сервисы → бэкап `data/` → полный rebuild |
| Прерванный ingest | Повторить ту же команду — checkpoint продолжит |

### Checkpoint ingest (временные файлы)

Во время embedding ETL сохраняет **состояние для возобновления**, чтобы длинный ingest после сбоя или `Ctrl+C` не пересчитывал уже готовые батчи через API эмбеддингов.

| Файл | Назначение | Срок жизни |
|------|------------|------------|
| `ingest_checkpoint_{lang}.json` | Частичный прогон: `doc_hash`, модель эмбеддингов, `vectors_by_hash` (хеш контента → вектор) | **Временный** — удаляется при успешном ingest |
| `ingest_checkpoint_{lang}.tmp` | Временный файл атомарной записи checkpoint JSON | Удаляется вместе с checkpoint |
| `faiss-{lang}.index.tmp` | Временный файл при записи FAISS | Заменяется при успешном сохранении индекса |

По языкам: `ingest_checkpoint_ru.json`, `ingest_checkpoint_en.json`. Обновляются после каждого батча эмбеддингов.

**При успешном завершении** (`ETLService.ingest_schema`, `mcp-rag/scripts/run_etl.py`):

1. Сохраняются SQLite + FAISS + manifest.
2. Checkpoint для завершённых языков **удаляется автоматически** (сервис + дополнительная очистка в CLI).

**Если ingest прерван** (код выхода `130`, ошибка API, убит процесс):

- Checkpoint **остаётся на диске** — повторите **ту же** команду (`make etl-ingest` и т.д.); совместимый checkpoint подхватится.
- Не удаляйте checkpoint вручную, если хотите продолжить с места остановки.

Файлы в `data/.gitignore` — runtime-артефакты не коммитятся.

При `Ctrl+C` CLI выводит инструкцию по resume (`exit code 130`).

---

## Резервное копирование

### Что бэкапить

Минимум для восстановления RAG:

```
data/kb.db
data/faiss-ru.index
data/faiss-en.index
data/manifest-ru.json
data/manifest-en.json
data/rag-document-ru.md
data/rag-document-en.md
```

Для истории чатов также бэкапьте `backend/data/app.db`.

### Процедура

1. Остановить backend (или убедиться, что ingest не идёт).
2. Скопировать `data/` и `backend/data/app.db` с меткой времени.
3. Секреты `.env` хранить отдельно (не в git).

### Восстановление

1. Остановить backend.
2. Заменить `data/` и `backend/data/app.db` из бэкапа.
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
| Индекс есть | `make etl-manifest` |
| Распределение чанков | `make etl-stats` |
| Связь с LLM | Тестовое сообщение в режиме LLM |
| RAG pipeline | Сообщение в RAG + trace panel |

---

## Troubleshooting

### `503 rag_index_missing`

**Причина:** нет FAISS-индекса или manifest.

**Решение:** `make etl-ingest`. Проверить `data/faiss-ru.index` и `data/faiss-en.index`.

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
