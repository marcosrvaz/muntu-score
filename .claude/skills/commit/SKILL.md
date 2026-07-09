---
name: commit
description: Cria commit git no padrao deste repo — mensagem concisa em pt-BR com prefixo semantico, SEM trailer Co-Authored-By Claude (prova publica de autoria). Invoque com /commit quando for commitar.
disable-model-invocation: true
---

# commit

Cria um commit seguindo as convencoes do Muntu Score.

## Regras duras

1. **NUNCA** adiciona `Co-Authored-By: Claude` nem `Generated with Claude Code`. Este repo e prova publica de autoria do Marcos — commits so como Marcos.
2. Mensagem em **pt-BR**, concisa, prefixo semantico: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.
3. **NUNCA** commita `.env`, secrets, `.backups/`, `outputs/`, `*.bak`, `venv/`.
4. Nao commita sem pedido — este skill JA e o pedido explicito.

## Passos

1. `git status` + `git diff --staged` (e `git diff` pra unstaged). Entende o que mudou.
2. Se nada staged, `git add` so os arquivos relevantes a mudanca (nunca `git add -A` cego — evita secrets/lixo).
3. Confirma que nenhum path sensivel entrou: `git diff --staged --name-only | grep -E '\.env|\.bak|/outputs/|/\.backups/'` deve vir vazio. Se nao, aborta e avisa.
4. Roda `python -m pytest -q` se houve mudanca em `muntu/` ou `pipeline.py`. Falhou = avisa antes de commitar.
5. Commit com HEREDOC (uma mensagem, sem trailer):

```bash
git commit -m "$(cat <<'EOF'
feat: descricao concisa da mudanca
EOF
)"
```

6. Reporta o hash e a mensagem. Nao pusheia sem pedido.
