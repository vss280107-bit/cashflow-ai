"""Recurring income / bill detection from transaction history."""
from __future__ import annotations

import calendar
import math
import re
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd


def normalize(desc: str) -> str:
    s = re.sub(r"[^a-z\s]", " ", (desc or "").lower())
    return " ".join([w for w in s.split() if len(w) > 1][:3])


def add_keys(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["key"] = df["description"].map(normalize) + "|" + df["type"]
    return df


@dataclass
class RecurringItem:
    key: str
    label: str
    type: str
    category: str
    period: str  # weekly | biweekly | monthly
    interval_days: int
    amount: float
    dom: int
    last_date: date
    count: int

    def to_dict(self) -> dict:
        return {
            "label": self.label, "type": self.type, "category": self.category, "period": self.period,
            "amount": round(self.amount, 2), "day_of_month": self.dom,
            "last_date": self.last_date.isoformat(), "occurrences": self.count,
        }


# name: (days, gap tolerance, max amount coefficient of variation)
PERIODS = {"weekly": (7, 1, 0.25), "biweekly": (14, 2, 0.25), "monthly": (30, 4, 0.40)}


def detect(df: pd.DataFrame, min_occurrences: int = 3) -> list[RecurringItem]:
    if df.empty:
        return []
    d = add_keys(df)
    end = d["date"].max()
    items: list[RecurringItem] = []
    for key, g in d.groupby("key"):
        if key.startswith("|"):
            continue
        by_day = g.groupby(g["date"].dt.normalize())["amount"].sum()
        if len(by_day) < min_occurrences:
            continue
        dates = by_day.index
        gaps = np.diff(dates.values).astype("timedelta64[D]").astype(int)
        med = float(np.median(gaps))
        for name, (p, tol, cv_max) in PERIODS.items():
            if abs(med - p) > tol:
                continue
            regular = float(np.mean(np.abs(gaps - p) <= tol))
            amounts = by_day.values
            cv = float(np.std(amounts) / np.mean(amounts)) if np.mean(amounts) > 0 else 9
            active = (end - dates[-1]).days <= 2 * p
            if regular >= 0.7 and cv <= cv_max and active:
                latest = g.sort_values("date").iloc[-1]
                cats = g["category"].mode()
                items.append(RecurringItem(
                    key=key, label=str(latest["description"]).strip() or key.split("|")[0].title(),
                    type=str(latest["type"]), category=str(cats.iloc[0]) if len(cats) else "other",
                    period=name, interval_days=p, amount=float(np.median(amounts[-3:])),
                    dom=int(np.median([x.day for x in dates])), last_date=dates[-1].date(), count=len(dates),
                ))
            break
    return items


def project(item: RecurringItem, start: date, end: date) -> list[date]:
    """Future due dates of a recurring item inside [start, end] (always after its last seen date)."""
    out: list[date] = []
    if item.period == "monthly":
        y, m = start.year, start.month
        while date(y, m, 1) <= end:
            dt = date(y, m, min(item.dom, calendar.monthrange(y, m)[1]))
            if start <= dt <= end and dt > item.last_date:
                out.append(dt)
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    else:
        step = item.interval_days
        k = max(1, math.ceil((start - item.last_date).days / step))
        dt = item.last_date + timedelta(days=step * k)
        while dt <= end:
            out.append(dt)
            dt += timedelta(days=step)
    return out
