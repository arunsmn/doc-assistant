import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routes import documents, chat
from app.database import engine, Base
from app.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Try to create tables but don't crash if DB is unavailable
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("==> Database tables ready")
    except Exception as e:
        logger.error(f"==> Database connection failed: {e}", exc_info=True)
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
