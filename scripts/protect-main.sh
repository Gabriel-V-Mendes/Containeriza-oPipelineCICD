#!/usr/bin/env bash
# Protege a branch main: nada entra sem PR e sem TODOS os checks do CI verdes.
# É isso que garante que "um PR com teste quebrado não faz merge".
#
# Pré-requisitos: gh autenticado (gh auth login) com permissão de admin no repo.
# Branch protection é gratuita em repositórios PÚBLICOS.
# Uso: ./scripts/protect-main.sh [owner/repo]
set -euo pipefail

repo="${1:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
echo "Protegendo a branch main de $repo ..."

# Os "contexts" são os nomes (campo name:) dos jobs em .github/workflows/ci.yml.
gh api --method PUT "repos/$repo/branches/main/protection" \
  -H "Accept: application/vnd.github+json" \
  --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["Lint", "Secret Scan", "Test", "Build, Scan & Push"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
JSON

echo "OK. Checks obrigatórios:"
gh api "repos/$repo/branches/main/protection/required_status_checks" -q '.contexts[]'
