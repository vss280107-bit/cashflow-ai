import math
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import MonthlyBudget, Transaction, User
from ..schemas import BudgetIn

router = APIRouter(prefix="/api/budget", tags=["budget"])


def _month(value: str | None) -> tuple[str, date, date]:
    value = value or date.today().strftime("%Y-%m")
    try:
        first = date.fromisoformat(f"{value}-01")
    except ValueError:
        raise HTTPException(422, "Month must use YYYY-MM format") from None
    if first.strftime("%Y-%m") != value:
        raise HTTPException(422, "Month must use YYYY-MM format")
    following = date(first.year + (first.month == 12), 1 if first.month == 12 else first.month + 1, 1)
    return value, first, following


def calculate_budget_state(budget_amount: float | None, amount_spent: float, month: str) -> dict:
    """Calculate a safe monthly summary, including explicit zero/invalid budget state."""
    try:
        spent = float(amount_spent)
        if not math.isfinite(spent) or spent < 0:
            spent = 0.0
    except (TypeError, ValueError):
        spent = 0.0
    spent = round(spent, 2)

    try:
        budget = float(budget_amount)
        if not math.isfinite(budget) or budget <= 0:
            budget = 0.0
    except (TypeError, ValueError):
        budget = 0.0
    if budget == 0:
        return {
            "month": month,
            "budget_amount": None,
            "amount_spent": spent,
            "remaining_balance": None,
            "percentage_used": None,
            "status": "not_set",
        }

    remaining = round(budget - spent, 2)
    raw_percentage = spent / budget * 100
    percentage_used = round(raw_percentage, 2)
    status = "exceeded" if raw_percentage >= 100 else "warning" if raw_percentage >= 80 else "on_track"
    return {
        "month": month,
        "budget_amount": round(budget, 2),
        "amount_spent": spent,
        "remaining_balance": remaining,
        "percentage_used": percentage_used,
        "status": status,
    }


def _budget_state(user: User, db: Session, month: str | None = None) -> dict:
    selected_month, first, following = _month(month)
    amounts = (
        db.query(Transaction.amount)
        .filter(
            Transaction.user_id == user.id,
            Transaction.type == "expense",
            Transaction.date >= first,
            Transaction.date < following,
        )
        .all()
    )
    valid_amounts = []
    for (amount,) in amounts:
        try:
            value = float(amount)
        except (TypeError, ValueError):
            continue
        if math.isfinite(value) and value > 0:
            valid_amounts.append(value)

    saved_budget = db.query(MonthlyBudget).filter_by(user_id=user.id, month=selected_month).first()
    # Retain the old single-budget value as this month's limit until a month-specific value is saved.
    legacy_budget = user.monthly_budget if selected_month == date.today().strftime("%Y-%m") else 0.0
    budget_amount = saved_budget.amount if saved_budget else legacy_budget
    return calculate_budget_state(budget_amount, sum(valid_amounts), selected_month)


@router.get("")
def get_budget(
    month: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _budget_state(user, db, month)


@router.put("")
def set_budget(body: BudgetIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    selected_month, _, _ = _month(body.month)
    saved_budget = db.query(MonthlyBudget).filter_by(user_id=user.id, month=selected_month).first()
    if saved_budget:
        saved_budget.amount = body.amount
    else:
        db.add(MonthlyBudget(user_id=user.id, month=selected_month, amount=body.amount))
    if selected_month == date.today().strftime("%Y-%m"):
        user.monthly_budget = body.amount
    db.commit()
    db.refresh(user)
    return _budget_state(user, db, selected_month)
