# Venv de embeddings (torch CPU — pesado, ISOLADO do venv principal)

python3 -m venv .venv-embed
.venv-embed/bin/pip install -r scripts/embeddings/requirements.txt
export MUNTU_EMBED_PYTHON=$PWD/.venv-embed/bin/python

Modelo baixa no 1º uso: laion/clap-htsat-unfused (larger_clap_music DESCARTADO 2026-07-09
— checkpoint degenerado, ver docstring do embed_audio.py). Pin: transformers<5.
Spike 2026-07-08 provou: instala liso, roda CPU. `.venv-embed/` no .gitignore.
