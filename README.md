# 💰 HisabKitab – Finance Tracker

A full-stack finance tracking application that lets you upload bank statement PDFs, extract transactions using a vision LLM (Ollama or LM Studio), and analyse your spending with interactive dashboards.

---

## Features

- **PDF upload & parsing** — Upload bank statements as PDFs; a background worker converts pages to optimised images and sends them to a local vision LLM for transaction extraction
- **Auto-categorisation** — The LLM deduces each transaction's category (Groceries, Dining, Transport, etc.) from the description; uses the document's own category when present
- **Transaction management** — Filter by merchant, category, type, date range, and amount; inline-edit category and merchant; bulk-delete selected rows or all matching a filter
- **Analytics dashboards** — Monthly spend/receive trend, category breakdown, merchant ranking, and cashflow summary
- **Pluggable LLM backend** — Supports both Ollama and LM Studio via a swappable adapter; handles truncated LLM responses gracefully with a 4-stage JSON recovery fallback
- **Image optimisation** — Pages are rendered at 150 DPI in grayscale and saved as JPEG (~10–20× smaller than colour PNG), drastically reducing LLM token usage while retaining text quality
- **No external system dependencies** — PDF conversion uses PyMuPDF (pure Python wheel); no Poppler or other system packages required

---

## Architecture

```
HisabKitab/
├── backend/                  Flask REST API (also serves the frontend)
│   ├── app.py                Entry point — registers blueprints, starts worker, serves frontend
│   ├── config.py             Environment config (loaded from .env)
│   ├── requirements.txt      Python dependencies
│   ├── .env.example          Environment template
│   └── src/
│       ├── db/               SQLite schema & connection helper
│       ├── auth/             Email/password auth + JWT
│       ├── imports/          PDF upload, background worker, image optimisation,
│       │                     LLM normalisation (4-stage truncation recovery), persistence
│       ├── llm/              Vision LLM adapters — Ollama & LM Studio (pluggable)
│       ├── transactions/     CRUD + filtering / sorting / pagination + bulk-delete
│       └── analytics/        Monthly, category, merchant, cashflow endpoints
│
└── frontend/                 Plain HTML/CSS/JS — served directly by Flask at /
    ├── index.html            Login
    ├── register.html         Sign up
    ├── dashboard.html        Overview (cashflow + recent transactions)
    ├── upload.html           PDF upload + real-time job status polling
    ├── transactions.html     Filterable table with inline edit + bulk actions
    ├── analytics.html        Charts & analytics dashboards
    ├── css/style.css         Dark-themed stylesheet
    └── js/                   API client, auth, toast, imports, transactions, analytics
```

---

## Prerequisites

