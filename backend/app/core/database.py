#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDF Testing Infrastructure - Database Management
High-performance async database layer with connection pooling
"""

import asyncio
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    create_async_engine,
    AsyncEngine,
    async_sessionmaker
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
import structlog
from contextlib import asynccontextmanager

from core.config import settings

logger = structlog.get_logger()

# Create the declarative base
Base = declarative_base()

# Global engine instance
engine: Optional[AsyncEngine] = None
SessionLocal: Optional[async_sessionmaker] = None


def create_engine_with_pool() -> AsyncEngine:
    """Create async engine with optimized connection pooling"""
    
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL must be configured")
    
    # Engine configuration for performance
    engine_config = {
        "url": str(settings.DATABASE_URL),
        "echo": settings.DB_ECHO,
        "future": True,
        "poolclass": QueuePool,
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_pre_ping": True,  # Verify connections before use
        "connect_args": {
            "server_settings": {
                "jit": "off",  # Disable JIT for faster connection
                "timezone": "UTC",
                "statement_timeout": f"{settings.QUERY_TIMEOUT}s"
            },
            "command_timeout": settings.QUERY_TIMEOUT
        }
    }
    
    return create_async_engine(**engine_config)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for performance (if using SQLite for testing)"""
    if "sqlite" in str(settings.DATABASE_URL):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=1000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()


async def init_db() -> None:
    """Initialize database connection and session factory"""
    global engine, SessionLocal
    
    logger.info("Initializing database connection")
    
    try:
        engine = create_engine_with_pool()
        
        # Test connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        # Create session factory
        SessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False
        )
        
        logger.info("Database connection initialized successfully")
        
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


async def create_tables() -> None:
    """Create all database tables"""
    if not engine:
        await init_db()
    
    logger.info("Creating database tables")
    
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they're registered
            from models import *  # noqa
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise


async def drop_tables() -> None:
    """Drop all database tables (for testing)"""
    if not engine:
        await init_db()
    
    logger.warning("Dropping all database tables")
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.info("Database tables dropped successfully")
        
    except Exception as e:
        logger.error("Failed to drop database tables", error=str(e))
        raise


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with automatic cleanup"""
    if not SessionLocal:
        await init_db()
    
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session"""
    async with get_db_session() as session:
        yield session


class DatabaseManager:
    """High-performance database operations manager"""
    
    def __init__(self):
        self.engine = engine
        self.session_factory = SessionLocal
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            async with get_db_session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False
    
    async def get_connection_stats(self) -> dict:
        """Get database connection pool statistics"""
        if not self.engine:
            return {}
        
        pool = self.engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid()
        }
    
    async def execute_query(self, query: str, params: dict = None) -> list:
        """Execute raw SQL query with parameters"""
        async with get_db_session() as session:
            result = await session.execute(text(query), params or {})
            return [dict(row) for row in result.fetchall()]
    
    async def bulk_insert(self, model_class, data_list: list) -> None:
        """Optimized bulk insert operation"""
        if not data_list:
            return
        
        async with get_db_session() as session:
            session.add_all([model_class(**data) for data in data_list])
            await session.commit()
    
    async def bulk_update(self, model_class, data_list: list, 
                         update_key: str = "id") -> None:
        """Optimized bulk update operation"""
        if not data_list:
            return
        
        async with get_db_session() as session:
            for data in data_list:
                key_value = data.pop(update_key)
                await session.execute(
                    update(model_class)
                    .where(getattr(model_class, update_key) == key_value)
                    .values(**data)
                )
            await session.commit()


# Global database manager instance
db_manager = DatabaseManager()


# Performance monitoring for database operations
class DatabaseMetrics:
    """Database performance metrics collector"""
    
    def __init__(self):
        self.query_times = []
        self.connection_counts = []
        self.error_counts = 0
    
    def record_query_time(self, duration: float):
        """Record query execution time"""
        self.query_times.append(duration)
        
        # Keep only last 1000 entries
        if len(self.query_times) > 1000:
            self.query_times = self.query_times[-1000:]
    
    def record_connection_count(self, count: int):
        """Record active connection count"""
        self.connection_counts.append(count)
        
        # Keep only last 100 entries
        if len(self.connection_counts) > 100:
            self.connection_counts = self.connection_counts[-100:]
    
    def record_error(self):
        """Record database error"""
        self.error_counts += 1
    
    def get_metrics(self) -> dict:
        """Get performance metrics summary"""
        if not self.query_times:
            return {"status": "no_data"}
        
        return {
            "avg_query_time": sum(self.query_times) / len(self.query_times),
            "max_query_time": max(self.query_times),
            "min_query_time": min(self.query_times),
            "total_queries": len(self.query_times),
            "avg_connections": (
                sum(self.connection_counts) / len(self.connection_counts)
                if self.connection_counts else 0
            ),
            "error_count": self.error_counts
        }


# Global metrics instance
db_metrics = DatabaseMetrics()


async def close_db() -> None:
    """Close database connections"""
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("Database connections closed")


# Context manager for database transactions
@asynccontextmanager
async def transaction():
    """Database transaction context manager"""
    async with get_db_session() as session:
        async with session.begin():
            yield session