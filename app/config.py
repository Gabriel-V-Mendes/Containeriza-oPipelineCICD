"""Configuração lida de variáveis de ambiente (12-factor).

Nenhum valor sensível tem default aqui: se DATABASE_URL não existir, a aplicação
falha logo na inicialização com uma mensagem clara, em vez de subir "meio quebrada".
"""

import os


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "A variável de ambiente DATABASE_URL não está definida. "
            "Ex.: postgresql+psycopg://usuario:senha@db:5432/devops"
        )
    return url


APP_NAME = os.getenv("APP_NAME", "DevOps API")
APP_VERSION = os.getenv("APP_VERSION", "dev")
