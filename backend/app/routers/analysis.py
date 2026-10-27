from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Transaction, User
from ..services.forecaster import forecast, monthly_expenses
import pandas as pd

router = APIRouter(prefix="/api", tags=["analysis"])


def _rows(db: Session, user_id: int) -> pd.DataFrame:
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.date).all()
    return pd.DataFrame([{"date": t.date, "amount": t.amount, "type": t.type, "category": t.category} for t in transactions], columns=["date", "amount", "type", "category"])


@router.get("/summary")
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    df = _rows(db, user.id)
    if df.empty:
        return {"monthly": [], "categories": [], "insights": []}
    monthly = monthly_expenses(df)
    expenses = df[df["type"] == "expense"]
    category_totals = expenses.groupby("category")["amount"].sum().sort_values(ascending=False)
    categories = [{"category": name, "amount": round(float(amount), 2)} for name, amount in category_totals.items()]
    last = monthly.iloc[-1]
    previous = monthly.iloc[-2] if len(monthly) > 1 else None
    insights = []
    if previous is not None and previous.expense > 0 and last.expense > previous.expense * 1.1:
        insights.append("Your expenses increased compared with last month.")
    if categories:
        insights.append(f"Your largest recorded expense category is {categories[0]['category']}.")
    return {"monthly": [{"month": r.month.strftime("%Y-%m"), "income": round(float(r.income), 2), "expense": round(float(r.expense), 2)} for r in monthly.itertuples()], "categories": categories, "insights": insights}


@router.get("/forecast")
def get_forecast(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return forecast(_rows(db, user.id))


@router.get("/model/evaluation")
def model_evaluation(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = forecast(_rows(db, user.id))
    if not result["available"]:
        return {"available": False, "reason": result["message"]}
    if result["mae"] is None:
        return {"available": False, "reason": "Add at least ten months of monthly records to evaluate a time-based test split."}
    return {"available": True, "mae": result["mae"], "evaluation": result["evaluation"], "model": result["model"]}
