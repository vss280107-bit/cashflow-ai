# CashFlow AI — Personal Finance Cash-Flow Forecasting & Planning

Full-stack implementation of the *Personal Finance Cash-Flow Forecasting & Planning System* ML project.
It learns a user's spending patterns, forecasts income / expenses / balance with uncertainty ranges,
detects upcoming cash-shortage periods and turns the forecast into planning advice.

| Layer | Tech |
|---|---|
| Frontend | React 18 + Vite, Recharts, React Router |
| Backend | Python, FastAPI, SQLAlchemy, JWT auth (bcrypt) |
| ML | pandas, NumPy, scikit-learn (gradient boosting + quantile regression) |
| Database | SQLite by default, PostgreSQL via `DATABASE_URL`; descriptions encrypted at rest (Fernet) |
| Deploy | Docker Compose (Postgres + API + nginx) |

## Run locally

```bash
# 1) Backend  (http://localhost:8000, docs at /docs)
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # set SECRET_KEY
uvicorn app.main:app --reload

# 2) Frontend (http://localhost:5173, proxies /api -> :8000)
cd frontend
npm install
npm run dev
```
Register an account, then click **Load demo data** (a year of synthetic stipend, rent, subscriptions and noisy daily spending).

Or everything at once: `docker compose up --build` → http://localhost:8080

Tests: `cd backend && python -m pytest -q tests`

## How it maps to the project deck

| Deck item | Where |
|---|---|
| Transaction input (manual / import) | `routers/transactions.py` (form, CSV import) |
| Cleaning & categorisation | `services/categorizer.py` (keyword rules; swap for an ML classifier) |
| Recurring-pattern extraction | `services/recurring.py` (weekly / bi-weekly / monthly detection, projection) |
| Feature engineering | `services/forecaster.py::_build_rows` — calendar, salary-cycle position, rolling 7/14/30-day stats, same-weekday and trend features |
| Baseline | `BaselineModel` (moving average + seasonal naive); also the **cold-start** model for short histories |
| Main model | `GBModel` — direct multi-horizon `GradientBoostingRegressor` (mean) + two quantile models (10th/90th) |
| Risk estimation | 80% balance band: daily spread from the quantile models, accumulated as √Σσ² |
| Explainability | feature importances + "what drives the forecast" panel |
| Planning engine | `services/planner.py` — risk periods, spending headroom, insights, suggestions |
| What-if simulation | `POST /api/forecast/what-if` + Planner page |
| Evaluation | `services/evaluation.py` — time-based 70/15/15 split, rolling-origin backtest, MAE/RMSE/MAPE, income vs expenses vs net, interval coverage, low-balance precision/recall |

### Forecast design
Spending is split into **recurring** items (rent, subscriptions, salary: detected, then projected on their due dates
deterministically) and **discretionary** spending (modelled by gradient boosting). Balance = current balance + cumulative
(income − bills − discretionary − planned). Recurring detection and model training use only data available at the
forecast origin during backtests, so no future information leaks into evaluation.

### Security & privacy
Passwords are bcrypt-hashed, API access uses JWT bearer tokens, every query is scoped to the authenticated user and
transaction descriptions are encrypted at rest. Set strong `SECRET_KEY` / `FIELD_ENCRYPTION_KEY` values in production
and serve over HTTPS.

## API (all under `/api`)
`POST /auth/register|login` · `GET|PATCH /auth/me` · `GET|POST /transactions` · `PUT|DELETE /transactions/{id}` ·
`POST /transactions/import` (CSV) · `POST /transactions/demo` · `GET /forecast?horizon=` · `POST /forecast/what-if` ·
`GET /summary` · `GET /model/evaluation`

## Known limitations / next steps
- Models are cached in-process per user; use a job queue + model store for multi-worker deployments.
- Backtests need ~150 days of history; with less, the app shows the baseline forecast only.
- Future scope from the deck: bank-statement import, anomaly detection, goal planning, on-device modelling.

*Estimates are for planning support only and are not investment or financial advice.*
