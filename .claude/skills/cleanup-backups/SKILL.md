---
name: cleanup-backups
description: Lista lixo versionado / nao-ignorado no repo (.backups/, *.bak, outputs/, __pycache__) e sugere entradas de .gitignore. Read-only por padrao — so remove/edita com confirmacao. Invoque com /cleanup-backups.
disable-model-invocation: true
---

# cleanup-backups

Faz higiene do repo Muntu Score. **Nao remove nada sem confirmacao explicita.**

## Passos

1. Detecta lixo:
   ```bash
   git ls-files | grep -E '\.bak($|-)|/\.backups/|__pycache__|\.pyc$'   # lixo JA versionado (pior caso)
   find . -not -path './.git/*' \( -name '*.bak*' -o -name '__pycache__' -o -path './.backups/*' -o -path './outputs/*' \) 2>/dev/null
   ```
2. Le `.gitignore` atual. Compara com o que apareceu.
3. **Reporta** em duas listas:
   - **Versionado que devia sair** (`git rm --cached`) — ex: `muntu/sfx_map.py.bak-verbose-2026-07-07`.
   - **Nao-ignorado que devia entrar no `.gitignore`** — ex: `.backups/`, `outputs/`, `*.bak`, `__pycache__/`, `.pytest_cache/`.
4. Sugere o bloco a adicionar no `.gitignore`:
   ```gitignore
   .backups/
   outputs/
   *.bak
   *.bak-*
   __pycache__/
   .pytest_cache/
   ```
5. **Pergunta** antes de executar `git rm --cached` ou editar `.gitignore`. Nunca `rm -rf`. Nunca toca `.env`.
