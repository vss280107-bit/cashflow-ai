"""Planning / alert engine: turns forecasts into risk periods, insights and suggestions."""
from __future__ import annotations

from datetime import timedelta

import pandas as pd

from .recurring import add_keys, detect

DISCLAIMER = "Estimates for planning support only. This is not investment or financial advice."


def inr(x: float) -> str:
    return f"₹{x:,.0f}"


def risk_periods(daily: list[dict], threshold: float) -> list[dict]:
    periods, cur = [], None
    for r in daily:
        level = "high" if r["balance"] < threshold else ("medium" if r["balance_low"] < threshold else None)
        if level:
            if cur is None:
                cur = {"start": r["date"], "end": r["date"], "severity": level, "min_balance": r["balance"],
                       "min_balance_low": r["balance_low"]}
            else:
                cur["end"] = r["date"]
                cur["min_balance"] = min(cur["min_balance"], r["balance"])
                cur["min_balance_low"] = min(cur["min_balance_low"], r["balance_low"])
                if level == "high":
                    cur["severity"] = "high"
        elif cur:
            periods.append(cur)
            cur = None
    if cur:
        periods.append(cur)
    for p in periods:
        p["message"] = (
            f"Expected balance may fall to {inr(p['min_balance'])} (worst case {inr(p['min_balance_low'])}) "
            f"between {p['start']} and {p['end']}, below your {inr(threshold)} buffer."
            if p["severity"] == "high" else
            f"Worst case dips to {inr(p['min_balance_low'])} between {p['start']} and {p['end']}; "
            f"the expected path stays above your buffer.")
    return periods


def headroom(daily: list[dict], threshold: float) -> dict:
    """Extra spending absorbable over the horizon without breaching the buffer in the conservative case."""
    room = max(0.0, min(r["balance_low"] for r in daily) - threshold)
    return {"amount": round(room, 2), "per_day": round(room / len(daily), 2)}


def category_insights(df: pd.DataFrame, as_of) -> list[dict]:
    """Last 30 days vs the average of the three prior 30-day windows, discretionary categories only."""
    out = []
    if df.empty:
        return out
    keys = {i.key for i in detect(df)}
    d = add_keys(df)
    d = d[(d["type"] == "expense") & ~d["key"].isin(keys)]
    as_ts = pd.Timestamp(as_of)
    recent = d[d["date"] > as_ts - timedelta(days=30)].groupby("category")["amount"].sum()
    prior = d[(d["date"] <= as_ts - timedelta(days=30)) & (d["date"] > as_ts - timedelta(days=120))]
    base = prior.groupby("category")["amount"].sum() / 3.0
    for cat in recent.index:
        b = float(base.get(cat, 0.0))
        r = float(recent[cat])
        if b >= 500 and abs(r - b) / b >= 0.15:
            pct = (r - b) / b * 100
            out.append({"type": "spending", "category": cat, "change_pct": round(pct, 1), "recent": round(r, 2),
                        "baseline": round(b, 2),
                        "title": f"{cat.title()} spending is {abs(pct):.0f}% {'higher' if pct > 0 else 'lower'} than usual",
                        "detail": f"{inr(r)} in the last 30 days vs a typical {inr(b)}."})
    out.sort(key=lambda x: -abs(x["change_pct"]))
    return out[:4]


def build_plan(fc: dict, df: pd.DataFrame, threshold: float) -> dict:
    daily, summ = fc["daily"], fc["summary"]
    risks = risk_periods(daily, threshold)
    room = headroom(daily, threshold)
    insights = category_insights(df, fc["as_of"])

    bills = fc["upcoming_bills"]
    next7 = [b for b in bills if b["date"] <= daily[min(6, len(daily) - 1)]["date"]]
    if next7:
        insights.append({"type": "bills", "title": f"{len(next7)} recurring bill(s) due this week",
                         "detail": f"{inr(sum(b['amount'] for b in next7))}: " + ", ".join(b["label"] for b in next7[:4]) + "."})
    # heaviest week-of-month for bills
    if bills:
        wk = {}
        for b in bills:
            day = int(b["date"][-2:])
            wk[(day - 1) // 7] = wk.get((day - 1) // 7, 0) + b["amount"]
        top, amt = max(wk.items(), key=lambda kv: kv[1])
        if amt >= 0.4 * sum(wk.values()) and len(bills) >= 3:
            insights.append({"type": "bills", "title": "Heavy outflow window",
                             "detail": f"Days {top * 7 + 1}–{min(top * 7 + 7, 31)} of the month carry {inr(amt)} of recurring bills."})
    net = summ["total_income"] - summ["total_recurring_bills"] - summ["total_discretionary"] - summ["total_planned"]
    insights.append({"type": "forecast", "title": f"Expected net cash flow: {inr(net)}",
                     "detail": f"Over {fc['horizon']} days: income {inr(summ['total_income'])}, bills {inr(summ['total_recurring_bills'])}, "
                               f"flexible spending {inr(summ['total_discretionary'])}."})

    tips = []
    if risks and risks[0]["severity"] == "high":
        tips.append(f"Keep flexible spending low before {risks[0]['start']}, or move non-urgent purchases after your next income.")
    elif risks:
        tips.append(f"Your worst case dips below your buffer around {risks[0]['start']}; hold off on large optional purchases until then.")
    if room["amount"] > 0:
        tips.append(f"You can absorb about {inr(room['amount'])} of extra spending in the next {fc['horizon']} days "
                    f"(≈ {inr(room['per_day'])}/day) and still stay above your {inr(threshold)} buffer in the conservative case.")
    else:
        tips.append("There is no spending headroom in the conservative case. Consider trimming discretionary spending.")
    over = [i for i in insights if i["type"] == "spending" and i["change_pct"] > 0]
    if over:
        o = over[0]
        tips.append(f"Bringing {o['category']} back to its usual level would free about {inr(o['recent'] - o['baseline'])} per month.")
    return {"risk_periods": risks, "headroom": room, "insights": insights, "suggestions": tips, "disclaimer": DISCLAIMER}
