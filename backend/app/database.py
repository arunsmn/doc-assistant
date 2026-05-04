from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# The engine is the connection to PostgreSQL
# pool_pre_ping=True checks the connection is alive before using it
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False,  # set True to see SQL queries in terminal (useful for debugging)
)

# Session factory — creates database sessions on demand
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# Base class all models inherit from
class Base(DeclarativeBase):
    pass


# FastAPI dependency — provides a DB session to any route that needs it
# The session is automatically closed when the request finishes
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
