import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _database_unavailable(db: Session, exc: SQLAlchemyError):
    db.rollback()
    # Do not log SQL parameters: they can contain emails or password hashes.
    logger.error("Authentication database operation failed (%s)", type(exc).__name__)
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                        "Authentication is temporarily unavailable. Please try again.") from None


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = str(body.email).strip().lower()
    try:
        if db.query(User).filter(func.lower(func.trim(User.email)) == email).first():
            raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
        user = User(
            email=email,
            name=body.name.strip(),
            hashed_password=hash_password(body.password),
            opening_balance=0.0,
            low_balance_threshold=2000.0,
        )
        db.add(user)
        db.flush()
        token = create_access_token(user.id)
        db.commit()
        return TokenOut(access_token=token)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "An account with this email already exists.") from None
    except SQLAlchemyError as exc:
        _database_unavailable(db, exc)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    email = str(body.email).strip().lower()
    try:
        user = db.query(User).filter(func.lower(func.trim(User.email)) == email).first()
    except SQLAlchemyError as exc:
        _database_unavailable(db, exc)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
