# Индекс документации

**Русский** · [English](README.md)

Центральный указатель документации **avia-bot**. Быстрый старт и скриншоты — в [README_RU.md](../README_RU.md).

## По аудитории

| Аудитория | С чего начать |
|-----------|---------------|
| **Продукт / бизнес** | [PRD_RU.md](PRD_RU.md) · [roadmap_ru.md](roadmap_ru.md) · [glossary_ru.md](glossary_ru.md) |
| **Разработчики** | [ARCHITECTURE_RU.md](ARCHITECTURE_RU.md) · [api_ru.md](api_ru.md) · [frontend_ru.md](frontend_ru.md) |
| **DevOps / SRE** | [deployment_ru.md](deployment_ru.md) · [operations_ru.md](operations_ru.md) · [configuration_ru.md](configuration_ru.md) |
| **ИБ / compliance** | [security_ru.md](security_ru.md) · [privacy_ru.md](privacy_ru.md) |
| **Владельцы базы знаний** | [knowledge_base_ru.md](knowledge_base_ru.md) · [rag_evaluation_ru.md](rag_evaluation_ru.md) |
| **QA / настройка RAG** | [rag_evaluation_ru.md](rag_evaluation_ru.md) · [api_ru.md](api_ru.md) (SSE trace) |

## Полный каталог

| Документ | Содержание |
|----------|------------|
| [PRD_RU.md](PRD_RU.md) | Продуктовые требования |
| [ARCHITECTURE_RU.md](ARCHITECTURE_RU.md) | Техническая архитектура, потоки данных, RAG |
| [roadmap_ru.md](roadmap_ru.md) | Этапы от демо MVP до продакшена |
| [api_ru.md](api_ru.md) | Справочник HTTP API, коды ошибок, SSE |
| [configuration_ru.md](configuration_ru.md) | Переменные окружения и настройки |
| [deployment_ru.md](deployment_ru.md) | Локальная разработка и Docker Compose |
| [operations_ru.md](operations_ru.md) | ETL, бэкапы, мониторинг, troubleshooting |
| [knowledge_base_ru.md](knowledge_base_ru.md) | Подготовка и обновление `rag-document.md` |
| [rag_evaluation_ru.md](rag_evaluation_ru.md) | Методика оценки качества RAG |
| [security_ru.md](security_ru.md) | Модель угроз, guards, hardening |
| [privacy_ru.md](privacy_ru.md) | Обработка данных и compliance |
| [frontend_ru.md](frontend_ru.md) | Структура React SPA и состояние |
| [glossary_ru.md](glossary_ru.md) | Термины продукта и разработки |
| [adr/](adr/) | Architecture Decision Records |

## Документация пакетов (вне `docs/`)

| Документ | Содержание |
|----------|------------|
| [backend/etl/README_RU.md](../backend/etl/README_RU.md) | Парсер и чанкер |
| [backend/tests/README_RU.md](../backend/tests/README_RU.md) | Тесты и команды |

## Соглашение об именах

| Файлы | Регистр |
|-------|---------|
| `README.md`, `README_RU.md`, `PRD.md`, `PRD_RU.md`, `ARCHITECTURE.md`, `ARCHITECTURE_RU.md` | **ЗАГЛАВНЫЕ** |
| Остальные файлы в `docs/` (например `api.md`, `roadmap.md`, `adr/`) | строчные |

## Языковые версии

Большинство документов доступно на **английском** и **русском** (`*_ru.md`). Ссылка на альтернативный язык — в начале каждого файла.

## Интерактивная документация API

При запущенном backend OpenAPI UI доступен по адресу:

- `http://127.0.0.1:8000/docs` (локальная разработка)
- `http://localhost:8080/api/docs` (Docker через Nginx — если проксируется)

[api_ru.md](api_ru.md) — стабильный человекочитаемый контракт; сгенерированный OpenAPI может содержать дополнительные детали схем.
