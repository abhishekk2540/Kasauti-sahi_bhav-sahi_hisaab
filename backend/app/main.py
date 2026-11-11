import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db
from .routers import agent, alerts, auth, customers, dashboard, rates, schemes, telegram

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create_all is fine for MVP; add Alembic before the first schema change in production
    yield


app = FastAPI(title="Kasauti API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

for r in (auth, rates, customers, alerts, schemes, dashboard, agent, telegram):
    app.include_router(r.router)


@app.get("/health")
def health():
    return {"status": "ok"}
