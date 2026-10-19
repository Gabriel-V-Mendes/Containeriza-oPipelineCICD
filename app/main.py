from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import APP_NAME, APP_VERSION
from app.database import Base, engine
from app.routers import items  # importa app.models, registrando as tabelas no Base


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Cria as tabelas se não existirem. Simples e suficiente para um único
    # modelo; com o schema evoluindo, o certo é usar migrações (Alembic).
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)
app.include_router(items.router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Liveness: o processo está de pé. NÃO depende do banco.

    É o endpoint usado pelo HEALTHCHECK do Docker: se o Postgres cair, a API
    não deve ser reiniciada em loop por isso.
    """
    return {"status": "healthy", "message": "API is running!"}


@app.get("/health/ready", tags=["health"])
def readiness_check() -> dict[str, str]:
    """Readiness: a API consegue falar com o banco."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database unavailable"
        ) from exc
    return {"status": "ready", "database": "ok"}
