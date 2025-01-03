import os
import sys

# Dynamically add the project root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import asyncio
import os
from contextvars import ContextVar
from logging.config import fileConfig
from typing import Any
from alembic.runtime.environment import EnvironmentContext
from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from src.subnet.miner.database.migrations.settings import MinerMigrationSettings, load_environment

# Alembic Config object
config = context.config

# Load the environment from Alembic CLI arguments or default to mainnet
env = context.get_x_argument(as_dictionary=True).get("env", "mainnet")
load_environment(env)  # Pass the environment dynamically
migration_settings = MinerMigrationSettings()
config.set_main_option("sqlalchemy.url", migration_settings.DATABASE_URL)

# Logging configuration
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support
from src.subnet.miner.database import OrmBase
target_metadata = OrmBase.metadata

ctx_var: ContextVar[dict[str, Any]] = ContextVar("ctx_var")


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    try:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()
    except AttributeError:
        context_data = ctx_var.get()
        with EnvironmentContext(
                config=context_data["config"],
                script=context_data["script"],
                **context_data["opts"],
        ):
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in online mode with an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(run_async_migrations())
        return

    ctx_var.set({
        "config": context.config,
        "script": context.script,
        "opts": context._proxy.context_opts,  # type: ignore
    })


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
