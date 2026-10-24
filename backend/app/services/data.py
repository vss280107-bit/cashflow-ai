import pandas as pd
from sqlalchemy.orm import Session

from ..models import Transaction


def load_df(db: Session, user_id: int) -> pd.DataFrame:
    rows = db.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.date).all()
    df = pd.DataFrame(
        [{"id": t.id, "date": pd.Timestamp(t.date), "amount": t.amount, "type": t.type,
          "category": t.category, "description": t.description or ""} for t in rows],
        columns=["id", "date", "amount", "type", "category", "description"],
    )
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    return df


def refresh_recurring_flags(db: Session, user_id: int) -> int:
    """Re-run recurring detection and persist `is_recurring` on every transaction."""
    from .recurring import add_keys, detect

    df = load_df(db, user_id)
    if df.empty:
        return 0
    keys = {r.key for r in detect(df)}
    flags = add_keys(df).set_index("id")["key"].isin(keys).to_dict()
    for t in db.query(Transaction).filter(Transaction.user_id == user_id):
        t.is_recurring = bool(flags.get(t.id, False))
    db.commit()
    return len(keys)