| Dependency | Why | Install |
|---|---|---|
| **Python 3.11+** | Backend runtime | [python.org](https://python.org) |
| **uv** _(recommended)_ or pip | Package manager | `pip install uv` |
| **Ollama** _or_ **LM Studio** | Local vision LLM for extraction | [ollama.com](https://ollama.com) / [lmstudio.ai](https://lmstudio.ai) |

> **No Poppler required.** PDF-to-image conversion is handled entirely by [PyMuPDF](https://pymupdf.readthedocs.io/), which installs as a pure Python wheel.

### Setting up the Vision LLM

**Ollama:**
```bash
ollama pull llava          # or any vision-capable model (e.g. llava:13b, qwen2-vl)
ollama serve               # starts on localhost:11434
```

**LM Studio:**
1. Download and install from [lmstudio.ai](https://lmstudio.ai)
2. Download a vision model (e.g. Qwen2-VL, LLaVA)
3. Start the local server — default endpoint: `http://localhost:1234`

---

## Quick Start

```bash
cd backend

# Create virtual environment (using uv)
uv venv
.\.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
uv pip install -r requirements.txt

# Configure environment
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
# Edit .env: set SECRET_KEY, LLM_BACKEND, and model settings

# Start the server — initialises DB and starts background worker automatically
python app.py
```

The app is available at **http://localhost:5000** — frontend and API are served from the same process, no separate frontend server needed.

### Usage Flow

1. **Sign Up** — Create an account on the register page
2. **Upload** — Drop a bank statement PDF on the Upload page
3. **Wait** — The background worker converts pages to optimised images and extracts transactions via your vision LLM; status is polled automatically
4. **Review** — Transactions page shows all extracted rows; filter by merchant, category, date, amount; edit merchant or category inline
5. **Bulk clean** — Use the bulk-actions bar to delete selected transactions or all rows matching the current filter
6. **Analyse** — Analytics page shows monthly trends, category breakdown, top merchants, and cashflow summary

---

## API Reference

### Auth
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | `{email, password, display_name?}` |
| `POST` | `/api/auth/login` | `{email, password}` → `{token, user_id}` |
| `GET` | `/api/auth/me` | Current user info (requires `Authorization: Bearer <token>`) |

### Imports
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/imports/upload` | Multipart PDF upload (field: `file`) |
| `GET` | `/api/imports/jobs` | List all import jobs |
| `GET` | `/api/imports/jobs/:id` | Job status + extracted transaction count |

### Transactions
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/transactions` | List with filters, sort, pagination |
| `GET` | `/api/transactions/:id` | Single transaction |
| `PATCH` | `/api/transactions/:id` | Update `category_id`, `merchant`, `description`, `notes` |
| `DELETE` | `/api/transactions/:id` | Delete single transaction |
| `POST` | `/api/transactions/bulk-delete` | Bulk delete by IDs or by filter |
| `GET` | `/api/transactions/categories` | List available categories |

**GET /api/transactions query params:**
`search`, `merchant`, `category_id`, `txn_type`, `date_from`, `date_to`, `amount_min`, `amount_max`, `sort_by` (date|amount|merchant), `sort_dir` (asc|desc), `page`, `per_page`

**POST /api/transactions/bulk-delete body:**
```json
// By specific IDs:
{ "ids": [1, 2, 3] }

// All rows matching filters:
{ "all": true, "merchant": "Starbucks", "date_from": "2025-01-01" }
```

### Analytics
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/analytics/monthly` | Monthly spend/receive trend (`?months=12`) |
| `GET` | `/api/analytics/categories` | Category breakdown (`?date_from=&date_to=&txn_type=debit`) |
| `GET` | `/api/analytics/merchants` | Top merchants by spend (`?limit=20`) |
| `GET` | `/api/analytics/cashflow` | Income vs expense summary |

---

## Configuration

All settings are in `.env` (copy from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-key-change-me` | JWT signing key — **change in production** |
| `DATABASE_PATH` | `hisabkitab.db` | SQLite file path |
| `LLM_BACKEND` | `ollama` | `ollama` or `lmstudio` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llava` | Vision model name in Ollama |
| `LMSTUDIO_BASE_URL` | `http://localhost:1234` | LM Studio server URL |
| `LMSTUDIO_MODEL` | `local-model` | Model identifier in LM Studio |
| `WORKER_POLL_INTERVAL` | `2` | Seconds between job queue polls |
| `IMG_DPI` | `150` | PDF render resolution (higher = sharper but more tokens) |
| `IMG_JPEG_QUALITY` | `85` | JPEG compression quality (1–95; lower = smaller file) |
| `IMG_MAX_DIMENSION` | `1600` | Max image width/height in pixels before down-scaling |

### Image Optimisation Tuning

The pipeline renders bank statement pages to **grayscale JPEG** at **150 DPI**, which typically produces files **10–20× smaller** than the original colour PNG approach, while keeping text perfectly legible for the vision LLM.

If extraction quality suffers on dense statements, try increasing `IMG_DPI=200` or `IMG_JPEG_QUALITY=90`. Worker logs print per-page size info to help you tune:

```
[ImgOpt] page 1: 1237×1600px, 98 KB (grayscale JPEG q85)
```

---

## Default Categories

The database is seeded with 12 system-wide categories that the LLM uses for auto-labelling:

| # | Name | Icon |
|---|---|---|
| 1 | Groceries | 🛒 |
| 2 | Dining | 🍽️ |
| 3 | Transport | 🚗 |
| 4 | Shopping | 🛍️ |
| 5 | Bills & Utilities | 💡 |
| 6 | Entertainment | 🎬 |
| 7 | Health | 🏥 |
| 8 | Travel | ✈️ |
| 9 | Education | 📚 |
| 10 | Income | 💰 |
| 11 | Transfer | 🔄 |
| 12 | Other | 📦 |

---

## Tech Stack

- **Backend**: Flask 3, SQLite (WAL mode), PyJWT, PyMuPDF, requests
- **Frontend**: Vanilla HTML/CSS/JS, dark theme, no framework
- **Vision LLM**: Ollama or LM Studio — pluggable adapter pattern
- **Auth**: Email/password with JWT tokens (per-user data isolation)
- **Background jobs**: In-app daemon thread + SQLite `import_jobs` table (no Redis/Celery)
