# 🚀 Projeto DevOps: Containerização e Pipeline CI/CD

# Esse projeto foi feito com o objetivo de estudos e pratica na cultura DevOps focando em boas praticas de infraestrutura e segurança 

## 🎯 Objetivo Arquitetônico
[cite_start]O objetivo primário deste projeto é solucionar o problema histórico da inconsistência de dependências entre os ecossistemas locais de desenvolvimento e produção (o famoso "funciona na minha máquina"). 

[cite_start]A solução técnica adotada foi a conteinerização estruturada da aplicação, combinada com um pipeline de integração contínua (CI) automatizado[cite: 2].

## 🛠️ Stack Tecnológica
* **Aplicação:** FastAPI (Python)
* **Banco de Dados:** PostgreSQL
* **Orquestração e Containers:** Docker, Docker Compose
* **Qualidade de Código:** Pytest
* **Automação e CI/CD:** GitHub Actions
* **Segurança (DevSecOps):** Aqua Trivy

---

## ⚙️ A Esteira de CI/CD (Como funciona)
[cite_start]O orquestrador central do pipeline foi configurado para ser acionado mecanicamente a cada novo push para a ramificação principal (main branch)[cite: 9, 10]. O fluxo de trabalho contempla as seguintes etapas técnicas:

1. [cite_start]**Checkout & Setup:** O repositório de código-fonte é extraído de forma limpa pelo agente em nuvem do GitHub Actions[cite: 11].
2. [cite_start]**Testes Unitários Isolados:** Execução das suítes de teste para comprovar que as funcionalidades não quebraram o comportamento das regras de negócio[cite: 12].
3. [cite_start]**Build Contínuo Otimizado:** O motor autônomo processa a imagem do Docker baseando-se estritamente nas regras do Dockerfile multi-estágio[cite: 13].
4. [cite_start]**Verificação Estática de Segurança (Image Scanning):** Incorporação do Trivy para varrer fisicamente a imagem binária em busca de bibliotecas vulneráveis e exposições (CVEs)[cite: 14].
5. [cite_start]**Container Registry:** Em caso de sucesso, a imagem recebe uma tag semântica e fica pronta para envio aos repositórios de artefatos[cite: 15].

---

## 🔒 Boas Práticas de Segurança e Infraestrutura Aplicadas
* [cite_start]**Multi-stage Builds:** O provisionamento de ambientes de compilação volumosos aumenta a superfície de ataques[cite: 4]. [cite_start]Por isso, adotamos compilações de múltiplos estágios para gerar imagens minimalistas e enxutas[cite: 3, 5].
* [cite_start]**Princípio do Privilégio Mínimo:** Os privilégios operacionais foram modificados para que a aplicação não execute processos valendo-se do superusuário irrestrito `root` dentro do contêiner.
* **Infraestrutura como Código Local:** Utilização do `docker-compose.yml` e mapeamento de volumes (Bind Mounts) para garantir isolamento e fluidez no desenvolvimento sem contaminar a imagem final de produção.

---
