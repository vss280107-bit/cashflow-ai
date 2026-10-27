# CashFlow AI

CashFlow AI is a small personal-finance application built as a college machine-learning project. It stores transactions per account, summarizes monthly income and expenses, and uses a scikit-learn model to estimate next month's expenses when enough history is available.

## Problem and objectives

Students often record spending without a simple way to see where money goes or how upcoming expenses compare with income. This project demonstrates a full-stack way to collect transaction data, calculate useful summaries, and train and evaluate a regression model on historical monthly spending.

## Features

- Register, sign in, and sign out with hashed passwords and a protected API.
- Add, edit, list, filter, search, and delete income and expense transactions.
- Import CSV files and see row-level validation errors.
- Load synthetic demo transactions for an account.
- View monthly income, expenses, calculated net balance, category breakdown, and spending trends.
- Forecast next month's expenses and estimate savings from the latest recorded month's income.
- Compare held-out actual and predicted expenses and view MAE when enough monthly history exists.

## Technology

- Frontend: React 18, Vite, React Router, Recharts, plain CSS.
- Backend: Python, FastAPI, SQLAlchemy, Pydantic, pandas, NumPy, scikit-learn.
- Database: SQLite by default, persisted to `backend/cashflow.db` when started from the backend directory.
- Authentication: bcrypt password hashes and signed JWT bearer tokens. Transaction descriptions remain encrypted in SQLite, including records from the existing database.

No Docker, external AI service, paid API, PostgreSQL, or browser storage is needed. The browser stores only the login token; financial records are in SQLite.

## Architecture and folder structure

The React app calls `/api` through Vite's development proxy. FastAPI validates requests, resolves the bearer token to a user, and scopes transaction queries by that user's ID. SQLAlchemy persists users and transactions. The forecasting service aggregates each user's transactions into consecutive calendar months, trains a Random Forest regressor on lagged monthly expense totals, and returns a next-month estimate.

```text
backend/
  app/                 FastAPI app, models, routes, and forecasting service
  tests/               API and model workflow tests
  requirements.txt
  .env.example
frontend/
  src/pages/           Login, dashboard, transaction, and forecast screens
  src/api.js           API client
  package.json
  vite.config.js
```

## Requirements and setup

Use Python 3.10 or newer and Node.js 18 or newer. Start the backend and frontend in separate terminals.

### Backend (Windows PowerShell)

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

### Backend (macOS/Linux)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. Interactive API docs are at `http://localhost:8000/docs`. SQLite tables are created on first startup. Existing database files are not deleted or reset automatically.

### Frontend (Windows, macOS, or Linux)

In a second terminal from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, register, and start adding transactions. To inspect the optimized static build, run `npm run build` and optionally `npm run preview` from `frontend/`.

## Environment variables

Copy `backend/.env.example` to `backend/.env` for local configuration:

- `DATABASE_URL` defaults to `sqlite:///./cashflow.db` (relative to the backend working directory).
- `SECRET_KEY` should be replaced with a long random value for real deployments. The checked-in example is only a development placeholder.
- `CORS_ORIGINS` defaults to `http://localhost:5173`.

Keep `.env` out of version control. Keep `SECRET_KEY` stable when reusing an existing database because it also derives the development encryption key for transaction descriptions. Optionally set a stable `FIELD_ENCRYPTION_KEY` (Fernet key) instead. The example values are for local development only.

## Demo data

From the dashboard or Transactions page, choose **Load demo data**. The generated synthetic history covers roughly one year, making it useful for the charts and model demo. Loading demo data replaces that account's current transactions; this is clearly presented as a demo action.

## CSV import

Required columns are `date,amount`; optional columns are `type,category,description`.

```csv
date,amount,type,category,description
2026-01-05,250,expense,food,Cafe lunch
2026-01-10,32000,income,salary,Monthly stipend
```

Dates accept `YYYY-MM-DD`, `DD/MM/YYYY`, or `DD-MM-YYYY`. A negative amount implies an expense and is stored as a positive amount. Invalid rows are skipped and their row numbers and reasons are returned. Files must be UTF-8 encoded.

## Machine-learning workflow

1. Transactions are grouped into calendar months; missing months between the first and last record are filled with zero totals.
2. For each month from the fourth onward, features are the preceding three months' expense totals and the calendar month number. Each target is that month's total expense. These features only use earlier months, preventing future-data leakage.
3. With at least nine months of history (six supervised rows), a `RandomForestRegressor` trains on the user's own rows. It is retrained from current database data when a forecast is requested; it is not a pre-trained global model.
4. The next month's prediction uses the most recent three expense totals and the next calendar month.
5. The held-out evaluation reserves the latest 20% of supervised rows for testing, trains on the earlier rows, and reports mean absolute error (MAE) plus actual/predicted values.
6. With fewer than nine months, the app labels its output **Baseline estimate** and uses the average expense of the latest three months. It does not call that estimate machine learning. With fewer than four months, it explains that more history is needed.

The model is intentionally small and illustrative. Monthly totals hide within-month timing, zero-filled months may not mean true zero spending, and personal spending patterns can change. A random forest trained on one account's short history may generalize poorly. MAE is shown only when there are enough held-out observations.

## API overview

All endpoints are under `/api`; protected endpoints need `Authorization: Bearer <token>`.

- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- `GET|POST /transactions`, `PUT|DELETE /transactions/{id}`
- `GET /transactions/categories`, `POST /transactions/import`, `POST /transactions/demo`
- `GET /summary`, `GET /forecast`, `GET /model/evaluation`
- `GET /health`

## Tests

From `backend/` with its virtual environment active:

```bash
python -m pytest -q tests
```

The suite covers password hashing, registration/login, authenticated transaction operations, cross-user isolation, CSV row validation, demo data, monthly forecasts, and summaries.
