"""Monthly expense forecasting from the authenticated user's transaction history."""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor


def monthly_expenses(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["month", "income", "expense"])
    rows = df.copy()
    rows["month"] = pd.to_datetime(rows["date"]).dt.to_period("M").dt.to_timestamp()
    monthly = rows.pivot_table(index="month", columns="type", values="amount", aggfunc="sum", fill_value=0)
    for col in ("income", "expense"):
        if col not in monthly:
            monthly[col] = 0.0
    # Fill calendar gaps so lag features represent consecutive months.
    idx = pd.date_range(monthly.index.min(), monthly.index.max(), freq="MS")
    monthly = monthly.reindex(idx, fill_value=0).rename_axis("month").reset_index()
    return monthly[["month", "income", "expense"]]


def _features(monthly: pd.DataFrame):
    values = monthly["expense"].to_numpy(dtype=float)
    X, y = [], []
    for i in range(3, len(values)):
        X.append([values[i-1], values[i-2], values[i-3], monthly.loc[i, "month"].month])
        y.append(values[i])
    return np.asarray(X), np.asarray(y)


def forecast(df: pd.DataFrame) -> dict:
    monthly = monthly_expenses(df)
    if len(monthly) < 4:
        return {"available": False, "model": None, "message": "Add at least four months of transactions to build a monthly forecast.", "predicted_expenses": None, "estimated_savings": None, "history": [], "categories": [], "mae": None, "evaluation": []}
    X, y = _features(monthly)
    trained = len(y) >= 6
    evaluation, mae = [], None
    if trained:
        split = max(1, int(len(y) * 0.8))
        if split < len(y):
            model_test = RandomForestRegressor(n_estimators=100, min_samples_leaf=1, random_state=42)
            model_test.fit(X[:split], y[:split])
            test_predictions = np.maximum(0, model_test.predict(X[split:]))
            actuals = y[split:]
            mae = float(np.mean(np.abs(actuals - test_predictions)))
            eval_months = monthly["month"].iloc[split + 3:]
            evaluation = [{"month": month.strftime("%Y-%m"), "actual": round(float(a), 2), "predicted": round(float(p), 2)} for month, a, p in zip(eval_months, actuals, test_predictions)]
        model = RandomForestRegressor(n_estimators=100, min_samples_leaf=1, random_state=42)
        model.fit(X, y)
        next_month = monthly.iloc[-1]["month"] + pd.offsets.MonthBegin(1)
        next_x = np.asarray([[monthly.iloc[-1]["expense"], monthly.iloc[-2]["expense"], monthly.iloc[-3]["expense"], next_month.month]])
        predicted = max(0.0, float(model.predict(next_x)[0]))
        model_name = "Random Forest regression"
        message = "Trained on this account's monthly expenses using the previous three months and calendar month."
    else:
        # Transparent baseline only; do not label a short history as machine learning.
        predicted = float(monthly["expense"].tail(3).mean())
        model_name = "Baseline estimate"
        message = "A machine-learning forecast needs at least nine months of records. This estimate is the average of the latest three months."
    income = float(monthly.iloc[-1]["income"])
    expense_rows = df[df["type"] == "expense"].copy()
    categories = []
    if not expense_rows.empty:
        cat = expense_rows.groupby("category")["amount"].sum().sort_values(ascending=False)
        categories = [{"category": k, "amount": round(float(v), 2)} for k, v in cat.items()]
    history = [{"month": r.month.strftime("%Y-%m"), "income": round(float(r.income), 2), "expense": round(float(r.expense), 2)} for r in monthly.itertuples()]
    return {"available": True, "model": model_name, "message": message, "predicted_expenses": round(predicted, 2), "expected_income": round(income, 2), "estimated_savings": round(income - predicted, 2), "history": history, "categories": categories, "mae": round(mae, 2) if mae is not None else None, "evaluation": evaluation}
