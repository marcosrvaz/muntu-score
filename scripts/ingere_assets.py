"""Ingestão do banco curado. Duas fontes:

1) Diretório de áudio local (own/artlist): cada faixa.mp3 com sidecar faixa.json
   (tags no schema TAGS_MUSICA de muntu/tags.py, escritas na curadoria) ->
   text_emb (descritor) + audio_emb (CLAP). Sem sidecar -> PULA e loga (curadoria
   é obrigatória: banco mal-etiquetado é lixo bem-organizado, spec §2.7).
2) --epidemic <json>: lista [{track_id, titulo, tags...}] -> ponteiro só-texto (D8).

Uso:
  python scripts/ingere_assets.py --dir <pasta_mp3> --source own [--license-ok]
  python scripts/ingere_assets.py --epidemic <curados.json>

GATE D10: rodar em MASSA só depois do veredito do spike (WS-B).
"""
import argparse
import glob
import json
import os

from muntu import banco


def ingere_dir(pasta: str, source: str, license_ok: bool):
    ok = pulados = 0
    for mp3 in sorted(glob.glob(os.path.join(pasta, "**", "*.mp3"), recursive=True)):
        sidecar = os.path.splitext(mp3)[0] + ".json"
        if not os.path.exists(sidecar):
            print(f"[ingere] SEM SIDECAR (pulado): {mp3}")
            pulados += 1
            continue
        with open(sidecar, encoding="utf-8") as f:
            t = json.load(f)
        rid = banco.insere_asset("music", source, mp3, t,
                                 titulo=os.path.basename(mp3), license_ok=license_ok,
                                 audio_path=mp3)
        print(f"[ingere] {'ok' if rid else 'FALHOU'}: {mp3}")
        ok += 1 if rid else 0
    print(f"[ingere] {ok} inseridos, {pulados} sem sidecar")


def ingere_epidemic(path: str):
    with open(path, encoding="utf-8") as f:
        faixas = json.load(f)
    for fx in faixas:
        rid = banco.insere_asset("music", "epidemic", f"epidemic:{fx['track_id']}",
                                 fx.get("tags") or {}, titulo=fx.get("titulo", ""))
        print(f"[ingere] {'ok' if rid else 'FALHOU'}: epidemic:{fx['track_id']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("--source", default="own", choices=["own", "artlist"])
    ap.add_argument("--license-ok", action="store_true")
    ap.add_argument("--epidemic")
    args = ap.parse_args()
    if args.dir:
        ingere_dir(args.dir, args.source, args.license_ok)
    if args.epidemic:
        ingere_epidemic(args.epidemic)
