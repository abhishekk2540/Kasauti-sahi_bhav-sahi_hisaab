# Kasauti-sahi_bhav-sahi_hisaab
# Kasauti: jeweller toolkit (backend + frontend)

`backend/` is a FastAPI API and `frontend/` is a Next.js (App Router, TypeScript, Tailwind) web app. Together they make a jeweller B2B tool: daily gold/silver rates, branded rate banner, customer price alerts,
11-month scheme ledger and an AI assistant. Built from `Jeweller_AI_Project_Plan.xlsx` (user stories US-01..US-17).

**Design rule:** money decisions are deterministic code. The LLM only explains and drafts; every number it shows
comes from a tool call into the database, and it can never change data without the owner's confirmation.

> Step-by-step VS Code + configuration guide: see **SETUP.md**.

## Run locally
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env            # set RATE_PROVIDER=mock to work offline
set -a; . ./.env; set +a
uvicorn app.main:app --reload   # docs at http://localhost:8000/docs
python -m app.jobs daily        # fetch rates -> run alert rules -> draft scheme reminders
python -m pytest -q             # 45 tests
python -m evals.run_evals       # agent eval, 16 cases (needs GROQ_API_KEY or ANTHROPIC_API_KEY in .env)
```
Or `docker compose up` (API + Postgres).

## Story coverage
| Story | Where |
|---|---|
| US-01 signup, shop name, logo | `routers/auth.py` |
| US-02 daily rates, last-known + `stale` flag | `services/rates.py`, `providers.py`, `jobs.py` |
| US-03 banner PNG | `GET /banner.png`, `services/banner.py` |
| US-04 margin per metal, change log | `PUT /margins/{metal}`, `GET /margins/log` |
| US-05 customers (search, opt-out) | `routers/customers.py` |
| US-06/07 customer alerts, delivery status | `services/alerts.py`, `GET /alerts/deliveries` |
| US-08 own rules, deterministic | `services/rules.py` (no LLM) |
| US-09 scheme ledger | `routers/schemes.py`, `services/schemes.py` |
| US-10 reminders: AI draft, editable, owner sends | `services/reminders.py` |
| US-11 agent: tools, streaming, confirm-before-write | `services/agent/`, `POST /agent/chat` (SSE) |
| US-12 price explanation from stored data only | tool `get_price_movement` |
| US-13 dashboard | `GET /dashboard` |
| US-14 backtest incl. GST + spread, reports losses | `GET /backtest` |
| US-15 evals | `evals/` |
| US-16 disclaimer | banner, alert text, every rates/dashboard response |
| US-17 Docker + CI + daily cron | `Dockerfile`, `.github/workflows/` |

## Things to know before going live
1. **Live prices are untested.** `GoldApiProvider` (gold-api.com spot + open.er-api.com USD/INR) could not be reached
   from the build sandbox, so only the mock provider ran in tests. Run one real `POST /rates/refresh` and check the shape.
2. **Spot is not the Indian retail rate.** It excludes import duty and local premium. Compare with a local jeweller's
   quote and set `RATE_ADJUST_GOLD_PCT` / `RATE_ADJUST_SILVER_PCT`.
3. **No price history on day 1.** 7/30-day averages and alerts need 3+ stored days; backtest needs 40+. Start the
   daily job early (or import a historical CSV into `rates`).
4. **Postgres not exercised.** Tests run on SQLite; models are portable but run `docker compose up` once. Add Alembic
   before the first schema change (currently `create_all`).
5. **Telegram:** create a bot, set `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_WEBHOOK_SECRET`, then
   `setWebhook` to `https://<api>/telegram/webhook` with `secret_token`. Owners and customers link via the deep links
   returned by `GET /me` and `GET /customers`; customers can `/stop`.
6. **Agent evals have not been run against a real model** (no API key in the sandbox). Default model is Groq `openai/gpt-oss-20b`, a small model: expect it to miss some tool-selection cases, which is exactly what the evals measure. If accuracy is low, tighten the prompt in `services/agent/runner.py` or switch `GROQ_MODEL`. The agent loop, tools and confirmation flow are tested
   with scripted fake models for both Groq and Anthropic (streamed tool-call chunks, bad JSON, parallel calls). Run `evals.run_evals` and put the real accuracy % here.
7. Legal check with a CA/lawyer before any paid launch (per US-16).

## Frontend
`frontend/`: dashboard, rates + margin + shareable banner, customers, alerts, schemes + payments, reminders (review before send),
streaming AI assistant with confirm-before-write, backtest, settings. Run it with `npm install && npm run dev` (see SETUP.md, step 9).
It was tested end to end in a real browser against the backend (13 flows incl. mobile layout) using a mock Groq server;
not yet tested against live Groq, live prices or Telegram.
