from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Enable SSL conditionally (required for cloud DBs like Neon/Supabase, but disabled for local DBs)
is_local_db = "localhost" in settings.DATABASE_URL or "127.0.0.1" in settings.DATABASE_URL
ssl_config = True if not is_local_db else False

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=300,       # recycle connections after 5 min to avoid stale TCP
    pool_timeout=10,        # fail fast if no connection available within 10s
    connect_args={
        "ssl": ssl_config,
        "statement_cache_size": 0,  # avoids asyncpg prepared statement conflicts
    },
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
