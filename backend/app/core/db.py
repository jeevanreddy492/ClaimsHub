"""Database engine and session handling.

Services own the transaction: they call ``session.commit()`` when a unit of work
is done. The request dependency only rolls back on error and closes the session.
"""

from collections.abc import Iterator

from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    # Named constraints make Oracle errors readable (no SYS_C00123 names).
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def build_engine(url: str | None = None) -> Engine:
    settings = get_settings()
    url = url or settings.database_url
    if url.startswith("sqlite"):
        # Tests only: one shared in-memory DB across threads.
        engine = create_engine(
            url, connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
        )

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _record):  # type: ignore[no-untyped-def]
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

        return engine

    connect_args = {"dsn": settings.database_dsn} if settings.database_dsn else {}
    return create_engine(
        url,
        connect_args=connect_args,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout_seconds,
        pool_pre_ping=True,  # drops dead connections (Autonomous DB closes idle ones)
        pool_recycle=1800,
        echo=settings.db_echo,
        future=True,
    )


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def is_oracle(session: Session) -> bool:
    return session.get_bind().dialect.name == "oracle"
