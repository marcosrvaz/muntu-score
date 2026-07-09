"""Identificação de faixa (AudD) — quando a piada É a música famosa.

O Gemini ouvindo descreve o registro mas não NOMEIA a faixa (o Danúbio Azul do Pepsi
saiu "glorioso tema orquestral romântico"); fingerprinting nomeia. Amostra 2-3 janelas
de ~12s do ad -> AudD -> matches únicos {titulo, artista, ano, generos}. O tagueador
injeta os matches no prompt como ground truth. Gated em AUDD_API_TOKEN; best-effort:
sem token/falha -> [] (o tagueamento segue só com o ouvido do Gemini).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

API_URL = "https://api.audd.io/"
JANELA_S = 12


def disponivel() -> bool:
    return bool(os.environ.get("AUDD_API_TOKEN"))


def _duracao(video_path: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "json", video_path], capture_output=True, text=True, check=True)
    return float(json.loads(r.stdout)["format"]["duration"])


def _trecho(video_path: str, inicio_s: float, dur_s: float = JANELA_S) -> str:
    """Janela de áudio do ad -> mp3 temp (AudD aceita upload direto). Chamador apaga."""
    fd, dst = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    subprocess.run(["ffmpeg", "-y", "-ss", str(inicio_s), "-i", video_path, "-t", str(dur_s),
                    "-ac", "1", "-b:a", "128k", dst], check=True, capture_output=True)
    return dst


def _match(payload) -> dict | None:
    """Resposta do AudD -> match enxuto; None sem match/ilegível."""
    r = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(r, dict):
        return None
    generos = []
    am = r.get("apple_music") or {}
    if isinstance(am, dict) and isinstance(am.get("genreNames"), list):
        generos = [g for g in am["genreNames"] if isinstance(g, str) and g and g != "Music"]
    return {"titulo": r.get("title") or "", "artista": r.get("artist") or "",
            "ano": (r.get("release_date") or "")[:4], "generos": generos}


def identifica(video_path: str, n_janelas: int = 3) -> list[dict]:
    """Ad -> faixas identificadas (únicas, com ~posição). [] best-effort."""
    if not disponivel():
        return []
    out, vistos = [], set()
    try:
        import httpx
        dur = _duracao(video_path)
        # começo / meio / fim-menos-um-pouco: cobre intro, corpo e a música do payoff
        inicios = [max(0.0, dur * f - JANELA_S / 2) for f in (0.15, 0.5, 0.85)][:n_janelas]
        for t0 in inicios:
            mp3 = _trecho(video_path, t0)
            try:
                with open(mp3, "rb") as f:
                    resp = httpx.post(API_URL,
                                      data={"api_token": os.environ["AUDD_API_TOKEN"],
                                            "return": "apple_music"},
                                      files={"file": f}, timeout=60.0)
                resp.raise_for_status()
                m = _match(resp.json())
                if m and (m["titulo"], m["artista"]) not in vistos:
                    vistos.add((m["titulo"], m["artista"]))
                    m["em_s"] = round(t0, 1)
                    out.append(m)
            finally:
                if os.path.exists(mp3):
                    os.remove(mp3)
    except Exception as e:                     # noqa: BLE001 — best-effort
        print(f"[muntu] faixa_id indisponivel ({type(e).__name__}: {e})", file=sys.stderr)
    return out
