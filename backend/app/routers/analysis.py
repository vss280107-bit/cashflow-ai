from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import WhatIfIn
from ..services import evaluation, forecaster, planner
from ..services.data import load_df
from ..services.recurring import add_keys, detect

router = APIRouter(prefix="/api", tags=["analysis"])


def _forecast(user: User, db: Session, horizon: int, extras=None):
    df = load_df(db, user.id)
    if df.empty:
        raise HTTPException(409, "No transactions yet. Add some or load the demo data.")
    fc = forecaster.build_forecast(df, user.id, user.opening_balance, horizon, extras)
    return df, fc


@router.get("/forecast")
def get_forecast(horizon: int = Query(30, ge=7, le=60), user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    df, fc = _forecast(user, db, horizon)
    return {**fc, "threshold": user.low_balance_threshold, "plan": planner.build_plan(fc, df, user.low_balance_threshold)}


@router.post("/forecast/what-if")
def what_if(body: WhatIfIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    df, base = _forecast(user, db, body.horizon)
    _, scen = _forecast(user, db, body.horizon, body.expenses)
    th = user.low_balance_threshold
    plan = planner.build_plan(scen, df, th)
    breach = next((r["date"] for r in scen["daily"] if r["balance"] < th), None)
    breach_low = next((r["date"] for r in scen["daily"] if r["balance_low"] < th), None)
    total = sum(e.amount for e in body.expenses)
    return {
        "baseline": base["daily"], "scenario": scen["daily"], "threshold": th,
        "total_planned": round(total, 2),
        "end_balance_change": round(scen["summary"]["expected_balance"] - base["summary"]["expected_balance"], 2),
        "scenario_end_balance": scen["summary"]["expected_balance"],
        "first_breach_expected": breach, "first_breach_worst_case": breach_low,
        "verdict": ("unsafe" if breach else "risky" if breach_low else "safe"),
        "headroom_after": plan["headroom"], "risk_periods": plan["risk_periods"],
        "disclaimer": planner.DISCLAIMER,
    }


@router.get("/summary")
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    df = load_df(db, user.id)
    if df.empty:
        return {"monthly": [], "categories": [], "recurring": []}
    monthly = (df.assign(month=df["date"].dt.strftime("%Y-%m")).pivot_table(
        index="month", columns="type", values="amount", aggfunc="sum", fill_value=0).reset_index())
    for c in ("income", "expense"):
        if c not in monthly: monthly[c] = 0.0
    last90 = df[(df["type"] == "expense") & (df["date"] > df["date"].max() - __import__("pandas").Timedelta(days=90))]
    cats = last90.groupby("category")["amount"].sum().sort_values(ascending=False)
    return {
        "monthly": [{"month": r.month, "income": round(r.income, 2), "expense": round(r.expense, 2)}
                    for r in monthly.itertuples()],
        "categories": [{"category": k, "amount": round(float(v), 2)} for k, v in cats.items()],
        "recurring": [i.to_dict() for i in detect(df)],
    }


@router.get("/model/evaluation")
def model_evaluation(horizon: int = Query(30, ge=7, le=45), user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    df = load_df(db, user.id)
    return evaluation.run_backtest(df, user.opening_balance, user.low_balance_threshold, horizon)
