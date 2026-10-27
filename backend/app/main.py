from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine, migrate_transaction_recurring_column, migrate_user_financial_columns
from .routers import analysis, auth, budget, transactions


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_user_financial_columns()
    migrate_transaction_recurring_column()
    yield


app = FastAPI(title="CashFlow AI API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(analysis.router)
app.include_router(budget.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
