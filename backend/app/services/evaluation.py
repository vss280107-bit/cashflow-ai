"""Time-based train / validation / test evaluation with rolling-origin backtesting."""
from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from .forecaster import BaselineModel, _same_dow, daily_series, date_range, make_model, salary_day
from .recurring import detect, project

MIN_DAYS = 150


def _mae(a, p): return float(np.mean(np.abs(np.asarray(a) - np.asarray(p)))) if len(a) else None
def _rmse(a, p): return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(p)) ** 2))) if len(a) else None


def _wmape(actual_blocks, pred_blocks):
    a, p = np.asarray(actual_blocks), np.asarray(pred_blocks)
    m = a > 0
    return float(np.mean(np.abs(a[m] - p[m]) / a[m]) * 100) if m.any() else None


def _round(d: dict) -> dict:
    return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in d.items()}


def run_backtest(df: pd.DataFrame, opening_balance: float, threshold: float, horizon: int = 30, step: int = 3) -> dict:
    if df.empty:
        return {"available": False, "reason": "No transactions yet."}
    start, end = df["date"].min().date(), df["date"].max().date()
    n = (end - start).days + 1
    if n < MIN_DAYS:
        return {"available": False,
                "reason": f"Need at least {MIN_DAYS} days of history for a meaningful backtest (you have {n})."}
    dates = date_range(start, n)
    i_train, i_val = int(n * 0.70), int(n * 0.85)

    train_df = df[df["date"].dt.date <= dates[i_train - 1]]
    items = detect(train_df)                      # recurring detected on training data only
    keys = {i.key for i in items}
    s = daily_series(df, keys, start, n)
    sal = salary_day(items)

    model = make_model(s["disc"][:i_train], dates[:i_train], sal)
    naive = BaselineModel()

    # deterministic recurring flows projected from the training period
    rec_exp, rec_inc = np.zeros(n), np.zeros(n)
    for it in items:
        for dt in project(it, dates[i_train - 1] + timedelta(days=1), end):
            (rec_exp if it.type == "expense" else rec_inc)[(dt - start).days] += it.amount
    irr_mean = float(s["inc_irr"][:i_train][-90:].mean())
    net_actual = s["inc_all"] - s["exp_all"]
    bal_end_of_day = opening_balance + np.cumsum(net_actual)

    def evaluate(lo: int, hi: int) -> dict | None:
        origins = list(range(lo, hi - horizon, step))
        if not origins:
            return None
        A, P, N, M, Q10, Q90 = [], [], [], [], [], []
        wa, wp, wn = [], [], []
        inc_a, inc_p, inc_b, exp_a, exp_p, exp_b, net_a, net_p, net_b = ([] for _ in range(9))
        tp = fp = tn = fn = 0
        end_err_m, end_err_b = [], []
        for o in origins:
            sl = slice(o + 1, o + 1 + horizon)
            pr = model.predict(s["disc"], dates, horizon, origin=o)
            ma = float(s["disc"][max(0, o - 27): o + 1].mean())
            sn = np.array([_same_dow(s["disc"], dates, o, dates[o] + timedelta(days=h)) for h in range(1, horizon + 1)])
            act = s["disc"][sl]
            A += list(act); P += list(pr["mean"]); N += list(sn); M += [ma] * horizon
            Q10 += list(pr["q10"]); Q90 += list(pr["q90"])
            for w in range(4):
                b = slice(w * 7, w * 7 + 7)
                wa.append(act[b].sum()); wp.append(pr["mean"].values[b].sum()); wn.append(sn[b].sum())
            # income / expenses / net, model vs trailing-28-day-average baseline
            inc_pred = rec_inc[sl] + irr_mean
            exp_pred = rec_exp[sl] + pr["mean"].values
            inc_base = np.full(horizon, s["inc_all"][max(0, o - 27): o + 1].mean())
            exp_base = np.full(horizon, s["exp_all"][max(0, o - 27): o + 1].mean())
            inc_a += list(s["inc_all"][sl]); inc_p += list(inc_pred); inc_b += list(inc_base)
            exp_a += list(s["exp_all"][sl]); exp_p += list(exp_pred); exp_b += list(exp_base)
            net_a += list(net_actual[sl]); net_p += list(inc_pred - exp_pred); net_b += list(inc_base - exp_base)
            # low-balance detection
            b0 = bal_end_of_day[o]
            path_true = b0 + np.cumsum(net_actual[sl])
            path_pred = b0 + np.cumsum(inc_pred - exp_pred)
            path_base = b0 + np.cumsum(inc_base - exp_base)
            truth, pred = path_true.min() < threshold, path_pred.min() < threshold
            tp += truth and pred; fp += (not truth) and pred; fn += truth and (not pred); tn += (not truth) and (not pred)
            end_err_m.append(abs(path_true[-1] - path_pred[-1])); end_err_b.append(abs(path_true[-1] - path_base[-1]))
        cov = float(np.mean((np.array(A) >= np.array(Q10)) & (np.array(A) <= np.array(Q90))) * 100)
        total = tp + fp + fn + tn
        return {
            "origins": len(origins),
            "discretionary_daily": {
                "model": _round({"mae": _mae(A, P), "rmse": _rmse(A, P)}),
                "seasonal_naive": _round({"mae": _mae(A, N), "rmse": _rmse(A, N)}),
                "moving_average": _round({"mae": _mae(A, M), "rmse": _rmse(A, M)}),
            },
            "discretionary_weekly_mape": _round({"model": _wmape(wa, wp), "seasonal_naive": _wmape(wa, wn)}),
            "interval_coverage_80": round(cov, 1),
            "cash_flow_daily_mae": {
                "income": _round({"model": _mae(inc_a, inc_p), "baseline": _mae(inc_a, inc_b)}),
                "expenses": _round({"model": _mae(exp_a, exp_p), "baseline": _mae(exp_a, exp_b)}),
                "net": _round({"model": _mae(net_a, net_p), "baseline": _mae(net_a, net_b)}),
            },
            "ending_balance_mae": _round({"model": float(np.mean(end_err_m)), "baseline": float(np.mean(end_err_b))}),
            "low_balance_detection": {
                "threshold": threshold, "true_positive": int(tp), "false_positive": int(fp),
                "false_negative": int(fn), "true_negative": int(tn),
                "precision": round(tp / (tp + fp), 2) if (tp + fp) else None,
                "recall": round(tp / (tp + fn), 2) if (tp + fn) else None,
                "accuracy": round((tp + tn) / total, 2) if total else None,
            },
        }

    return {
        "available": True, "horizon": horizon, "model": model.kind,
        "split": {"train_days": i_train, "validation_days": i_val - i_train, "test_days": n - i_val,
                  "train_end": dates[i_train - 1].isoformat(), "validation_end": dates[i_val - 1].isoformat()},
        "validation": evaluate(i_train - 1, i_val),
        "test": evaluate(i_val - 1, n),
        "feature_importance": model.importances[:8],
        "recurring_detected": len(items),
        "note": "Frozen model trained on the first 70% of history; rolling-origin forecasts every "
                f"{step} days. Recurring bills are detected on training data only.",
    }
