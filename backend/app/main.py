import os
import logging
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routes import documents, chat
from app.database import engine, Base
from app.logger import setup_logging
from app.config import settings

setup_logging()
logger = logging.getLogger(__name__)

# Initialize Sentry — only if DSN is configured
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.2,  # capture 20% of requests for performance monitoring
        environment="production",
        send_default_pii=False,  # don't send personally identifiable information
    )
    logger.info("Sentry initialized")
else:
    logger.info("Sentry disabled — SENTRY_DSN not set")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Try to create tables but don't crash if DB is unavailable
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("==> Database tables ready")
    except Exception as e:
        logger.error("Database connection failed", exc_info=True)
        logger.error("==> Starting without database — uploads and chat will fail")

    logger.info("DocMind API starting up")
    yield
    logger.info("DocMind API shutting down")


app = FastAPI(title="Doc Assistant API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://doc-assistant-three.vercel.app",
        "https://doc-assistant-production.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Doc Assistant API is running"}


# Test endpoint — remove after verifying Sentry works
@app.get("/sentry-test")
def sentry_test():
    raise ValueError("Sentry test error — if you see this in Sentry, it works!")
