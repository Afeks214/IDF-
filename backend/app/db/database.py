"""
Database configuration and connection management for IDF Testing Infrastructure.
Optimized for Hebrew text support with PostgreSQL.
"""

import os
from typing import AsyncGenerator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# Database configuration for Hebrew support
DATABASE_CONFIG = {
    "encoding": "utf-8",
    "client_encoding": "utf8",
    "timezone": "Asia/Jerusalem",
    # PostgreSQL specific settings for Hebrew support
    "connect_args": {
        "server_settings": {
            "jit": "off",  # Disable JIT for better Hebrew text performance
            "shared_preload_libraries": "pg_stat_statements",
            "default_text_search_config": "hebrew",  # Hebrew full-text search
            "lc_collate": "he_IL.UTF-8",
            "lc_ctype": "he_IL.UTF-8",
        }
    }
}

# Environment variables
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://dev_user:dev_password@localhost:5432/idf_testing"
)

# For sync operations (migrations, etc.)
SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# Create declarative base
Base = declarative_base()

# Async engine for main application
async_engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections every hour
    echo=os.getenv("SQL_DEBUG", "false").lower() == "true",
    **DATABASE_CONFIG
)

# Sync engine for migrations and administrative tasks
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=os.getenv("SQL_DEBUG", "false").lower() == "true",
)

# Session makers
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    Ensures proper connection handling and Hebrew text support.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Set Hebrew locale for this session
            await session.execute(text("SET lc_time = 'he_IL.UTF-8'"))
            await session.execute(text("SET timezone = 'Asia/Jerusalem'"))
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


async def create_tables():
    """Create all tables in the database with Hebrew support."""
    async with async_engine.begin() as conn:
        # Enable Hebrew extensions
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        
        # Create tables
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all tables (for testing/reset)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


class DatabaseManager:
    """Database management utilities for IDF Testing Infrastructure."""
    
    def __init__(self):
        self.async_engine = async_engine
        self.sync_engine = sync_engine
    
    async def check_connection(self) -> bool:
        """Check if database connection is working."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception:
            return False
    
    async def check_hebrew_support(self) -> bool:
        """Verify Hebrew text support is working correctly."""
        try:
            async with AsyncSessionLocal() as session:
                # Test Hebrew text insertion and retrieval
                test_hebrew = "בדיקת תמיכה בעברית"
                result = await session.execute(text("SELECT :hebrew_text"), {"hebrew_text": test_hebrew})
                retrieved = result.scalar()
                return retrieved == test_hebrew
        except Exception:
            return False
    
    async def get_database_info(self) -> dict:
        """Get database information and configuration."""
        try:
            async with AsyncSessionLocal() as session:
                queries = {
                    "version": "SELECT version()",
                    "encoding": "SHOW server_encoding",
                    "collation": "SHOW lc_collate",
                    "timezone": "SHOW timezone",
                    "max_connections": "SHOW max_connections",
                }
                
                info = {}
                for key, query in queries.items():
                    result = await session.execute(text(query))
                    info[key] = result.scalar()
                
                return info
        except Exception as e:
            return {"error": str(e)}
    
    async def optimize_for_hebrew(self):
        """Apply Hebrew-specific database optimizations."""
        async with AsyncSessionLocal() as session:
            # Set Hebrew-optimized configuration
            optimizations = [
                "SET default_text_search_config = 'hebrew'",
                "SET lc_collate = 'he_IL.UTF-8'",
                "SET lc_ctype = 'he_IL.UTF-8'",
                "SET client_encoding = 'UTF8'",
            ]
            
            for optimization in optimizations:
                try:
                    await session.execute(text(optimization))
                except Exception as e:
                    print(f"Warning: Could not apply optimization '{optimization}': {e}")
            
            await session.commit()


# Global database manager instance
db_manager = DatabaseManager()


# Connection event handlers for Hebrew support
@async_engine.sync_engine.event.listens_for(sync_engine, "connect")
def set_hebrew_pragmas(dbapi_connection, connection_record):
    """Set Hebrew-specific connection parameters."""
    with dbapi_connection.cursor() as cursor:
        # Set client encoding to UTF-8
        cursor.execute("SET client_encoding TO 'UTF8'")
        # Set timezone to Israel
        cursor.execute("SET timezone TO 'Asia/Jerusalem'")


async def test_database_setup():
    """Test database setup and Hebrew support."""
    print("Testing database connection...")
    
    # Test basic connection
    is_connected = await db_manager.check_connection()
    print(f"Database connection: {'✓' if is_connected else '✗'}")
    
    # Test Hebrew support
    hebrew_support = await db_manager.check_hebrew_support()
    print(f"Hebrew text support: {'✓' if hebrew_support else '✗'}")
    
    # Get database info
    db_info = await db_manager.get_database_info()
    if "error" not in db_info:
        print(f"Database version: {db_info.get('version', 'Unknown')}")
        print(f"Encoding: {db_info.get('encoding', 'Unknown')}")
        print(f"Collation: {db_info.get('collation', 'Unknown')}")
        print(f"Timezone: {db_info.get('timezone', 'Unknown')}")
    else:
        print(f"Error getting database info: {db_info['error']}")
    
    return is_connected and hebrew_support


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_database_setup())