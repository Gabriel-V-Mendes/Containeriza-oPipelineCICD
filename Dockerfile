# ==========================================
# Estágio 1: Builder (Compilação)
# ==========================================
FROM python:3.12-slim AS builder

# Criação de um ambiente virtual para isolar as dependências
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

# Instalação das dependências sem guardar cache para economizar espaço
RUN pip install --no-cache-dir -r requirements.txt

# ==========================================
# Estágio 2: Production (Imagem Final)
# ==========================================
FROM python:3.12-slim

# Criação de um usuário sem privilégios de root (Princípio do menor privilégio)
RUN useradd -m appuser

# Copia apenas o ambiente virtual pronto do estágio 'builder'
COPY --from=builder /opt/venv /opt/venv

# Adiciona o venv ao PATH
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copia o código da aplicação
COPY app/main.py .

# Ajusta as permissões para o usuário não-root
RUN chown -R appuser:appuser /app

# Define o usuário que executará o processo
USER appuser

EXPOSE 8000

# Comando para iniciar a aplicação
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]