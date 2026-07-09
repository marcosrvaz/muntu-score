# Venv de embeddings (torch CPU — pesado, ISOLADO do venv principal)

python3 -m venv .venv-embed
.venv-embed/bin/pip install -r scripts/embeddings/requirements.txt
export MUNTU_EMBED_PYTHON=$PWD/.venv-embed/bin/python

Modelo baixa no 1º uso: laion/larger_clap_music (~2GB).
Spike 2026-07-08 provou: instala liso, roda CPU. `.venv-embed/` no .gitignore.
