"""Discretionary-spend forecasting (direct multi-horizon gradient boosting + quantile bands),
combined with deterministic recurring bills/income into a cash-flow and balance forecast."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

from .recurring import RecurringItem, add_keys, detect, project

MAX_H = 60        # longest supported forecast horizon (days)
MIN_HIST = 28     # days of history required before a forecast origin
Z80 = 1.2816      # z-score for an 80% interval

FEATURES = ["h", "dow", "dom", "week_of_month", "is_weekend", "days_to_month_end",
            "salary_cycle_pos", "roll7", "roll14", "roll30", "std30", "same_dow_4w", "trend_ratio"]
FEATURE_LABELS = {
    "h": "Forecast distance (days ahead)", "dow": "Day of week", "dom": "Day of month", "month": "Month",
    "week_of_month": "Week of month", "is_weekend": "Weekend", "days_to_month_end": "Days to month end",
    "salary_cycle_pos": "Position in salary cycle", "roll7": "7-day avg spend", "roll14": "14-day avg spend",
    "roll30": "30-day avg spend", "std30": "30-day spend volatility", "same_dow_4w": "Same weekday, last 4 weeks",
    "trend_ratio": "Recent vs 30-day trend",
}


def _build_rows(vals: np.ndarray, dates: list[date], origins: list[int], horizon: int, salary_dom: int):
    s = pd.Series(vals)
    r7 = s.rolling(7, min_periods=1).mean().values
    r14 = s.rolling(14, min_periods=1).mean().values
    r30 = s.rolling(30, min_periods=1).mean().values
    sd30 = s.rolling(30, min_periods=2).std().fillna(0).values
    n = len(vals)
    rows, ys, meta = [], [], []
    for o in origins:
        od = dates[o]
        for h in range(1, horizon + 1):
            d = od + timedelta(days=h)
            tw = d.weekday()
            off = (od.weekday() - tw) % 7
            idxs = [o - off - 7 * j for j in range(4) if o - off - 7 * j >= 0]
            sdow = float(vals[idxs].mean()) if idxs else float(r30[o])
            dim = calendar.monthrange(d.year, d.month)[1]
            rows.append([h, tw, d.day, (d.day - 1) // 7, int(tw >= 5), dim - d.day,
                         (d.day - salary_dom) % 31, r7[o], r14[o], r30[o], sd30[o], sdow,
                         r7[o] / (r30[o] + 1.0)])
            ys.append(vals[o + h] if o + h < n else np.nan)
            meta.append((o, h))
    return pd.DataFrame(rows, columns=FEATURES), np.array(ys, dtype=float), meta


def _same_dow(vals: np.ndarray, dates: list[date], o: int, target: date) -> float:
    off = (dates[o].weekday() - target.weekday()) % 7
    idxs = [o - off - 7 * j for j in range(4) if o - off - 7 * j >= 0]
    return float(vals[idxs].mean()) if idxs else float(vals[max(0, o - 29): o + 1].mean())


class BaselineModel:
    """Cold-start model: blend of 28-day moving average and same-weekday seasonal naive."""

    kind = "baseline"
    importances: list[dict] = []

    def fit(self, vals, dates, salary_dom):
        return self

    def predict(self, vals, dates, horizon, origin=None) -> pd.DataFrame:
        o = len(vals) - 1 if origin is None else origin
        hist = vals[: o + 1]
        ma = float(hist[-28:].mean())
        recent = hist[-90:]
        lo, hi = float(np.quantile(recent, 0.1)), float(np.quantile(recent, 0.9))
        mean = [0.5 * ma + 0.5 * _same_dow(vals, dates, o, dates[o] + timedelta(days=h)) for h in range(1, horizon + 1)]
        mean = np.array(mean)
        return pd.DataFrame({"mean": mean, "q10": np.minimum(lo, mean), "q90": np.maximum(hi, mean)})


class GBModel:
    """Gradient-boosting mean model + two quantile models (10th/90th percentile)."""

    kind = "gradient_boosting"

    def __init__(self):
        self.salary_dom = 1
        self.importances: list[dict] = []

    def _gbr(self, **kw):
        return GradientBoostingRegressor(n_estimators=120, max_depth=3, learning_rate=0.06, subsample=0.8,
                                         min_samples_leaf=20, random_state=42, **kw)

    def fit(self, vals, dates, salary_dom):
        self.salary_dom = salary_dom
        origins = list(range(MIN_HIST, len(vals) - 1, 2))
        X, y, _ = _build_rows(vals, dates, origins, MAX_H, salary_dom)
        m = ~np.isnan(y)
        X, y = X[m], y[m]
        self.mean = self._gbr(loss="squared_error").fit(X, y)
        self.q10 = self._gbr(loss="quantile", alpha=0.1).fit(X, y)
        self.q90 = self._gbr(loss="quantile", alpha=0.9).fit(X, y)
        imp = sorted(zip(FEATURES, self.mean.feature_importances_), key=lambda t: -t[1])
        self.importances = [{"feature": f, "label": FEATURE_LABELS[f], "importance": round(float(v), 4)}
                            for f, v in imp]
        return self

    def predict(self, vals, dates, horizon, origin=None) -> pd.DataFrame:
        o = len(vals) - 1 if origin is None else origin
        X, _, _ = _build_rows(vals[: o + 1], dates[: o + 1], [o], horizon, self.salary_dom)
        mean = np.clip(self.mean.predict(X), 0, None)
        q10 = np.clip(self.q10.predict(X), 0, None)
        q90 = np.clip(self.q90.predict(X), 0, None)
        return pd.DataFrame({"mean": mean, "q10": np.minimum(q10, mean), "q90": np.maximum(q90, mean)})


def make_model(vals: np.ndarray, dates: list[date], salary_dom: int):
    """Cold-start strategy: tiny histories get the transparent baseline."""
    if len(vals) < 90 or int((vals > 0).sum()) < 25:
        return BaselineModel().fit(vals, dates, salary_dom)
    return GBModel().fit(vals, dates, salary_dom)


# ---------------------------------------------------------------- history helpers
def date_range(start: date, n: int) -> list[date]:
    return [start + timedelta(days=i) for i in range(n)]


def salary_day(items: list[RecurringItem]) -> int:
    inc = [i for i in items if i.type == "income" and i.period == "monthly"]
    return max(inc, key=lambda i: i.amount).dom if inc else 1


def daily_series(df: pd.DataFrame, keys: set[str], start: date, n: int) -> dict[str, np.ndarray]:
    """Dense daily arrays: all/discretionary expenses and all/irregular income."""
    d = add_keys(df)
    idx = pd.date_range(start, periods=n, freq="D")
    rec = d["key"].isin(keys)

    def agg(mask):
        s = d[mask].groupby(d["date"].dt.normalize())["amount"].sum()
        s.index = pd.DatetimeIndex(s.index).as_unit("ns")
        return s.reindex(idx.as_unit("ns"), fill_value=0.0).values.astype(float)

    exp, inc = d["type"] == "expense", d["type"] == "income"
    return {"exp_all": agg(exp), "inc_all": agg(inc), "disc": agg(exp & ~rec), "inc_irr": agg(inc & ~rec)}


_CACHE: dict[int, tuple] = {}


def get_model(user_id: int, signature: tuple, vals, dates, salary_dom):
    hit = _CACHE.get(user_id)
    if hit and hit[0] == signature:
        return hit[1]
    model = make_model(vals, dates, salary_dom)
    _CACHE[user_id] = (signature, model)
    return model


def clear_cache(user_id: int):
    _CACHE.pop(user_id, None)


# ---------------------------------------------------------------- full forecast
def build_forecast(df: pd.DataFrame, user_id: int, opening_balance: float, horizon: int = 30,
                   extras: list | None = None) -> dict:
    if df.empty:
        raise ValueError("Add some transactions first.")
    horizon = max(7, min(int(horizon), MAX_H))
    start = df["date"].min().date()
    as_of = df["date"].max().date()
    n = (as_of - start).days + 1
    dates = date_range(start, n)

    items = detect(df)
    keys = {i.key for i in items}
    s = daily_series(df, keys, start, n)
    sal = salary_day(items)
    signature = (len(df), as_of, round(float(df["amount"].sum()), 2))
    model = get_model(user_id, signature, s["disc"], dates, sal)
    pred = model.predict(s["disc"], dates, horizon)  # origin = last day

    f_start, f_end = as_of + timedelta(days=1), as_of + timedelta(days=horizon)
    fdates = date_range(f_start, horizon)
    bills = np.zeros(horizon)
    rec_inc = np.zeros(horizon)
    due: list[dict] = []
    for it in items:
        for dt in project(it, f_start, f_end):
            i = (dt - f_start).days
            if it.type == "expense":
                bills[i] += it.amount
                due.append({"date": dt.isoformat(), "label": it.label, "amount": round(it.amount, 2),
                            "category": it.category})
            else:
                rec_inc[i] += it.amount
    irr_mean = float(s["inc_irr"][-90:].mean())
    planned = np.zeros(horizon)
    for e in extras or []:
        i = (e.date - f_start).days
        if 0 <= i < horizon:
            planned[i] += e.amount

    income = rec_inc + irr_mean
    disc = pred["mean"].values
    net = income - bills - disc - planned
    current = opening_balance + float(s["inc_all"].sum() - s["exp_all"].sum())
    bal = current + np.cumsum(net)
    sigma_d = np.maximum((pred["q90"].values - pred["q10"].values) / (2 * Z80), 1.0)
    band = Z80 * np.sqrt(np.cumsum(sigma_d ** 2))

    daily = [{
        "date": fdates[i].isoformat(), "income": round(float(income[i]), 2),
        "recurring_bills": round(float(bills[i]), 2), "discretionary": round(float(disc[i]), 2),
        "discretionary_low": round(float(pred["q10"].values[i]), 2),
        "discretionary_high": round(float(pred["q90"].values[i]), 2),
        "planned": round(float(planned[i]), 2), "net": round(float(net[i]), 2),
        "balance": round(float(bal[i]), 2), "balance_low": round(float(bal[i] - band[i]), 2),
        "balance_high": round(float(bal[i] + band[i]), 2),
    } for i in range(horizon)]

    due.sort(key=lambda r: r["date"])
    return {
        "as_of": as_of.isoformat(), "horizon": horizon, "model": model.kind, "current_balance": round(current, 2),
        "daily": daily, "upcoming_bills": due, "recurring": [i.to_dict() for i in items],
        "drivers": model.importances[:6],
        "summary": {
            "expected_balance": daily[-1]["balance"], "range_low": daily[-1]["balance_low"],
            "range_high": daily[-1]["balance_high"], "total_income": round(float(income.sum()), 2),
            "total_recurring_bills": round(float(bills.sum()), 2),
            "total_discretionary": round(float(disc.sum()), 2), "total_planned": round(float(planned.sum()), 2),
        },
    }
