"""Tagueador — LLM/VLM etiqueta comerciais REAIS no tag-schema (learn-from-ads).

O "aprendizado" do sistema É a extração: nada de treinar modelo — o VLM assiste a
montagem (música/cena) e o áudio-model OUVE o ad (SFX/VO) e devolvem tags no schema
de muntu/tags.py. Este módulo é o SPIKE do crux (spec §2.7): validar que o modelo lê
registro fino (ironia, cultura, traço de voz) ANTES de construir banco. Reusa a infra
de visão de mood.py; gated na mesma key. Best-effort: falha -> [] / {}.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile

from muntu import mood, tags

MAX_TOKENS = 16000


PROMPT_MUSICA = (
    "You are a MUSIC SUPERVISOR analyzing ONE real TV commercial as a montage of N scenes "
    "labeled S1..SN (chronological). Your job is to TAG the music actually used, part by "
    "part, in a fixed schema — this builds a reference library of how real ads score story.\n"
    "For each musical part (a stretch with one musical treatment) return:\n"
    "  - span: which scenes it covers, free text (e.g. \"S1-S3, the party opening\").\n"
    "  - era: the SOUND's period (\"1980s\", \"1960s\", \"modern\").\n"
    "  - registro: short specific register/genre description of what you HEAR implied by "
    "the footage (\"cheesy 80s power ballad\", \"quirky comedic pizzicato\").\n"
    "  - ironia: \"sincero\" (straight emotion) | \"kitsch\" (deliberately cheesy/campy) | "
    "\"deadpan\" (straight music AGAINST absurdity) | \"parodia\" (mocks a genre).\n"
    "  - cultura: cultural/regional reference (\"brega\", \"bossa nova\", \"balkan brass\", "
    "\"surf rock\") or \"\".\n"
    "  - funcao: setup | build | payoff | reveal | transicao | assinatura.\n"
    "  - instrumentacao: up to 3 signature instruments.\n"
    "  - mode: major | minor | ambiguous.  - bpm: estimated int or null.\n"
    'Return ONLY JSON: {"partes": [{"span": "...", "era": "...", "registro": "...", '
    '"ironia": "...", "cultura": "...", "funcao": "...", "instrumentacao": [...], '
    '"mode": "...", "bpm": <int|null>}]}'
)


def disponivel() -> bool:
    """Mesmo gate do reader/mood (le o filme)."""
    return mood.clima_disponivel()


def _chama(content: list, max_tokens: int = MAX_TOKENS) -> dict:
    """POST OpenRouter (mesmo backend do reader) com content multimodal arbitrário."""
    import httpx
    r = httpx.post(
        url=mood.MOOD_URL,
        headers={"Authorization": f"Bearer {os.environ['MUNTU_MOOD_API_KEY']}"},
        json={"model": mood.MODEL, "max_tokens": max_tokens,
              "messages": [{"role": "user", "content": content}]},
        timeout=240.0,
    )
    r.raise_for_status()
    return mood._parse_json(r.json()["choices"][0]["message"]["content"])


def _normaliza_musica(data: dict) -> list[dict]:
    """Saída do VLM -> lista de TAGS_MUSICA validadas (+span). Item ilegível cai fora."""
    out = []
    for p in (data.get("partes") or []) if isinstance(data, dict) else []:
        if not isinstance(p, dict):
            continue
        t = tags.valida_tags(p, "music")
        t["span"] = (p.get("span") or "").strip()
        out.append(t)
    return out


def tagueia_musica(video_path: str, cortes: list[float], duracao: float) -> list[dict]:
    """Ad real -> tags de música por parte. [] se indisponível/falha (best-effort)."""
    if not disponivel():
        return []
    try:
        m = mood.montagem_do_filme(video_path, cortes, duracao)
        if m is None:
            return []
        b64 = base64.standard_b64encode(m).decode("utf-8")
        return _normaliza_musica(_chama([
            {"type": "text", "text": PROMPT_MUSICA},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ]))
    except Exception as e:                     # noqa: BLE001 — best-effort
        import sys
        print(f"[muntu] tagueador musica falhou ({type(e).__name__}: {e})", file=sys.stderr)
        return []
