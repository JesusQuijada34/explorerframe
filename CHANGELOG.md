# Changelog — ExplorerFrame

All notable changes to this project are documented here.
Format: `[version] YYYY-MM-DD — description`

---

## [v1.2] 2026-03-14

### Server (`app.py`)
- **Fix HTTP 500**: session directory now created before `Session(app)` initializes, preventing crash on first request in Render
- **Fix gunicorn timeout**: `render.yaml` now starts gunicorn with `--workers 1 --timeout 120` — prevents worker kill during 30s long-poll
- **Bot 24/7**: Telegram bot polling runs in a daemon thread started at module load; `threading.Lock` prevents duplicate threads across gunicorn restarts; 409 conflicts handled with backoff
- **Redirect if logged in**: `/`, `/login/`, `/register/` now redirect to `/dashboard/` when a session is active
- **Platform block**: Linux, macOS, Android, iOS user-agents are blocked on public pages and redirected to `/unavailable` (HTTP 403)
- **GitHub release tracking**: reads `details.xml` from the repo's `main` branch to get the current version, then fetches the matching GitHub release and locates `EF.zip` (the patch bundle containing `ExplorerFrame.exe` + `Winverm.exe`); validates the download URL with a HEAD request before caching
- **New version notification**: when `details.xml` version changes, all registered users receive a Telegram message with the download link and the release changelog sent as a `.md` file
- **Bot commands `/start` and `/help`**: redesigned with full onboarding instructions, available commands list, and current version info
- **Bot command `/version`**: new command — shows current version and direct `EF.zip` download link
- **Bot command `/key`**: shows permanent API key + inline language menu (Python, Bash, PowerShell, Node.js, PHP) with ready-to-use download snippets
- **Bot command `/download`**: sends `ExplorerFrame.exe` directly to the chat for registered users
- **`SESSION_COOKIE_SECURE`**: enabled only when `FLASK_ENV=production`
- **Dashboard `base_url`**: snippets now show the real server URL instead of a placeholder
- **Dashboard onboarding guide**: step-by-step instructions for registration, bot commands, and session duration
- **`og:image` / Twitter Card**: index page includes preview meta tags pointing to an auto-screenshot of the site
- **Error pages**: `404.html` (not found) and `unavailable.html` (platform block) added; `403` handler wired to existing `forbidden.html`

### Agent (`explorer.py`)
- **`dotenv` support**: loads `.env` at startup; `BOT_TOKEN`, `API_URL`, `OWNER_ID` read from environment
- **`OWNER_ID`**: always added to `authorized_users` regardless of `AUTHORIZED_IDS` value
- **`check_for_updates` → `check_for_updates_job`**: converted to `async def` with `context: ContextTypes.DEFAULT_TYPE` signature, registered directly in `job_queue` (no more `asyncio.create_task` wrapper)
- **Fix auth header**: changed `Authorization: Bearer` → `X-API-Key` in update token requests
- **Fix keylog clear**: `keylog.txt` is now emptied only after a successful send, not unconditionally
- **Startup warning**: logs a warning if `authorized_users` is empty at boot

### Winverm (`winverm.py`)
- **Fix auth header**: changed `Authorization: Bearer` → `X-API-Key`

### Config
- **`.env`**: documented all variables — `BOT_TOKEN`, `API_URL`, `APP_BASE_URL`, `OWNER_ID`, `AUTHORIZED_IDS`, `UPDATE_TOKEN`, `GITHUB_REPO`
- **`render.yaml`**: added `APP_BASE_URL`, `FLASK_ENV=production`; gunicorn flags `--workers 1 --timeout 120 --keep-alive 5`
- **`details.xml`**: added `encoding="UTF-8"` declaration; formatted consistently

### Templates
- **`templates/unavailable.html`**: new — Windows-only block page with OS compatibility chips
- **`templates/index.html`**: og:image + Twitter Card meta tags; version badge from `details.xml`
- **`templates/dashboard.html`**: onboarding guide section; real `base_url` in all code snippets

---

## [v1.0.0] 2026-03-01

- Initial release: agent (`explorer.py`), server (`app.py`), updater helper (`winverm.py`)
- Telegram bot with 2FA registration, backup, screenshot detection, keylogger, file explorer, power control, WiFi control, patch application
- Flask server with MongoDB, bcrypt, API key auth, one-time download tokens
- Render deployment config
