# Setup guide: run Kasauti backend locally (VS Code)

## 0. Prerequisites
- Python 3.12+ (`python --version`)
- VS Code with the **Python** extension (VS Code will suggest the recommended ones when you open the folder)
- Optional: Docker Desktop (only for the Postgres route)

## 1. Open the project
`File > Open Folder...` and choose the **kasauti** folder (the one that contains `backend/` and `.vscode/`).

## 2. Create a virtual environment and install packages
Open a terminal in VS Code (`Ctrl+` ` ) and run:

**Mac / Linux**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
**Windows (PowerShell)**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
(If PowerShell blocks the script: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.)

Then press `Ctrl+Shift+P` > **Python: Select Interpreter** > choose `backend/.venv`.

## 3. Configure (the `.env` file)
```bash
cp .env.example .env        # Windows: copy .env.example .env
```
Edit `backend/.env`. The app reads this file automatically; you never export variables by hand.

| Variable | What to put | Needed? |
|---|---|---|
| `RATE_PROVIDER` | `mock` = fake prices, works offline (use this first). `goldapi` = real prices from the internet | yes |
| `DATABASE_URL` | Neon pooled PostgreSQL URL, including `?sslmode=require`; SQLite remains available for local-only development | no |
| `JWT_SECRET` | Any long random text. Generate: `python -c "import secrets;print(secrets.token_urlsafe(32))"` | yes in production |
| `CORS_ORIGINS` | Frontend address, e.g. `http://localhost:3000` (comma-separate several) | when frontend exists |
| `RATE_ADJUST_GOLD_PCT` / `_SILVER_PCT` | Calibrate to Indian retail rate, e.g. `6`. Compare with a local jeweller's quote | when using `goldapi` |
| `GROQ_API_KEY` | From console.groq.com/keys (starts with `gsk_`). If set, Groq is used automatically | for AI features |
| `GROQ_MODEL` | Default `openai/gpt-oss-20b` | no |
| `LLM_PROVIDER` | `groq` or `anthropic`. Leave empty = groq if `GROQ_API_KEY` is set, else anthropic | no |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | Only if you want Claude instead of Groq (default model `claude-sonnet-5-5`) | no |
| `TELEGRAM_BOT_TOKEN` | From @BotFather on Telegram (`/newbot`) | for alerts |
| `TELEGRAM_BOT_USERNAME` | The bot's username without `@` (makes the customer/owner link buttons work) | for alerts |
| `TELEGRAM_WEBHOOK_SECRET` | Any random string you choose | for alerts |
| `REMINDER_DAYS_BEFORE` | Days before due date to draft scheme reminders (default 3) | no |

Minimum to start: `RATE_PROVIDER=mock`. Without a Telegram token, alerts are only logged to the terminal, not sent.

## 4. Configure local authentication
Kasauti uses its backend for email/password signup and login. Signup requires a name, phone
number, email, password, and matching confirmation. Passwords must be at least seven characters
and include uppercase, lowercase, a number, and a special character.
```dotenv
# backend/.env
JWT_SECRET=replace-with-a-long-random-value
```
After signup or login, the frontend stores the short-lived API token locally and opens the
dashboard. Never commit `.env` files.

## 5. Run the API
**Easiest in VS Code:** press `F5` (or Run and Debug panel) and pick **API (uvicorn, reload)**. Breakpoints work.

**Or from the terminal** (inside `backend/`, venv active):
```bash
uvicorn app.main:app --reload
```
Open http://localhost:8000/docs for the interactive API page, and http://localhost:8000/health should say `{"status":"ok"}`.

## 6. Try it
- Open `backend/requests.http` and install the **REST Client** extension; click *Send Request* on each block in order
  (sign up > copy token into `@token` > refresh rates > rates > banner ...). Or do the same in `/docs` using the
  **Authorize** button.
- Run the daily job (fetch rates, check alerts, draft reminders): `F5` > **Daily job**, or `python -m app.jobs daily`.
- Mock prices only start today, so averages/alerts need a few days of data. To test alerts now, run the tests (they seed history).

## 7. Run tests
Click the beaker icon in VS Code's sidebar (pytest is pre-configured), or:
```bash
python -m pytest -q
```

## 8. Real prices, Telegram, AI (when ready)
1. **Real prices:** set `RATE_PROVIDER=goldapi`, restart, call `POST /rates/refresh`. If it returns `ok: false`, read `error`.
2. **Telegram:** create bot with @BotFather, fill the three `TELEGRAM_*` values. Telegram must reach your server, so for local testing use a tunnel (e.g. `ngrok http 8000`), then register it once:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/setWebhook" -d "url=https://<your-ngrok>/telegram/webhook" -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>"
   ```
   Then `GET /me` returns `telegram_link`: open it and press Start. Customers get their own link from `GET /customers`.
3. **AI (Groq):** in `backend/.env` set `GROQ_API_KEY=gsk_...` (nothing else needed; the model defaults to `openai/gpt-oss-20b`), restart, call `POST /agent/chat` (responses stream as Server-Sent Events). Scheme reminder drafts also use it. Run `F5` > **Agent evals** to measure accuracy and put the % in the README. Never commit `.env` or paste the key into chat; `.gitignore` already excludes it.

## 9. Neon PostgreSQL instead of SQLite (optional)
1. In the Neon dashboard, open your project and copy the **pooled** connection string.
   It normally contains `-pooler` in the hostname and ends with `?sslmode=require`.
2. In `backend/.env`, replace only the `DATABASE_URL` value. Do not commit this file:
   ```dotenv
   DATABASE_URL=postgresql://<user>:<password>@<host>/<database>?sslmode=require
   ```
3. Restart the API. On startup, `init_db()` creates the SQLAlchemy tables in Neon.
4. Verify the connection:
   ```bash
   python -c "from sqlalchemy import text; from app.db import engine; print(engine.connect().execute(text('SELECT 1')).scalar())"
   ```
   The command must print `1`. If Neon reports a certificate or connection error, re-copy the
   pooled URL and keep `sslmode=require`.

## 10. Run the frontend (Next.js)
Needs **Node.js 20+** (`node -v`). Keep the backend from step 4 running.
```bash
cd frontend
cp .env.example .env.local     # Windows: copy .env.example .env.local
npm install
npm run dev                    # http://localhost:3000
```
`frontend/.env.local` has one setting: `NEXT_PUBLIC_API_URL=http://localhost:8000` (where the backend lives).
In VS Code you can also press `F5` and choose **Full stack (API + Frontend)** to start both.

First run: open http://localhost:3000, **Create account**, then on **Rates & Banner** press *Fetch rates now*
(with `RATE_PROVIDER=mock` this gives fake prices; history fills one day at a time, so charts and 7/30-day
comparisons stay empty for the first days unless you seed data).

Make sure the backend `CORS_ORIGINS` includes the frontend address (default `http://localhost:3000`).

### Deploy
- **Frontend on Vercel:** import the repo, set *Root Directory* = `frontend`, add env var `NEXT_PUBLIC_API_URL` = your backend URL (https).
- **Backend on Render/Railway:** root `backend`, Dockerfile build; set `DATABASE_URL`, `JWT_SECRET`, `APP_ENV=production`, `CORS_ORIGINS=https://<your-vercel-domain>`, plus `GROQ_API_KEY` / Telegram vars.
- Update `NEXT_PUBLIC_API_URL` if the backend URL changes; it is baked in at build time, so redeploy the frontend.

## Troubleshooting
- **`ModuleNotFoundError: app`**: you are not inside `backend/`. `cd backend`, or use the F5 configs (they set it).
- **`ModuleNotFoundError: fastapi`**: wrong interpreter. Select `backend/.venv` (step 2) and reopen the terminal.
- **401 Not authenticated**: send `Authorization: Bearer <token>`; tokens expire after 72 h, log in again.
- **Login keeps returning to the sign-in page**: clear the `kasauti_token` local-storage item,
  restart the backend and frontend, then log in again.
- **Banner shows "Rs." instead of the rupee sign** (Linux only): `sudo apt install fonts-dejavu-core`.
- **`409 No rates available yet`**: call `POST /rates/refresh` first.
- **Changed `.env` but nothing changed**: restart the server (`--reload` watches code, not `.env`).
- **Reset local data**: stop the server, delete `backend/kasauti.db`.
- **Frontend shows "Cannot reach the server"**: backend not running, or `NEXT_PUBLIC_API_URL` wrong. Restart `npm run dev` after editing `.env.local`.
- **Browser console CORS error**: add the frontend address to `CORS_ORIGINS` in `backend/.env` and restart the API.
- **Logged out suddenly**: tokens last 72 hours; log in again.
