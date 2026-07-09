"""Banco curado learn-from-ads — Supabase + pgvector, retrieval híbrido (RRF).

2 vetores complementares por asset: text-embed do descritor (INTENÇÃO — cobre tudo,
incl. Epidemic-ponteiro) + CLAP do áudio (SOM — só own/artlist, de-riska o tagueador:
tag errada, som ainda acha). Fusão por RRF na função Postgres busca_hibrida (D1).
Text-embed via OpenRouter /api/v1/embeddings (mesma key do reader — D4); audio-embed
(CLAP) num venv dedicado torch-CPU (MUNTU_EMBED_PYTHON) via subprocess — torch não
entra no venv principal. Gated em SUPABASE_URL/SUPABASE_KEY; best-effort:
indisponível/falha -> []/None, pipeline nunca cai por causa do banco (padrão epidemic).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from muntu import tags as tags_mod

_TIMEOUT_EMBED = 600   # 1º uso baixa modelo (~2GB) — generoso de propósito


def banco_disponivel() -> bool:
    if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY")):
        return False
    try:
        import supabase  # noqa: F401
        return True
    except ImportError:
        return False


def _client():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def _roda_embed(script: str, payload: dict) -> list:
    """Bridge pro venv de embeddings. [] se venv não configurado/falha (best-effort)."""
    py = os.environ.get("MUNTU_EMBED_PYTHON")
    if not py:
        return []
    try:
        r = subprocess.run(
            [py, os.path.join("scripts", "embeddings", script)],
            input=json.dumps(payload), capture_output=True, text=True,
            timeout=_TIMEOUT_EMBED,
        )
        if r.returncode != 0:
            print(f"[muntu] {script} falhou: {r.stderr[-500:]}", file=sys.stderr)
            return []
        return json.loads(r.stdout)["vetores"]
    except Exception as e:                     # noqa: BLE001 — best-effort
        print(f"[muntu] {script} indisponivel ({type(e).__name__}: {e})", file=sys.stderr)
        return []


EMBED_URL = "https://openrouter.ai/api/v1/embeddings"
EMBED_MODEL = "openai/text-embedding-3-small"   # 1536-dim (D4)


def embed_texto(textos: list[str]) -> list[list[float]]:
    """Text-embedding via OpenRouter (endpoint OpenAI-compat, MESMA key do reader —
    zero key nova, zero modelo local). [] se key ausente/falha (best-effort)."""
    key = os.environ.get("MUNTU_MOOD_API_KEY")
    if not key or not textos:
        return []
    try:
        import httpx
        r = httpx.post(EMBED_URL, headers={"Authorization": f"Bearer {key}"},
                       json={"model": EMBED_MODEL, "input": textos}, timeout=60.0)
        r.raise_for_status()
        data = sorted(r.json()["data"], key=lambda d: d["index"])
        return [d["embedding"] for d in data]
    except Exception as e:                     # noqa: BLE001 — best-effort
        print(f"[muntu] embed_texto falhou ({type(e).__name__}: {e})", file=sys.stderr)
        return []


def embed_audio(paths: list[str]) -> list:
    return _roda_embed("embed_audio.py", {"paths": paths})


def insere_asset(asset_type: str, source: str, pointer: str, tags_dict: dict,
                 titulo: str = "", era: str = "", bpm=None, license_ok: bool = False,
                 audio_path: str | None = None):
    """Insere/atualiza 1 asset (upsert em source+pointer). Descritor+text_emb sempre;
    audio_emb quando há áudio local (own/artlist). None se banco/embeds indisponíveis."""
    if not banco_disponivel():
        return None
    t = tags_mod.valida_tags(tags_dict, "music" if asset_type == "music" else asset_type)
    desc = tags_mod.descritor(t, "music" if asset_type == "music" else asset_type)
    vt = embed_texto([desc])
    if not vt:
        return None
    va = None
    if audio_path:
        vs = embed_audio([audio_path])
        va = vs[0] if vs else None
    try:
        r = _client().table("assets").upsert({
            "asset_type": asset_type, "source": source, "pointer": pointer,
            "titulo": titulo, "era": era or t.get("era", ""), "bpm": bpm or t.get("bpm"),
            "license_ok": license_ok, "tags": t, "descritor": desc,
            "text_emb": vt[0], "audio_emb": va,
        }, on_conflict="source,pointer").execute()
        return r.data[0]["id"] if r.data else None
    except Exception as e:                     # noqa: BLE001 — best-effort
        print(f"[muntu] insere_asset falhou ({type(e).__name__}: {e})", file=sys.stderr)
        return None


def busca_hibrida(texto: str | None = None, audio_path: str | None = None,
                  tipo: str = "music", era: str | None = None,
                  so_licenciados: bool = False, n: int = 10,
                  peso_texto: float = 1.0, peso_audio: float = 1.0) -> list[dict]:
    """Retrieval híbrido: texto casa INTENÇÃO, áudio casa SOM, RRF funde (no Postgres).
    audio_path é o bridge A→B (D9): o draft gerado é a query de áudio. [] best-effort."""
    if not banco_disponivel() or not (texto or audio_path):
        return []
    q_text = None
    if texto:
        vt = embed_texto([texto])
        q_text = vt[0] if vt else None
    q_audio = None
    if audio_path:
        va = embed_audio([audio_path])
        q_audio = va[0] if va and va[0] else None
    if q_text is None and q_audio is None:
        return []
    try:
        r = _client().rpc("busca_hibrida", {
            "q_text": q_text, "q_audio": q_audio, "tipo": tipo, "filtro_era": era,
            "so_licenciados": so_licenciados, "n": n,
            "peso_texto": peso_texto, "peso_audio": peso_audio,
        }).execute()
        return r.data or []
    except Exception as e:                     # noqa: BLE001 — best-effort
        print(f"[muntu] busca_hibrida falhou ({type(e).__name__}: {e})", file=sys.stderr)
        return []


def _query_da_parte(parte: dict, era_filme: str = "") -> str:
    """Parte da timeline -> texto de query (mesmo vocabulário do descritor de ingestão:
    consistência query<->documento é o que faz o text-embed casar)."""
    return tags_mod.descritor({
        "era": era_filme, "registro": parte.get("mood") or parte.get("clima") or "",
        "ironia": parte.get("ironia"), "cultura": parte.get("cultura") or "",
        "funcao": parte.get("papel") or "",
        "instrumentacao": parte.get("instrumentacao") or [],
    })


def popula_beds(timeline: dict, so_score: bool = True) -> None:
    """A->B via banco curado: MESMO contrato de epidemic.popula_beds (muta partes
    setando bed_file -> reusa o encanamento PIN camada 2 de trilha.py, zero mudança lá).
    Ponteiro epidemic (sem áudio local) não vira bed aqui. Best-effort por parte."""
    if not banco_disponivel():
        return
    era = (timeline.get("era") or "").strip()
    for parte in timeline.get("partes") or []:
        if so_score and parte.get("tipo") == "diegetic":
            continue
        if parte.get("bed_file"):              # PIN do usuário vence sempre
            continue
        hits = busca_hibrida(texto=_query_da_parte(parte, era), tipo="music", n=3)
        for h in hits:
            p = h.get("pointer") or ""
            if not p.startswith("epidemic:") and os.path.exists(p):
                parte["bed_file"] = p
                break
