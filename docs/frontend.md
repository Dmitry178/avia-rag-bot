# Frontend architecture

**English** · [Русский](frontend_ru.md)

Structure and conventions of the **avia-bot** React SPA. Backend contract: [api.md](api.md). System context: [ARCHITECTURE.md](ARCHITECTURE.md#frontend-architecture).

---

## Stack

| Technology | Role |
|------------|------|
| React 19 | UI framework |
| TypeScript | Typing |
| Vite | Dev server, build, `/api` proxy |
| PrimeReact | Components (dialogs, inputs, toasts) |
| TanStack Query | Server state (chats, messages) |
| Zustand | Client UI state (settings, theme, selection) |
| i18next | Russian (default) and English |

---

## Directory layout

```
frontend/src/
├── app/                 # Shell, layout, providers
│   ├── layout/          # AppLayout, AppHeader
│   └── providers/       # QueryClient, SSE, theme hydration
├── features/
│   ├── chats/           # Sidebar, chat list, SSE hook
│   ├── chat/            # Dialog, composer, mode switch
│   ├── rag/             # RAG settings panel
│   ├── llm/             # LLM parameters panel
│   └── trace/           # Trace panel (RAG mode)
├── shared/
│   ├── api/             # HTTP client, types, queryClient
│   ├── i18n/            # Locales en.json, ru.json
│   ├── components/      # Modal, toast, delete confirm
│   └── persist.ts       # localStorage helpers
├── theme/               # Light/dark/system themes
└── styles/global.css
```

Feature-based folders — colocate components, hooks, and stores per domain.

---

## Layout

Three-column shell (`app/layout/AppLayout.tsx`):

| Column | RAG mode | LLM mode |
|--------|----------|----------|
| Left | Chat sidebar | Chat sidebar |
| Center | Chat panel + composer | Chat panel + composer |
| Right | Trace panel | LLM parameters panel |

Mode switch in header (`features/chat/modeStore.ts`). Chat lists are filtered by `chat_type` on the API.

**Decision tree UI:** when `metadata.decision_tree_guidance` is present, `ChatPanel` renders an operational procedure card above the assistant reply.

---

## State management

| Concern | Solution | Persistence |
|---------|----------|-------------|
| Chats, messages | TanStack Query (`useChats`, `useChat`) | Server |
| RAG toggles | `ragSettingsStore` | localStorage + sent per message |
| LLM settings | `llmSettingsStore` | localStorage + sent per message |
| Selected chat per mode | `chats/store.ts` | localStorage |
| Chat mode (llm/rag) | `modeStore.ts` | localStorage |
| Theme | `theme/store.ts` | localStorage |
| Composer draft | `composerDraftStorage.ts` | session per chat |
| Delete confirm | `deleteConfirmStore` | ephemeral |

Settings are included in each `POST /messages` so the backend snapshots them in message metadata.

---

## API client

- Base URL: `VITE_API_URL` or relative `/api`
- Module: `shared/api/chats.ts`
- Types: `shared/api/types.ts` (mirror backend schemas)
- Dev proxy: `vite.config.ts` → `http://127.0.0.1:8000`
- Prod: Nginx proxies `/api` to backend container

Network errors: `shared/api/networkError.ts` — user-facing toasts.

---

## Real-time (SSE)

`features/chats/hooks/useChatEvents.ts` — opened in `AppProviders`:

1. Generate `clientId` (Zustand `chats/store.ts`, persisted per browser).
2. Subscribe to `GET /api/chats/events?client_id=…`.
3. On send, pass same `client_id` in message body.
4. Handle `trace`, `chat_title`, `error` events.

Trace steps update the trace panel live during RAG requests.

---

## Internationalization

- Config: `shared/i18n/config.ts`
- Locales: `shared/i18n/locales/en.json`, `ru.json`
- RAG method help: `shared/i18n/ragMethods.ts`
- Default language: Russian

UI language is independent of knowledge base content language.

---

## Theming

- Definitions: `theme/themes.json`
- Apply: `theme/applyTheme.ts`
- Preferences: `light` | `dark` | `system`

CSS variables in `styles/global.css`.

---

## Key user flows

### Send message (RAG)

1. User types in composer (`useComposerDraft`, auto-resize).
2. `useChat` calls `POST /chats/{id}/messages` with current `rag_config`.
3. SSE `trace` events stream to `TracePanel`.
4. Response appends user + assistant messages to query cache.
5. Optional `chat_title` SSE updates sidebar.

### Create / delete chat

- `useChats` — list, create, delete (empty chats delete without confirm).
- `DeleteConfirmHost` — global confirm dialog for non-empty deletes.

---

## Development commands

```bash
make frontend-install
make frontend-dev      # :5173
make frontend-build
make frontend-typecheck
```

---

## Related documentation

| Document | Content |
|----------|---------|
| [api.md](api.md) | Endpoints and SSE events |
| [deployment.md](deployment.md) | Vite proxy and Docker Nginx |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full system design |
