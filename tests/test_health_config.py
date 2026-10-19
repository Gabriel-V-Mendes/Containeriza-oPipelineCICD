"""Testes dos caminhos de erro que não dependem do CRUD."""

import pytest
from sqlalchemy.exc import OperationalError

from app import config, main


def _database_down():
    raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_readiness_returns_503_when_database_is_down(client, monkeypatch):
    # monkeypatch.context() desfaz o patch ao sair do bloco, antes do teardown
    # da fixture "client" (que precisa do banco para o drop_all).
    with monkeypatch.context() as m:
        m.setattr(main.engine, "connect", _database_down)
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}


def test_liveness_ignores_database_outage(client, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(main.engine, "connect", _database_down)
        response = client.get("/health")
    assert response.status_code == 200


def test_missing_database_url_fails_fast(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        config.get_database_url()


def test_build_engine_postgresql():
    from app.database import _build_engine

    eng = _build_engine("postgresql+psycopg://user:pass@localhost:5432/test")
    assert eng.dialect.name == "postgresql"
