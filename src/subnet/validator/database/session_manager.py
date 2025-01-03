import contextlib
import os
from typing import AsyncIterator, Optional
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from loguru import logger


class DatabaseSessionManager:
    def __init__(self) -> None:
        self._engine: Optional[AsyncEngine] = None
        self._sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None

    def init(self, db_url: str) -> None:
        # Customize connection arguments for specific databases
        if "postgresql" in db_url:
            connect_args = {
                "statement_cache_size": 0,
                "prepared_statement_cache_size": 0,
            }
        else:
            connect_args = {}

        self._engine = create_async_engine(
            url=db_url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        self._sessionmaker = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
        )

    async def close(self) -> None:
        if self._engine is None:
            return
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise IOError("DatabaseSessionManager is not initialized")
        async with self._sessionmaker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise IOError("DatabaseSessionManager is not initialized")
        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise


db_manager = DatabaseSessionManager()


async def get_session() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency to get a database session.
    Usage: session: AsyncSession = Depends(get_session)
    """
    async with db_manager.session() as session:
        yield session


def run_migrations():
    import subprocess
    import os
    from pathlib import Path

    # Resolve the correct path to the `alembic.ini` file
    script_directory = Path(__file__).parent.parent  # One level up to `validator`
    execution_path = script_directory / "database"  # Point to `validator/database`

    # Backup command
    if os.getenv("SKIP_BACKUP", "False") == "False":
        backup_result = subprocess.run(
            ["docker", "start", "postgres_backup"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if backup_result.stdout:
            logger.warning(backup_result.stdout)
        if backup_result.stderr:
            logger.error(backup_result.stderr)

    # Migration command
    if os.getenv("SKIP_MIGRATIONS", "False") == "False":
        command = ["alembic", "upgrade", "head"]
        migration_result = subprocess.run(
            command,
            cwd=str(execution_path),  # Correctly set cwd to `validator/database`
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if migration_result.stdout:
            logger.warning(migration_result.stdout)
        if migration_result.stderr:
            logger.error(migration_result.stderr)
