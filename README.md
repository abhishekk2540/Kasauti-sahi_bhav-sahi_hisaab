# Kasauti — Sahi Bhav, Sahi Hisaab

A B2B digital toolkit for jewellery businesses to manage daily metal rates, customer price alerts, jewellery savings schemes, and business operations through a unified dashboard.

Kasauti combines deterministic financial calculations with AI-assisted business workflows, helping jewellers make informed decisions while keeping pricing, financial records, and business actions under their control.

---

## Overview

Kasauti is a full-stack jewellery business management platform consisting of a FastAPI backend and a Next.js frontend.

The platform brings essential jewellery business operations into one place:

- Daily gold and silver market rates.
- Branded, shareable rate banners.
- Customer management and automated price alerts.
- 11-month jewellery savings scheme ledger.
- Payment tracking and scheme reminders.
- AI-powered business assistant.
- Intelligent alert agent with tool-based execution.
- Historical rate analysis and backtesting.

**Core principle:** Financial calculations are handled by deterministic application logic. AI is used for explanations, assistance, and drafting—not as a source of financial truth. Every financial figure comes from application tools and database records. Any operation that modifies business data requires owner confirmation.

---

## Key Features

### 1. Gold & Silver Rate Management
- Daily gold and silver rate fetching.
- Live rate provider integration.
- Last-known rate fallback.
- Stale-rate identification.
- Configurable metal price adjustments.
- Historical rate tracking.

### 2. Branded Rate Banner
- Automatically generated PNG rate banners.
- Shop name and branding.
- Shareable daily gold and silver prices.
- Rate disclaimer included in generated banners.

### 3. Customer Management & Alerts
- Customer registration and management.
- Customer search functionality.
- Individual customer alert preferences.
- Automated price-based alert rules.
- Alert delivery status tracking.
- Customer notification opt-out.

### 4. Jewellery Savings Scheme Ledger
- 11-month savings scheme management.
- Customer-wise scheme records.
- Monthly payment tracking.
- Payment history.
- Scheme maturity tracking.
- Automated reminder drafts.

### 5. AI Business Assistant
- Natural-language business queries.
- Database-connected information retrieval.
- Gold and silver price explanations.
- Customer and scheme information assistance.
- Streaming responses using Server-Sent Events.
- Tool-based execution.
- Confirmation before modifying business records.

### 6. Intelligent Alert Agent
- Automated alert-rule evaluation.
- Customer-specific notification workflows.
- Database-backed tool execution.
- AI-generated reminder drafts.
- Owner-controlled message approval.
- Delivery tracking.

### 7. Rate Analysis & Backtesting
- Historical rate movement analysis.
- 7-day and 30-day averages.
- GST and spread-aware backtesting.
- Profit and loss reporting.
- Historical strategy evaluation.

---

## System Architecture

```text
                 KASAUTI PLATFORM
                        |
           +------------+------------+
           |                         |
      Next.js Frontend           FastAPI Backend
           |                         |
           |                  +------+------+
           |                  |             |
           |              REST APIs     AI Agent
           |                  |             |
           |                  |        Tool Execution
           |                  |             |
           |                  +------+------+
           |                         |
           |                    Database
           |                         |
           |              +----------+----------+
           |              |          |          |
           |            Rates     Customers   Schemes
           |              |          |          |
           |              +----------+----------+
           |                         |
           |                  Background Jobs
           |                         |
           +-------------------------+
```

### Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, React, TypeScript |
| Styling | Tailwind CSS |
| Backend | Python, FastAPI |
| Database | SQLite, PostgreSQL |
| AI Integration | Groq, Anthropic |
| AI Model | GPT-OSS-20B (configurable) |
| Authentication | JWT |
| Market Data | GoldAPI, USD/INR exchange-rate API |
| Notifications | Telegram Bot API |
| API Documentation | OpenAPI / Swagger |
| Testing | Pytest, Agent Evaluations |
| Deployment | Docker, Docker Compose |
| CI/CD | GitHub Actions |

---

## Project Structure

```text
kasauti/
│
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── providers.py
│   │   ├── jobs.py
│   │   └── main.py
│   │
│   ├── evals/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── public/
│   └── package.json
│
├── .github/
│   └── workflows/
│
├── docker-compose.yml
├── SETUP.md
└── README.md
```

---

## Getting Started

### Prerequisites

Make sure you have the following installed:

- Python 3.10+
- Node.js 20+
- npm
- Git
- PostgreSQL (optional for local development)

