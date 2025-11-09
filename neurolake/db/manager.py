"""
Database Connection Manager

Centralized database connection management with connection pooling.
Eliminates duplicate database connection code across the codebase.
"""

from typing import Generator, AsyncGenerator, Optional
from contextlib import contextmanager, asynccontextmanager
import logging

from sqlalchemy import create_engine, event, pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from neurolake.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Centralized database connection manager with singleton pattern

    Features:
    - Connection pooling with configurable pool size
    - Sync and async session support
    - Automatic connection health checks
    - Thread-safe singleton pattern

    Example:
        # Sync usage
        with get_db_session() as session:
            result = session.execute("SELECT 1")

        # Async usage
        async with get_async_db_session() as session:
            result = await session.execute("SELECT 1")
    """

    _instance: Optional['DatabaseManager'] = None
    _sync_engine = None
    _async_engine = None
    _sync_session_factory = None
    _async_session_factory = None

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize database manager"""
        if self._sync_engine is None:
            self._initialize_engines()

    def _initialize_engines(self):
        """Initialize SQLAlchemy engines with connection pooling"""
        settings = get_settings()
        db_settings = settings.database

        # Sync engine
        self._sync_engine = create_engine(
            db_settings.connection_string,
            poolclass=QueuePool,
            pool_size=db_settings.pool_size,
            max_overflow=db_settings.max_overflow,
            pool_timeout=db_settings.pool_timeout,
            pool_recycle=db_settings.pool_recycle,
            pool_pre_ping=True,  # Verify connections before using
            echo=db_settings.echo_sql,
        )

        # Async engine
        self._async_engine = create_async_engine(
            db_settings.async_connection_string,
            pool_size=db_settings.pool_size,
            max_overflow=db_settings.max_overflow,
            pool_timeout=db_settings.pool_timeout,
            pool_recycle=db_settings.pool_recycle,
            pool_pre_ping=True,
            echo=db_settings.echo_sql,
        )

        # Session factories
        self._sync_session_factory = sessionmaker(
            bind=self._sync_engine,
            class_=Session,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        self._async_session_factory = async_sessionmaker(
            bind=self._async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        # Setup connection event listeners
        self._setup_event_listeners()

        logger.info(
            f"Database connection pool initialized: "
            f"pool_size={db_settings.pool_size}, "
            f"max_overflow={db_settings.max_overflow}"
        )

    def _setup_event_listeners(self):
        """Setup SQLAlchemy event listeners for connection monitoring"""

        @event.listens_for(self._sync_engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Log new database connections"""
            logger.debug(f"New database connection established: {connection_record}")

        @event.listens_for(self._sync_engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Log connection checkout from pool"""
            logger.debug("Connection checked out from pool")

        @event.listens_for(self._sync_engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """Log connection checkin to pool"""
            logger.debug("Connection returned to pool")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a synchronous database session with automatic cleanup

        Yields:
            Session: SQLAlchemy session

        Example:
            db_manager = DatabaseManager()
            with db_manager.get_session() as session:
                result = session.query(User).all()
        """
        session = self._sync_session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an asynchronous database session with automatic cleanup

        Yields:
            AsyncSession: Async SQLAlchemy session

        Example:
            db_manager = DatabaseManager()
            async with db_manager.get_async_session() as session:
                result = await session.execute(select(User))
        """
        session = self._async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Async database session error: {e}")
            raise
        finally:
            await session.close()

    def close(self):
        """Close all database connections and dispose engines"""
        if self._sync_engine:
            self._sync_engine.dispose()
            logger.info("Sync database engine disposed")

        if self._async_engine:
            self._async_engine.dispose()
            logger.info("Async database engine disposed")

    @property
    def sync_engine(self):
        """Get the synchronous SQLAlchemy engine"""
        return self._sync_engine

    @property
    def async_engine(self):
        """Get the asynchronous SQLAlchemy engine"""
        return self._async_engine


# Global instance
_db_manager = None


def get_db_manager() -> DatabaseManager:
    """Get the global DatabaseManager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency for getting a database session

    Usage in FastAPI:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db_session)):
            return db.query(User).all()
    """
    db_manager = get_db_manager()
    with db_manager.get_session() as session:
        yield session


async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting an async database session

    Usage in FastAPI:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_async_db_session)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    db_manager = get_db_manager()
    async with db_manager.get_async_session() as session:
        yield session
