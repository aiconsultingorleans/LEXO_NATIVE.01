"""
Configuration de la base de données SQLAlchemy
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
import logging

from .config import settings

logger = logging.getLogger(__name__)

# Moteur de base de données asynchrone
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base pour les modèles
metadata = MetaData()
Base = declarative_base(metadata=metadata)


async def get_db() -> AsyncSession:
    """Générateur de session de base de données"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialisation de la base de données"""
    try:
        async with engine.begin() as conn:
            # Création des tables
            await conn.run_sync(metadata.create_all)
        logger.info("✅ Base de données initialisée avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation de la base de données: {e}")
        raise