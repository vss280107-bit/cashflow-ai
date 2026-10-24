from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import analysis, auth, transactions


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Cash-Flow Forecasting & Planning API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(analysis.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
