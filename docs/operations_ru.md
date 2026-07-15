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
| `make etl-ingest` | Инкрементальный ingest (по умолчанию) |
| `make etl-ingest SOURCE=path/to/doc.md` | Ingest произвольного markdown |
| `make etl-stats` | Количество чанков по `content_type` |
| `make etl-manifest` | Последний manifest индекса |

Docker: `make docker-etl-ingest`.

### API-эквиваленты

| Метод | Путь |
|-------|------|
| `POST` | `/api/etl/ingest` — body: `{ "rebuild": false, "source_path": null }` |
| `GET` | `/api/etl/stats` |
| `GET` | `/api/etl/manifest` |

### Когда перезапускать ingest

| Событие | Действие |
|---------|----------|
| Изменился контент KB | `make etl-ingest` (инкрементально) |
| Сменилась embedding model | `make etl-ingest` с `rebuild=true` |
| Подозрение на рассинхрон FAISS/БД | Остановить backend → бэкап `backend/data/` → полный rebuild |
| Прерванный ingest | Повторить ту же команду — checkpoint продолжит |

### Checkpoint ingest

Файл: `backend/data/ingest_checkpoint.json`. Сохраняется между батчами эмбеддингов. При `Ctrl+C` CLI выводит инструкцию по resume (`exit code 130`).

### Артефакты на диске

| Файл | Назначение |
|------|------------|
| `backend/data/app.db` | SQLite (чанки, чаты, manifest) |
| `backend/data/faiss.index` | FAISS-индекс |
| `backend/data/manifest.json` | Метаданные последней сборки |
| `backend/data/ingest_checkpoint.json` | Состояние resume (временный) |

`id` чанка в SQLite должен совпадать с позицией строки в FAISS — при полном ingest пересобираются вместе.

---

## Резервное копирование

### Что бэкапить

Минимум для восстановления RAG:

```
backend/data/app.db
backend/data/faiss.index
backend/data/manifest.json
backend/data/rag-document.md   # исходная KB
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

**Решение:** `make etl-ingest`. Проверить `backend/data/faiss.index`.

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

**Причина:** `ETL__DOCUMENT_PATH` или `source_path` указывает на несуществующий файл.

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
