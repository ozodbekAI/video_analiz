import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from config import Config

Base = declarative_base()

config = Config()

# Engine yaratish
engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,  # True qilsangiz SQL loglar chiqadi
    pool_pre_ping=True,  # Connectionlarni tekshirish
    pool_size=10,
    max_overflow=20
)

# Session maker
async_session = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def create_db():
    """Database va tablelarni yaratish"""
    async with engine.begin() as conn:
        # UUID extension
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        
        # Barcha tablelarni yaratish
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Database tables created successfully")


async def get_session() -> AsyncSession:
    """Session olish uchun context manager"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
