# DevOps API: FastAPI containerizada com CI/CD

[![CI/CD](https://github.com/Gabriel-V-Mendes/Containeriza-oPipelineCICD/actions/workflows/ci.yml/badge.svg)](https://github.com/Gabriel-V-Mendes/Containeriza-oPipelineCICD/actions/workflows/ci.yml)

API REST em **FastAPI + PostgreSQL**, empacotada numa imagem Docker enxuta e sem root. Um pipeline do **GitHub Actions** roda lint, testes, scan de segredos, build, scan de vulnerabilidades (Trivy), publica a imagem no **GHCR** e faz o **deploy via Docker Compose** numa VPS.

---

## 1. Problema

A primeira versão deste repositório *parecia* ter CI/CD, mas na prática:

| Sintoma | Consequência |
|---|---|
| O `Dockerfile` copiava `app/main.py` para o lugar errado | A imagem **não iniciava sozinha** (`ModuleNotFoundError: No module named 'app'`). Só funcionava no Compose porque um volume "tapava" o erro |
| O CI só fazia build da imagem, nunca a executava | O bug acima passava com o pipeline **verde** |
| Os dados ficavam numa lista em memória; o Postgres subia, mas ninguém usava | Os dados sumiam a cada restart |
| `pytest` e `httpx` iam para a imagem de produção | Imagem maior e mais CVEs |
| O pipeline imprimia "pronta para o Registry", mas não publicava nada | Não havia CD |
| Não havia branch protection | Um PR com teste quebrado podia ser mergeado |

**Objetivo:** ter um caminho mensurável de `git push` até produção, em que nada quebrado chegue à `main` nem ao servidor.

**Critérios de pronto:**
- [x] Um PR com teste quebrado não faz merge (checks obrigatórios + branch protection, ver [§6](#6-pr-com-teste-quebrado-não-faz-merge)).
- [x] A imagem final roda sem root (UID `10001`). O CI verifica isso a cada build.
- [x] Existe uma tabela antes/depois de tamanho, tempo de build e vulnerabilidades (ver [§7](#7-antes--depois)).

---

## 2. Arquitetura

```mermaid
flowchart LR
    dev["Dev: git push / PR"] --> gha

    subgraph gha["GitHub Actions"]
        direction TB
        lint["Lint: ruff + hadolint"]
        sec["Secret Scan: gitleaks"]
        test["Test: pytest + Postgres"]
        build["Build -> non-root check -> smoke test Compose -> Trivy"]
        push["Push GHCR (só na main)"]
        deploy["Deploy via SSH (só na main)"]
        lint --> build
        sec --> build
        test --> build
        build --> push --> deploy
    end

    push --> ghcr[("ghcr.io")]
    deploy --> vps
    subgraph vps["VPS: docker compose"]
        api["api (FastAPI, UID 10001)"] --> db[("postgres:17")]
    end
    ghcr -. "docker compose pull" .-> api
```

```text
app/
  main.py           # app, lifespan, /health e /health/ready
  config.py         # configuração via variáveis de ambiente (falha rápido se faltar)
  database.py       # engine/sessão SQLAlchemy
  models.py         # tabela items
  schemas.py        # validação Pydantic
  routers/items.py  # CRUD
tests/              # 11 testes (SQLite local / Postgres no CI), cobertura mínima de 90%
Dockerfile          # multi-stage, digest fixo, sem pip, não-root, HEALTHCHECK
docker-compose.yml       # ambiente local/CI (um comando)
docker-compose.prod.yml  # produção (imagem do GHCR, sem defaults de senha)
.github/workflows/ci.yml # pipeline completo
.github/dependabot.yml   # pip, Dockerfile, Compose e Actions
scripts/protect-main.sh  # aplica a branch protection
```

---

## 3. Subir com um comando

Pré-requisito: Docker com Compose v2.

```bash
docker compose up -d --build --wait     # ou: make up
```

O `--wait` só termina quando o Postgres **e** a API estão `healthy`.

| URL | O quê |
|---|---|
| http://localhost:8000/docs | Swagger (documentação interativa) |
| http://localhost:8000/health | Liveness (não depende do banco) |
| http://localhost:8000/health/ready | Readiness (testa a conexão com o Postgres) |

Para derrubar: `docker compose down`. Acrescente `-v` para apagar também os dados.
O pgAdmin é opcional: `docker compose --profile tools up -d` → http://localhost:5050.

### Endpoints

| Método | Rota | Descrição | Sucesso |
|---|---|---|---|
| GET | `/items?limit=20&offset=0` | Lista com paginação (limit de 1 a 100) | 200 |
| GET | `/items/{id}` | Busca um item | 200 / 404 |
| POST | `/items` | Cria `{"name": "...", "description": "..."}` | 201 / 422 |
| PATCH | `/items/{id}` | Atualização parcial | 200 / 404 / 422 |
| DELETE | `/items/{id}` | Remove | 204 / 404 |

---

## 4. Testes e lint

```bash
make test     # pytest + cobertura (SQLite em memória, sem precisar de Docker)
make lint     # ruff check, ruff format --check, hadolint
make scan     # Trivy na imagem local, com o mesmo critério do CI
make secrets  # gitleaks no histórico e nos arquivos não commitados
make help     # todos os atalhos
```

Para rodar os testes contra Postgres localmente, como o CI faz:
`DATABASE_URL=postgresql+psycopg://user:senha@localhost:5432/db make test`

---

## 5. CI/CD

Arquivo: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

| Job | Quando roda | O que faz | Falha se |
|---|---|---|---|
| **Lint** | PR e push | `ruff check`, `ruff format --check`, `hadolint` | Erro de lint ou de formatação |
| **Secret Scan** | PR e push | `gitleaks` em **todo** o histórico (`fetch-depth: 0`) | Algum segredo for encontrado |
| **Test** | PR e push | `pytest` contra um Postgres 17 real (service container) | Teste falhar ou cobertura < 90% |
| **Build, Scan & Push** | Depois dos 3 acima | Build com cache GHA → **verifica UID ≠ 0** → **smoke test com Compose** (sobe API + DB e chama `/health`, `/health/ready` e `POST /items`) → **Trivy** → push no GHCR (só fora de PR) | Imagem rodar como root, não ficar healthy, ou ter CVE CRITICAL/HIGH com correção disponível |
| **Deploy** | Push na `main`, se `DEPLOY_ENABLED=true` | `scp` do compose de produção → `docker compose pull && up -d --wait` | O container não ficar healthy em 120 s |

Tags publicadas: `sha-<commit>` (imutável, é a usada no deploy), `main`, `latest` e `X.Y.Z` (quando há tag git `vX.Y.Z`).

### Deploy via Compose: configuração (uma vez)

**Na VPS** (qualquer Linux com Docker):

```bash
sudo adduser --disabled-password deploy && sudo usermod -aG docker deploy
sudo mkdir -p /opt/devops-api && sudo chown deploy: /opt/devops-api
# Como usuário deploy: crie /opt/devops-api/.env a partir do .env.example,
# com uma senha forte (ex.: openssl rand -base64 32)
```

**No GitHub** (Settings → Secrets and variables → Actions):

| Tipo | Nome | Valor |
|---|---|---|
| Secret | `SSH_PRIVATE_KEY` | Chave privada **dedicada** ao deploy (`ssh-keygen -t ed25519`) |
| Secret | `SSH_KNOWN_HOSTS` | Saída de `ssh-keyscan <ip-da-vps>` (evita ataque MITM) |
| Variable | `DEPLOY_ENABLED` | `true` |
| Variable | `DEPLOY_HOST` / `DEPLOY_USER` / `DEPLOY_PATH` | IP, `deploy`, `/opt/devops-api` |
| Variable | `APP_URL` | (opcional) URL pública, aparece no environment |

Depois do primeiro push, deixe o pacote **público** em *Packages → devops-api → Package settings*. Assim a VPS faz `pull` sem precisar de login.

**Rollback:** rode de novo o job de deploy de um commit anterior, ou na VPS:
`IMAGE_TAG=sha-<commit-bom> docker compose -f docker-compose.prod.yml up -d --wait`.

---

## 6. PR com teste quebrado não faz merge

O CI falhando, sozinho, **não bloqueia** o merge. Quem bloqueia é a branch protection exigindo os checks. Para aplicá-la (repositório público, `gh` autenticado):

```bash
./scripts/protect-main.sh      # ou: make protect-main
```

A `main` passa a exigir PR, os 4 checks verdes (`Lint`, `Secret Scan`, `Test`, `Build, Scan & Push`), branch atualizada e histórico linear. A regra vale também para admins.

**Como provar:**

```bash
git switch -c demo/teste-quebrado
sed -i 's/"healthy"/"broken"/' tests/test_main.py   # quebra um teste
git commit -am "demo: teste quebrado" && git push -u origin demo/teste-quebrado
gh pr create --fill
```

O job `Test` fica vermelho, `Build, Scan & Push` é pulado e o botão de merge fica bloqueado ("Required statuses must pass"). Feche o PR depois.

---

## 7. Antes × depois

Mesma máquina (4 vCPU, Docker 29.9 com BuildKit) e mesma imagem base (`python:3.12-slim`, já baixada antes). Cada build foi feito sem cache (`--no-cache`), 3 vezes, e o tempo é a mediana. O tempo inclui o download dos pacotes do PyPI. Vulnerabilidades medidas com Trivy 0.75 (`--scanners vuln`). **Antes** = commit `c42c14e`; **depois** = esta versão.

| Métrica | Antes | Depois | Δ |
|---|---|---|---|
| Tamanho da imagem (disco) | 282 MB | **241 MB** | −41 MB (−15%) |
| Tamanho comprimido (o que é baixado do registry) | 66,7 MB | **56,8 MB** | −9,9 MB (−15%) |
| Tempo de build sem cache (mediana de 3) | 29,3 s | **25,2 s** | −4,1 s (−14%) |
| Vulnerabilidades (total) | 180 | **166** | −14 |
| ↳ CRITICAL / HIGH | 0 / 47 | **0 / 44** | −3 HIGH |
| ↳ em bibliotecas Python | 14 | **0** | −14 |
| ↳ com correção disponível (bloqueiam o CI se forem HIGH+) | 16 (3 HIGH) | **2** (UNKNOWN) | −14 |
| A imagem inicia sozinha? | ❌ `ModuleNotFoundError` | ✅ | |
| Usuário em runtime | `appuser` (a imagem nem subia) | **UID 10001**, código só leitura | |
| HEALTHCHECK | ❌ | ✅ | |

A imagem nova **tem mais coisa** (SQLAlchemy e psycopg com libpq embutida) e mesmo assim ficou menor. Os ganhos vêm de três mudanças: tirar as ferramentas de teste da imagem, remover o `pip` em runtime e limpar o `__pycache__`.

As 166 vulnerabilidades que sobraram estão **todas nos pacotes Debian da imagem base**. Quase todas ainda não têm correção publicada. As 2 que já têm correção (`liblzma5`, severidade UNKNOWN) somem quando o Dependabot atualizar o digest do `python:3.12-slim`. Para chegar perto de zero, veja [§10](#10-o-que-eu-faria-diferente).

---

## 8. Decisões e trade-offs

| Decisão | Alternativa | Por quê / custo |
|---|---|---|
| **Deploy via Compose numa VPS**, por SSH | PaaS (Render/Railway), Kubernetes | Custo previsível e baixo, e o mesmo `compose` do dev roda em produção. Em troca, eu cuido do servidor (patches, firewall, backup) e o deploy tem alguns segundos de indisponibilidade ao recriar o container |
| **SQLAlchemy síncrono + psycopg 3 (`[binary]`)** | async + asyncpg | Código mais simples, e o FastAPI roda endpoints síncronos num threadpool. O wheel binário embute a libpq, então a imagem dispensa compilador. Async rende mais sob muita concorrência de I/O, o que este projeto não precisa |
| **`create_all` na inicialização** | Alembic (migrações) | Basta para uma única tabela. Não lida com alteração de schema (ver §10) |
| **Testes em SQLite local + Postgres no CI** | Só Postgres | `make test` roda em menos de 1 s sem Docker. O CI garante a compatibilidade com o banco real. O risco é alguma diferença de dialeto passar despercebida localmente, e o CI pega isso |
| **`python:3.12-slim` (Debian)** | Alpine, distroless, Chainguard | Compatível com qualquer wheel (glibc) e fácil de depurar. Em troca, carrega CVEs do Debian. Alpine (musl) costuma quebrar wheels; distroless dificulta o debug |
| **Remover o `pip` da imagem final** | Manter | Elimina 6 CVEs do pip e uma ferramenta útil para um atacante. Em troca, não dá para dar `pip install` dentro do container (não deveria mesmo) |
| **Imagem base fixada por digest** + Dependabot | Tag flutuante / `apt-get upgrade` | Builds reprodutíveis, com atualização via PR que passa pelo CI. Em troca, as correções do SO só chegam quando a imagem oficial é reconstruída |
| **Trivy bloqueia só CRITICAL/HIGH com correção** (`ignore-unfixed`) | Bloquear tudo | Bloquear o que não tem correção travaria todo PR sem que eu pudesse agir. O que bloqueia é sempre algo acionável |
| **Smoke test com Compose dentro do CI** | Só build | Pega exatamente a classe de bug da versão antiga (a imagem compila mas não sobe) |
| **Actions fixadas por SHA** | Tags `@v4` / `@master` | Tags podem ser movidas (ataques de supply chain em actions já aconteceram). O Dependabot mantém os SHAs atualizados |
| **`/health` não consulta o banco**; `/health/ready` consulta | Um endpoint só | Se o Postgres cair, o HEALTHCHECK não deve reiniciar a API em loop |
| **Container `read_only`, `cap_drop: ALL`, `no-new-privileges`**, código pertencendo ao root | Defaults do Docker | Um processo comprometido não consegue alterar a aplicação nem escalar privilégio |
| **Postgres sem porta publicada** | Expor `5432` | Não expõe o banco e evita conflito com um Postgres já instalado na máquina. Para acessar: `docker compose exec db psql` |
| **Gitleaks via container no CI** + pre-commit opcional | `gitleaks-action` | Sem dependência de licença nem de action de terceiros. O pre-commit barra o segredo antes de ele chegar ao histórico |
| **Deploy "push" via SSH** | "Pull" (Watchtower) / runner self-hosted | Deploy rastreável no Actions, com rollback por SHA. Em troca, exige uma chave SSH com acesso ao Docker do servidor (equivale a root na VPS: use chave dedicada e um usuário só para isso) |

---

## 9. Custo estimado

Valores consultados em **outubro/2026**, sem impostos. Confira antes de contratar, porque preços e free tiers mudam.

| Item | Custo | Observação |
|---|---|---|
| GitHub Actions | **US$ 0** | Grátis e ilimitado em runners padrão para **repositório público**. Cada execução deve usar cerca de 4 a 6 min somados entre os jobs (estimativa: confirme na aba Actions depois da primeira execução) |
| GHCR (registry) | **US$ 0** | Pacotes públicos são gratuitos |
| Dependabot, branch protection | **US$ 0** | Gratuitos em repositório público |
| VPS: Hetzner CX23 (2 vCPU, 4 GB, 40 GB NVMe, 20 TB de tráfego) | **≈ €5,99/mês** | Sobra recurso: medi cerca de 90 MB de RAM na stack (API 64 MB + Postgres 24 MB) depois de 50 requisições. O compose de produção limita a API a 256 MB e o banco a 512 MB. Uma VPS de 1 GB de qualquer provedor também serve |
| Domínio (opcional) | ≈ R$ 40/ano (`.com.br`) | Sem domínio, acessa-se pelo IP |
| **Total** | **≈ €6/mês** | **€0** se o deploy for só local ou numa máquina que você já tem |

Se o repositório for **privado**, o plano Free do GitHub inclui uma cota mensal de minutos de Actions. Com cerca de 5 min por execução, ela cobre algumas centenas de pushes por mês.

---

## 10. O que eu faria diferente

1. **Alembic desde o início.** O `create_all` não altera tabelas existentes; a primeira mudança de schema em produção vai exigir migração.
2. **Imagem base distroless ou Chainguard (Wolfi).** Quase todas as 166 CVEs restantes vêm do Debian. Uma base mínima reduziria esse número para perto de zero, ao custo de perder o shell para depuração.
3. **TLS e proxy reverso** (Caddy ou Traefik com Let's Encrypt). Hoje a API responde em HTTP puro na porta 8000.
4. **Backup do Postgres** (`pg_dump` agendado para um storage externo) e um teste de restauração. Sem isso, o volume da VPS é ponto único de falha.
5. **Deploy sem indisponibilidade** (blue/green com o proxy) e um ambiente de **staging** antes de produção.
6. **Assinar a imagem** com cosign (keyless via OIDC) e publicar SBOM e provenance, para a VPS só rodar imagem assinada pelo CI.
7. **Segredos fora de arquivo `.env`** (Docker secrets, SOPS ou um vault) e **Rulesets** do GitHub no lugar da branch protection clássicatá no `.gitignore`) e nos Secrets do GitHub.
- Os defaults do `docker-compose.yml` (`devops`/`devops`) val.
8. **Observabilidade:** logs em JSON, métricas Prometheus (`/metrics`) e alerta quando o `/health/ready` falhar.
9. **Nome do repositório:** `Containeriza-oPipelineCICD` foi um erro de digitação (o "ç" e o "ã" viraram `-o`). Renomearia para algo como `fastapi-docker-cicd`.

---
