"""Synthetic but realistic demo data (stipend + rent + subscriptions + noisy daily spending)."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

import numpy as np


def generate_demo_transactions(end: date | None = None, days: int = 365, seed: int = 7) -> list[dict]:
    rng = np.random.default_rng(seed)
    end = end or date.today() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    out: list[dict] = []

    def add(d, amount, typ, cat, desc):
        out.append({"date": d, "amount": round(float(amount), 2), "type": typ, "category": cat, "description": desc})

    d = start
    while d <= end:
        dim = calendar.monthrange(d.year, d.month)[1]
        wk = d.weekday() >= 5
        cycle = 1.25 if d.day <= 7 else (0.85 if d.day >= 24 else 1.0)  # spend more right after payday
        festive = 1.5 if (d.month in (10, 11) and 8 <= d.day <= 20) else 1.0

        # fixed monthly flows
        if d.day == 1: add(d, 32000, "income", "salary", "Stipend - Acme Labs")
        if d.day == 3: add(d, 9500, "expense", "rent", "Rent - PG")
        if d.day == 5: add(d, 119, "expense", "entertainment", "Spotify")
        if d.day == 8: add(d, 799, "expense", "bills", "Broadband Airtel")
        if d.day == 12: add(d, 649, "expense", "entertainment", "Netflix")
        if d.day == 15: add(d, 299, "expense", "bills", "Mobile recharge Jio")
        if d.day == min(20, dim): add(d, rng.uniform(900, 1500), "expense", "bills", "Electricity bill")
        if d.day == 2: add(d, 1000, "expense", "health", "Gym membership")

        # irregular income
        if rng.random() < 0.025: add(d, rng.uniform(3000, 8000), "income", "freelance", "Freelance client payment")

        # discretionary spending
        if rng.random() < 0.85: add(d, rng.uniform(80, 450) * (1.4 if wk else 1) * cycle * festive, "expense", "food",
                                    str(rng.choice(["Swiggy", "Zomato", "Canteen lunch", "Cafe coffee", "Dinner"])))
        if rng.random() < 0.5: add(d, rng.uniform(30, 250), "expense", "transport", str(rng.choice(["Uber", "Metro card", "Rapido"])))
        if rng.random() < 0.12 * (1.6 if wk else 1): add(d, rng.uniform(300, 2500) * festive, "expense", "shopping",
                                                         str(rng.choice(["Amazon order", "Myntra", "Flipkart"])))
        if wk and rng.random() < 0.35: add(d, rng.uniform(200, 900), "expense", "entertainment", str(rng.choice(["Movie BookMyShow", "Gaming Steam", "Cafe hangout"])))
        if rng.random() < 0.02: add(d, rng.uniform(500, 2500), "expense", "education", "Udemy course")
        if rng.random() < 0.015: add(d, rng.uniform(300, 1500), "expense", "health", "Pharmacy")
        if rng.random() < 0.006: add(d, rng.uniform(3000, 9000), "expense", "travel", "Trip - MakeMyTrip")
        d += timedelta(days=1)
    return out
