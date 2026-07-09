"""Mapa de SFX por tempo — o VLM le o filme e diz QUE som cada corte pede.

Escapa do teto de sync do foley cego (video->audio, MMAudio/ThinkSound): aqui o QUANDO
vem do analyzer (tempo de corte, frame-tight) e o QUE vem do VLM; a posicao no tempo e
trabalho NOSSO (igual aos stems, que ja sincam). O gerador so faz o one-shot decontextual;
nao pedimos sync a ele. Ver muntu-sfx-cena-nao-mood.

Reusa a infra de visao do mood (montagem S1..SN -> VLM Gemini 2.5 Pro). Gated na
mesma key (MUNTU_MOOD_API_KEY). Tags curtas por cena (prova de ouvido 2026-07-07:
tag >= ensaio no ElevenLabs text-to-SFX) -> max_tokens baixo basta; ensaio rico
estourava (finish=length -> content vazio). Best-effort: falha -> [] (sem camada
de SFX, binario intacto).
"""
from __future__ import annotations

import base64
import os

from muntu import mood

MAX_TOKENS = 8000    # tags curtas por cena (prova de ouvido 2026-07-07): tag >= ensaio no
#                      ElevenLabs text-to-SFX; ensaio rico so estourava token (finish=length
#                      -> content vazio). ~16 cenas x 2 tags x ~15 tok ~= 500 + JSON; 8k = gordura.

PROMPT = (
    "Montage of N scenes from ONE short TV commercial, labeled S1..SN in order "
    "(left-to-right, top-to-bottom).\n"
    "LOOK at each frame and decide TWO sound layers for that scene. Ignore the advertised "
    "brand/product — read the actual SETTING and ACTION shown.\n\n"
    "EACH FIELD IS A SHORT TAG, ONE PHRASE, MAX ~10 WORDS. NOT a paragraph. The downstream "
    "is a sound-effects generator — it wants a concise noun phrase, not an essay.\n\n"
    "1) AMBIENCE — room tone of the location: \"[indoor|outdoor] [place] [tone]\". First "
    "match what is on screen (a closed room is NOT a street). Examples: \"indoor crowded "
    "party hall\", \"small quiet bedroom\", \"indoor diner interior\", \"outdoor garden daytime\", "
    "\"outdoor city street\". NO music. NO intelligible speech.\n"
    "2) FOLEY — the single visible physical ACTION as a short tag, or \"\" if none clear. "
    "Examples: \"hand opens foil can\", \"footsteps walking\", \"cup set on table\".\n\n"
    'Return ONLY JSON: {"cenas": [{"ambiencia": "...", "foley": "..."}, ...]} — one object '
    "per scene, in order. Keep each value under ~10 words."
)


def mapa_disponivel() -> bool:
    """Mesmo gate do VLM de mood (le o filme)."""
    return mood.clima_disponivel()


def _chama(b64: str) -> dict:
    import httpx

    r = httpx.post(
        mood.MOOD_URL,
        headers={"Authorization": f"Bearer {os.environ['MUNTU_MOOD_API_KEY']}"},
        json={
            "model": mood.MODEL,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ]}],
        },
        timeout=180.0,
    )
    r.raise_for_status()
    return mood._parse_json(r.json()["choices"][0]["message"]["content"])


def gera_mapa(video_path: str, cortes: list[float], duracao: float) -> list[dict]:
    """[{t, dur, ambiencia, foley}] por cena. `t`/`dur` = span da cena (exato, analyzer).

    Duas camadas: `ambiencia` cobre a cena (room tone do local); `foley` = som de acao
    pontual no corte ("" se sem acao clara). [] se indisponivel.
    """
    if not mapa_disponivel():
        return []
    cenas = mood._cenas_de_cortes(cortes, duracao)
    try:
        m = mood.montagem_do_filme(video_path, cortes, duracao)   # extraida 1x, compartilhada
        if m is None:
            return []
        b64 = base64.standard_b64encode(m).decode("utf-8")
        out = _chama(b64).get("cenas", [])
        eventos = []
        for i, c in enumerate(cenas):
            d = out[i] if i < len(out) else {}
            eventos.append({
                "t": c["start"],
                "dur": c["end"] - c["start"],
                "ambiencia": (d.get("ambiencia") or "").strip(),
                "foley": (d.get("foley") or "").strip(),
            })
        return eventos
    except Exception as e:                     # noqa: BLE001 — best-effort
        import sys
        print(f"[muntu] sfx-map indisponivel ({type(e).__name__}: {e})", file=sys.stderr)
        return []
