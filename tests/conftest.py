"""Fixtures compartilhadas.

Por padrão os testes usam SQLite em memória (rápido, sem dependências).
No CI, DATABASE_URL aponta para um Postgres real (service container), então
os mesmos testes também rodam contra o banco de produção.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import pytest  # noqa: E402  (precisa vir depois de definir DATABASE_URL)
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    # Banco limpo a cada teste: nenhum teste depende da ordem de execução.
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as c:  # o "with" executa o lifespan (create_all)
        yield c
    Base.metadata.drop_all(bind=engine)
