# syntax=docker/dockerfile:1

# A imagem base está escrita direto nos dois FROM (e não numa ARG) de propósito:
# o Dependabot só reconhece imagens em linhas FROM literais. Ela é fixada por
# DIGEST (build reprodutível) e o Dependabot abre PR quando sai uma versão nova.

# ==========================================
# Estágio 1: builder — instala dependências num venv
# ==========================================
FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /build

# Só o requirements.txt primeiro: enquanto ele não mudar, esta camada (a mais
# lenta) vem do cache, mesmo que o código mude.
COPY requirements.txt .
# O pip já gera os .pyc durante a instalação, e eles são MANTIDOS: o container roda
# com filesystem somente leitura, então sem eles o Python recompilaria tudo a cada
# start (medido: 2,8 s contra 1,35 s para importar a aplicação, em troca de 24 MB).
# O pip não é necessário em runtime e sai do venv: menos espaço e menos CVEs.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y pip

# ==========================================
# Estágio 2: runtime — imagem final, sem ferramentas de build
# ==========================================
FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS runtime

LABEL org.opencontainers.image.title="devops-api" \
      org.opencontainers.image.description="API FastAPI containerizada com CI/CD"

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 1) Remove o pip "de sistema" que vem na imagem base (a aplicação usa o venv).
# 2) Cria um usuário sem privilégios com UID/GID numéricos fixos (permite que
#    orquestradores validem "runAsNonRoot" sem precisar resolver nomes).
RUN python -m pip uninstall -y pip \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
# O código pertence ao root e é só leitura para o usuário "app": mesmo que o
# processo seja comprometido, ele não consegue alterar a própria aplicação.
# Os .pyc do código são gerados aqui, pelo mesmo motivo dos .pyc das dependências.
COPY app/ ./app/
RUN python -m compileall -q app

USER 10001:10001

EXPOSE 8000

# Usa Python puro (a imagem slim não tem curl/wget) contra o endpoint de liveness.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]