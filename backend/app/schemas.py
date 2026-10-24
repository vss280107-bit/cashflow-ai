from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = ""


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    opening_balance: float
    low_balance_threshold: float

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: str | None = None
    opening_balance: float | None = None
    low_balance_threshold: float | None = Field(default=None, ge=0)


class TransactionIn(BaseModel):
    date: date
    amount: float = Field(gt=0)
    type: Literal["income", "expense"]
    category: str | None = None
    description: str = ""


class TransactionOut(BaseModel):
    id: int
    date: date
    amount: float
    type: str
    category: str
    description: str
    is_recurring: bool

    model_config = {"from_attributes": True}


class PlannedExpense(BaseModel):
    date: date
    amount: float = Field(gt=0)
    description: str = "Planned expense"


class WhatIfIn(BaseModel):
    horizon: int = Field(default=30, ge=7, le=60)
    expenses: list[PlannedExpense]
