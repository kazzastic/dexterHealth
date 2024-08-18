from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import AsyncGenerator

DATABASE_URL = "postgresql+asyncpg://username:password@localhost/dbname"

# Create an async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Create a configured "Session" class
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create a base class for models
Base = declarative_base()

async def create_tables():
    async with engine.begin() as conn:
        # Ensure all tables are created
        await conn.run_sync(Base.metadata.create_all)

# Example function to get a database session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
