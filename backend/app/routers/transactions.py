import csv
import io
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Transaction, User
from ..schemas import TransactionIn, TransactionOut
from ..services.categorizer import EXPENSE_CATEGORIES, INCOME_CATEGORIES, categorize
from ..services.data import refresh_recurring_flags
from ..services.forecaster import clear_cache
from ..services.seed import generate_demo_transactions

router = APIRouter(prefix="/api/transactions", tags=["transactions"])
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")


def _changed(db: Session, user_id: int):
    clear_cache(user_id)
    refresh_recurring_flags(db, user_id)


@router.get("/categories")
def categories():
    return {"expense": EXPENSE_CATEGORIES, "income": INCOME_CATEGORIES}


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    start: date | None = None, end: date | None = None, type: str | None = None,
    category: str | None = None, q: str | None = None, limit: int = Query(500, le=5000),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    query = db.query(Transaction).filter(Transaction.user_id == user.id)
    if start: query = query.filter(Transaction.date >= start)
    if end: query = query.filter(Transaction.date <= end)
    if type: query = query.filter(Transaction.type == type)
    if category: query = query.filter(Transaction.category == category)
    rows = query.order_by(Transaction.date.desc(), Transaction.id.desc()).all()
    if q:  # descriptions are encrypted at rest, so search happens after decryption
        rows = [r for r in rows if q.lower() in (r.description or "").lower()]
    return rows[:limit]


@router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(body: TransactionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = Transaction(user_id=user.id, date=body.date, amount=body.amount, type=body.type,
                    description=body.description, category=body.category or categorize(body.description, body.type))
    db.add(t)
    db.commit()
    _changed(db, user.id)
    db.refresh(t)
    return t


@router.put("/{txn_id}", response_model=TransactionOut)
def update_transaction(txn_id: int, body: TransactionIn, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    t = db.query(Transaction).filter(Transaction.id == txn_id, Transaction.user_id == user.id).first()
    if not t:
        raise HTTPException(404, "Transaction not found")
    t.date, t.amount, t.type, t.description = body.date, body.amount, body.type, body.description
    t.category = body.category or categorize(body.description, body.type)
    db.commit()
    _changed(db, user.id)
    db.refresh(t)
    return t


@router.delete("/{txn_id}", status_code=204)
def delete_transaction(txn_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.query(Transaction).filter(Transaction.id == txn_id, Transaction.user_id == user.id).first()
    if not t:
        raise HTTPException(404, "Transaction not found")
    db.delete(t)
    db.commit()
    _changed(db, user.id)


def _parse_date(raw: str) -> date:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date '{raw}'")


@router.post("/import")
async def import_csv(file: UploadFile = File(...), user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """CSV columns: date, amount, description [, type, category]. Negative amount or type=expense => expense."""
    text = (await file.read()).decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(400, "Empty CSV")
    cols = {c.strip().lower(): c for c in reader.fieldnames}
    if "date" not in cols or "amount" not in cols:
        raise HTTPException(400, "CSV needs at least 'date' and 'amount' columns")
    added, errors = 0, []
    for i, row in enumerate(reader, start=2):
        try:
            amount = float(str(row[cols["amount"]]).replace(",", "").replace("₹", "").strip())
            typ = (row.get(cols.get("type", ""), "") or "").strip().lower()
            if typ not in ("income", "expense"):
                typ = "expense" if amount < 0 else "income"
                if "type" not in cols and amount >= 0:
                    typ = "income"
            desc = (row.get(cols.get("description", ""), "") or "").strip()
            cat = (row.get(cols.get("category", ""), "") or "").strip().lower() or categorize(desc, typ)
            if amount == 0:
                raise ValueError("zero amount")
            db.add(Transaction(user_id=user.id, date=_parse_date(row[cols["date"]]), amount=abs(amount),
                               type=typ, category=cat, description=desc))
            added += 1
        except Exception as exc:  # collect row-level problems instead of failing the whole import
            errors.append({"row": i, "error": str(exc)})
    db.commit()
    _changed(db, user.id)
    return {"imported": added, "errors": errors[:20], "error_count": len(errors)}


@router.post("/demo")
def load_demo(replace: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    has = db.query(Transaction).filter(Transaction.user_id == user.id).count()
    if has and not replace:
        raise HTTPException(409, "You already have transactions. Pass replace=true to overwrite them.")
    if has:
        db.query(Transaction).filter(Transaction.user_id == user.id).delete()
    rows = generate_demo_transactions(end=date.today() - timedelta(days=1), seed=user.id + 6)
    db.add_all(Transaction(user_id=user.id, **r) for r in rows)
    user.opening_balance, user.low_balance_threshold = 8000.0, 3000.0
    db.commit()
    _changed(db, user.id)
    return {"imported": len(rows)}
