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
    from loguru import logger  # Assuming loguru is already imported for logging

    logger.debug(f"PATH: {os.environ['PATH']}")

    # Resolve the correct path to the `alembic.ini` file
    script_directory = Path(__file__).parent.parent  # Adjust as needed
    execution_path = script_directory / "database"  # Points to `validator/database`

    # Log the resolved execution path for debugging
    logger.debug(f"Execution path for alembic: {execution_path}")

    # Verify that alembic.ini exists
    if not (execution_path / "alembic.ini").exists():
        raise FileNotFoundError(f"Alembic.ini not found in {execution_path}")

    # Migration command
    if os.getenv("SKIP_MIGRATIONS", "False") == "False":
        # Use full path to alembic if required
        from shutil import which
        alembic_path = which("alembic")
        if not alembic_path:
            raise FileNotFoundError("Alembic executable not found. Ensure it is installed and in the PATH.")

        # Construct the Alembic command
        command = [alembic_path, "upgrade", "head"]

        # Ensure the environment contains the correct PATH
        env = os.environ.copy()
        logger.debug(f"Environment PATH: {env['PATH']}")

        # Run the migration
        migration_result = subprocess.run(
            command,
            cwd=str(execution_path),  # Set cwd to `validator/database`
            env=env,  # Pass the updated environment
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if migration_result.stdout:
            logger.warning(f"Migration stdout: {migration_result.stdout}")
        if migration_result.stderr:
            if "ERROR" in migration_result.stderr.upper():  # Log only actual errors
                logger.error(f"Migration stderr: {migration_result.stderr}")
            else:
                logger.info(f"Alembic stderr (non-critical): {migration_result.stderr}")

    logger.info("Migrations completed successfully.")
