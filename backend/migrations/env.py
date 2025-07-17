"""Alembic migration environment with Hebrew support."""

import logging
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import DATABASE_URL
from app.models.base import Base
from app.models.core import *  # Import all models

# Alembic Config object
config = context.config

# Set database URL from environment
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    
    # PostgreSQL specific settings for Hebrew support
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={
            "client_encoding": "utf8",
            "server_settings": {
                "timezone": "Asia/Jerusalem",
                "lc_collate": "he_IL.UTF-8",
                "lc_ctype": "he_IL.UTF-8",
            }
        }
    )

    with connectable.connect() as connection:
        # Set Hebrew-specific session variables
        connection.execute("SET client_encoding TO 'UTF8'")
        connection.execute("SET timezone TO 'Asia/Jerusalem'")
        
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()