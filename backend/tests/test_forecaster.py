from datetime import date, timedelta

import pandas as pd

from app.services.forecaster import forecast, monthly_expenses
from app.services.seed import generate_demo_transactions


def test_forecast_trains_random_forest_and_reports_time_split_mae():
    rows = generate_demo_transactions(end=date(2026, 10, 26), days=365, seed=23)
    frame = pd.DataFrame(rows)
    result = forecast(frame)
    assert result["available"] is True
    assert result["model"] == "Random Forest regression"
    assert result["predicted_expenses"] >= 0
    assert result["mae"] is not None
    assert result["evaluation"]


def test_short_history_is_labeled_as_a_baseline():
    rows = [
        {"date": date(2026, month, 5), "amount": amount, "type": "expense", "category": "food"}
        for month, amount in ((1, 100), (2, 200), (3, 300), (4, 400), (5, 500), (6, 600))
    ]
    result = forecast(pd.DataFrame(rows))
    assert result["available"] is True
    assert result["model"] == "Baseline estimate"
    assert result["mae"] is None
    assert result["predicted_expenses"] == 500


def test_month_aggregation_includes_missing_months_as_zero():
    rows = pd.DataFrame([
        {"date": date(2026, 1, 5), "amount": 100, "type": "expense"},
        {"date": date(2026, 3, 5), "amount": 300, "type": "expense"},
    ])
    monthly = monthly_expenses(rows)
    assert monthly["expense"].tolist() == [100, 0, 300]