### 1. Clone the Repository

```bash
git clone https://github.com/abhishekk2540/Kasauti-sahi_bhav-sahi_hisaab.git

cd Kasauti-sahi_bhav-sahi_hisaab
```

### 2. Backend Setup

```bash
cd backend

python -m venv venv
```

Activate the virtual environment.

**Windows:**

```powershell
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Create your environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Configure the required environment variables in `.env`.

| Variable | Description |
|---|---|
| `APP_ENV` | Application environment |
| `DATABASE_URL` | Database connection string |
| `JWT_SECRET` | JWT signing secret |
| `CORS_ORIGINS` | Allowed frontend origins |
| `RATE_PROVIDER` | Gold rate provider (`goldapi` or `mock`) |
| `GOLDAPI_API_KEY` | GoldAPI authentication key, if required by implementation |
| `RATE_ADJUST_GOLD_PCT` | Gold price adjustment |
| `RATE_ADJUST_SILVER_PCT` | Silver price adjustment |
| `LLM_PROVIDER` | AI provider selection |
| `GROQ_API_KEY` | Groq API key |
| `GROQ_MODEL` | Groq model name |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `ANTHROPIC_MODEL` | Anthropic model name |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_BOT_USERNAME` | Telegram bot username |
| `TELEGRAM_WEBHOOK_SECRET` | Telegram webhook verification secret |
| `REMINDER_DAYS_BEFORE` | Reminder scheduling configuration |

For local development, use the mock rate provider to avoid depending on external market-data services.

### 4. Start the Backend

```bash
uvicorn app.main:app --reload
```

Backend:

```text
http://localhost:8000
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

### 5. Run Background Jobs

```bash
python -m app.jobs daily
```

This executes the daily workflow:

- Fetch metal rates.
- Evaluate customer alert rules.
- Draft scheme reminders.

### 6. Frontend Setup

Open another terminal:

```bash
cd frontend

npm install

npm run dev
```

Frontend:

```text
http://localhost:3000
```

For additional configuration details, refer to `SETUP.md`.

---

## Testing & Evaluation

Kasauti includes automated backend tests and AI agent evaluation cases.

Run backend tests:

```bash
cd backend

python -m pytest -q
```

Current test coverage:

- 45 automated tests.
- Agent evaluation suite with 16 cases.
- Scripted model testing for Groq and Anthropic integrations.
- Tool execution and confirmation-flow testing.

Run agent evaluations:

```bash
python -m evals.run_evals
```

Agent evaluations require a configured AI provider API key.

---

## Business Logic & Data Safety

Financial accuracy is a central design requirement of Kasauti.

The platform follows these principles:

1. Financial calculations are performed using deterministic application code.
2. AI responses use database-backed tools for financial information.
3. AI cannot independently modify customer or financial records.
4. Business data modifications require owner confirmation.
5. Customer notification preferences and opt-out settings are respected.
6. Rate disclaimers are included in relevant price-related outputs.

AI assists business operations without replacing the underlying financial logic.

---

## Current Implementation Status

The following points should be considered before production deployment:

- **Market data:** Live GoldAPI integration requires real-world verification.
- **Retail pricing:** International spot prices are not equivalent to Indian jewellery retail prices. Local duties, premiums, and applicable taxes must be considered.
- **Historical data:** Moving averages and backtesting require sufficient stored rate history.
- **PostgreSQL:** Local tests primarily use SQLite. PostgreSQL deployment requires additional integration testing.
- **Database migrations:** Alembic should be introduced before production schema changes.
- **Telegram:** Production webhook configuration and end-to-end notification delivery require verification.
- **AI evaluation:** Real-model evaluation results should be recorded after testing with live provider credentials.
- **Production readiness:** Legal and financial compliance should be reviewed before commercial deployment.

---

## Future Scope

Potential areas for further development:

- WhatsApp Business API integration.
- Advanced customer segmentation.
- Multi-shop and multi-branch management.
- Advanced sales and inventory analytics.
- Improved notification automation.
- Historical price forecasting.
- Additional business intelligence reports.

---

## License

This project is distributed under the license included in the repository. See [LICENSE](LICENSE) for details.

---

## Author

**Abhishek Kumar**

Full Stack Developer | React | Next.js | Python | FastAPI | AI Integration

GitHub: https://github.com/abhishekk2540

---

**Kasauti — Sahi Bhav, Sahi Hisaab.**

A practical digital toolkit for modern jewellery businesses.
