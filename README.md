<div align="center">

# حَدُّوتَة - HADOTA Local AI Assistant

<p align="center">
  <img src="assets/HADOTA_حَدُّوتَة.png" alt="HADOTA (حَدُّوتَة) — Your Local AI Assistant" width="900">
</p>

> **HADOTA (حَدُّوتَة)** takes its name from the Egyptian Arabic word for a story or tale. Inspired by a great storyteller's curiosity, HADOTA is a local AI companion designed to make learning, exploring ideas, and having meaningful conversations feel natural and engaging.
More than just an assistant, HADOTA aims to create a personal space for curiosity, whether you're discovering a new concept, asking questions, exploring complex topics, or simply thinking out loud.
HADOTA brings the spirit of a curious storyteller to local AI.
</p>
</div>

HADOTA is a locally run Arabic/English chat application. It serves a small browser UI and a FastAPI API from one origin, while using the existing local Ollama runtime and the configured `qwen3.8:27b` model. The web app currently uses a **non-streaming request/response path**; streaming in the browser is not claimed as complete.

## What is implemented

- Arabic-first chat interface with mixed Arabic/English text support, separate conversations, conversation history, copy actions, and response continuation where available.
- Anonymous temporary sessions without registration, login, usernames, or passwords.
- Per-session conversation ownership checks, in-memory history, idle/absolute session expiry, and service cleanup.
- A maximum of one active generation, non-blocking busy handling, per-session and process-wide generation rate limits, bounded API request bodies, message-size validation, and finite session/conversation caps.
- Separate `/api/health` liveness and `/api/ready` runtime/model readiness endpoints.
- Safe Markdown rendering when the local `marked` and DOMPurify assets are installed.

## Architecture

```text
Browser
  └─ FastAPI UI + API (same origin)
       └─ anonymous in-memory session/conversation registry
            └─ ConversationService
                 └─ Prompt/context management
                      └─ OllamaRuntime → local Ollama → qwen3.8:27b
```

The app does not expose Ollama's port `11434` through its web server. Conversation state is kept in memory and disappears when a session expires or the FastAPI process restarts.

## Requirements

- Python 3.13 (the current Windows development environment uses Python 3.13).
- Ollama installed and running locally.
- The configured model installed, normally `qwen3.8:27b`.
- Node.js/npm only when the local Markdown/sanitizer assets need to be restored.

Install Python dependencies from the project root:

```powershell
python -m pip install -r requirements-dev.txt
```

The project also uses local `marked` and DOMPurify browser assets. To restore them when `frontend/vendor/node_modules` is absent:

```powershell
npm ci --prefix frontend/vendor
```

The tokenizer JSON used by the local token-counter tests may be a large local artifact; make sure `assets/tokenizers/qwen3.8-27b/tokenizer.json` is present before running those tests.

## Configure and start on Windows

The defaults are intended for local-only access. `.env.example` documents supported settings. Copy it to `.env` only when overrides are required; never commit `.env` or secrets.

```powershell
Set-Location "D:\Projects\Local AI Assistan"
python -m uvicorn app.web.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

Health checks:

- `GET /api/health`: confirms the web process is responsive; it does not require Ollama to be online.
- `GET /api/ready`: checks runtime reachability and, when the active configuration is available, the configured model inventory.

## Anonymous session and privacy behavior

- No account or login is required.
- The server creates an opaque HttpOnly session cookie. Conversation IDs alone do not grant access; the server checks ownership.
- Conversations and history are held in memory, not in a database.
- The UI attempts best-effort session cleanup when the visitor ends the session. Server-side idle and absolute TTLs remain authoritative.
- Restarting FastAPI clears all sessions and history.
- Do not enter passwords, API keys, personal secrets, or sensitive data.
- Local inference uses the Ollama process on the host computer. If the site is shared through a public HTTPS tunnel, visitor requests travel over that tunnel to the host machine; this is not a cloud-hosted inference service.

## Current default resource limits

| Control | Default |
|---|---:|
| API request body | 64 KiB |
| Message length | 4,000 characters |
| Active anonymous sessions | 25 |
| Conversations per session | 5 |
| Idle session TTL | 15 minutes |
| Absolute session lifetime | 4 hours |
| Per-session generations | 10 per 60 seconds |
| Global generations | 20 per 60 seconds |
| Active model generations | 1 |

These are configured guardrails, not performance or capacity guarantees. Public mode validates that the configured limits remain within a conservative policy. The public endpoint must stay disabled until the local and security acceptance gates in `docs/README_07_hadota_web_chat.md` pass.

## Tests

Run the deterministic suite and configured local integration checks with:

```powershell
python -m pytest .\tests\ -q
```

The two real-Ollama smoke-test modules contact the local runtime and require Ollama/model availability. CI runs deterministic tests without those local-runtime smoke tests. The token-counter tests need the local tokenizer JSON asset described above.

Also check syntax:

```powershell
python -m compileall -q app tests
node --check frontend\app.js
```

## Public sharing status

Tailscale Funnel is **not activated by this project change**. Because the approved experience has no login/password gate, anyone who gets a public URL can try to use the computer's local model. Public sharing must remain off until anonymous session isolation, limits, cancellation/failure paths, manual smoke tests, and the stop/kill-switch procedure are verified from an external network. Never expose Ollama port `11434` directly.

## Known limitations

- The browser web path is non-streaming. Do not represent it as live token streaming.
- The app runs on the owner's PC and depends on that PC, Ollama, the selected model, and the internet connection when shared remotely.
- There is no database, persistent user history, account system, unlimited concurrency, uptime guarantee, or production security certification.
- A public URL without a login gate is open to anyone who obtains it; limits reduce but do not eliminate abuse risk.
