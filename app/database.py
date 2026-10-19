"""Engine, sessão e classe base do SQLAlchemy."""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_database_url


class Base(DeclarativeBase):
    pass


def _build_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        # Usado apenas nos testes locais rápidos. O SQLite em memória precisa de
        # uma única conexão compartilhada (StaticPool) para que todas as sessões
        # enxerguem as mesmas tabelas.
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    # pool_pre_ping descarta conexões mortas (ex.: o Postgres reiniciou).
    return create_engine(url, pool_pre_ping=True)


engine = _build_engine(get_database_url())
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por requisição."""
    with SessionLocal() as session:
        yield session
