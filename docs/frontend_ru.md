# Архитектура frontend

**Русский** · [English](frontend.md)

Структура и соглашения React SPA **avia-bot**. Контракт backend: [api_ru.md](api_ru.md). Контекст: [architecture_ru.md](architecture_ru.md).

---

## Стек

| Технология | Роль |
|------------|------|
| React 19 | UI |
| TypeScript | Типизация |
| Vite | Dev server, сборка, proxy `/api` |
| PrimeReact | Компоненты |
| TanStack Query | Серверное состояние (чаты, сообщения) |
| Zustand | Клиентский UI (настройки, тема, выбор) |
| i18next | Русский (по умолчанию) и английский |

---

## Структура каталогов

```
frontend/src/
├── app/                 # Shell, layout, providers
│   ├── layout/          # AppLayout, AppHeader
│   └── providers/       # QueryClient, SSE, theme
├── features/
│   ├── chats/           # Sidebar, список чатов, SSE hook
│   ├── chat/            # Диалог, composer, переключатель режима
│   ├── rag/             # Панель настроек RAG
│   ├── llm/             # Панель параметров LLM
│   └── trace/           # Trace panel (режим RAG)
├── shared/
│   ├── api/             # HTTP-клиент, типы, queryClient
│   ├── i18n/            # en.json, ru.json
│   ├── components/      # Modal, toast, подтверждение удаления
│   └── persist.ts       # localStorage
├── theme/               # Светлая/тёмная/системная тема
└── styles/global.css
```

Feature-based — компоненты, hooks и stores рядом по домену.

---

## Layout

Трёхколоночный shell (`app/layout/AppLayout.tsx`):

| Колонка | RAG | LLM |
|---------|-----|-----|
| Слева | Sidebar чатов | Sidebar чатов |
| Центр | Чат + composer | Чат + composer |
| Справа | Trace panel | Панель LLM |

Переключатель режима в header (`modeStore.ts`). Списки чатов фильтруются по `chat_type` на API.

**Decision tree:** при `metadata.decision_tree_guidance` — карточка операционной процедуры над ответом ассистента.

---

## Управление состоянием

| Задача | Решение | Персистентность |
|--------|---------|-----------------|
| Чаты, сообщения | TanStack Query | Сервер |
| RAG toggles | `ragSettingsStore` | localStorage + в каждом сообщении |
| LLM settings | `llmSettingsStore` | localStorage + в сообщении |
| Выбранный чат по режиму | `chats/store.ts` | localStorage |
| Режим llm/rag | `modeStore.ts` | localStorage |
| Тема | `theme/store.ts` | localStorage |
| Черновик composer | `composerDraftStorage.ts` | session на чат |
| Подтверждение удаления | `deleteConfirmStore` | ephemeral |

Настройки уходят в каждом `POST /messages` — backend сохраняет снимок в metadata.

---

## API-клиент

- Base URL: `VITE_API_URL` или `/api`
- Модуль: `shared/api/chats.ts`
- Типы: `shared/api/types.ts`
- Dev proxy: `vite.config.ts` → `127.0.0.1:8000`
- Prod: Nginx → backend

Ошибки сети: `networkError.ts` — toast пользователю.

---

## Real-time (SSE)

`useChatEvents.ts` в `AppProviders`:

1. `clientId` в Zustand (на браузер).
2. Подписка `GET /api/chats/events?client_id=…`.
3. Тот же `client_id` в теле сообщения.
4. Обработка `trace`, `chat_title`, `error`.

Шаги trace обновляют панель во время RAG-запроса.

---

## Интернационализация

- `shared/i18n/config.ts`
- `locales/en.json`, `ru.json`
- Справка по RAG-методам: `ragMethods.ts`
- Язык по умолчанию: русский

Язык UI не зависит от языка KB.

---

## Темы

- `theme/themes.json`
- `theme/applyTheme.ts`
- `light` | `dark` | `system`

CSS-переменные в `global.css`.

---

## Ключевые сценарии

### Отправка сообщения (RAG)

1. Ввод в composer.
2. `POST /chats/{id}/messages` с `rag_config`.
3. SSE `trace` → `TracePanel`.
4. Ответ добавляет сообщения в кэш Query.
5. `chat_title` по SSE обновляет sidebar.

### Создание / удаление чата

- `useChats` — список, создание, удаление (пустые — без confirm).
- `DeleteConfirmHost` — диалог для непустых.

---

## Команды разработки

```bash
make frontend-install
make frontend-dev      # :5173
make frontend-build
make frontend-typecheck
```

---

## Связанная документация

| Документ | Содержание |
|----------|------------|
| [api_ru.md](api_ru.md) | Endpoints и SSE |
| [deployment_ru.md](deployment_ru.md) | Vite proxy и Docker |
| [architecture_ru.md](architecture_ru.md) | Системный дизайн |
