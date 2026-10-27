from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)

    @field_validator("password")
    @classmethod
    def password_length(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 UTF-8 bytes or fewer")
        return value


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("password")
    @classmethod
    def password_length(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 UTF-8 bytes or fewer")
        return value


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    name: str

    model_config = {"from_attributes": True}


class TransactionIn(BaseModel):
    date: date
    amount: float = Field(gt=0, allow_inf_nan=False)
    type: Literal["income", "expense"]
    category: str | None = None
    description: str = Field(default="", max_length=500)


class TransactionOut(BaseModel):
    id: int
    date: date
    amount: float
    type: str
    category: str
    description: str
    model_config = {"from_attributes": True}


class BudgetIn(BaseModel):
    amount: float = Field(gt=0, allow_inf_nan=False)
    month: str | None = None

    @field_validator("month")
    @classmethod
    def valid_budget_month(cls, value):
        if value is not None:
            try:
                parsed = date.fromisoformat(f"{value}-01")
            except ValueError as exc:
                raise ValueError("Month must use YYYY-MM format") from exc
            if parsed.strftime("%Y-%m") != value:
                raise ValueError("Month must use YYYY-MM format")
        return value
