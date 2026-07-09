"""Gera SFX one-shot a partir de TEXTO (ElevenLabs Sound Effects API).

O texto vem do mapa (sfx_map); a posicao no tempo e trabalho do pipeline (frame-tight).
O gerador so faz o som decontextual — nao pedimos sync a ele. Mesma key da musica
(ELEVENLABS_API_KEY) + precisa da permissao `sound_generation` na key. Gated + cache por
(texto, duracao). Best-effort: falha -> None (corte fica sem SFX, binario intacto).
"""
from __future__ import annotations

import hashlib
import io
import os

from pydub import AudioSegment

CACHE_DIR = "outputs/cache/sfx"
DUR_S = 1.2                                # one-shot curto; o transiente cai no corte
SUFIXO = ", clean, isolated, no music, no voice"   # reforca sound-design puro


def sfx_disponivel() -> bool:
    if not os.environ.get("ELEVENLABS_API_KEY"):
        return False
    try:
        import elevenlabs  # noqa: F401
        return True
    except ImportError:
        return False


def _cache_path(texto: str, dur: float, cache_dir: str) -> str:
    h = hashlib.sha1(f"{texto}|{dur}".encode()).hexdigest()[:16]
    return os.path.join(cache_dir, h + ".mp3")


def gera_sfx(texto: str, duracao_s: float = DUR_S,
             cache_dir: str = CACHE_DIR) -> AudioSegment | None:
    """One-shot de SFX do `texto`. None (best-effort) se indisponivel ou falhar."""
    if not sfx_disponivel() or not texto:
        return None
    os.makedirs(cache_dir, exist_ok=True)
    cache = _cache_path(texto, duracao_s, cache_dir)
    if os.path.exists(cache):
        return AudioSegment.from_file(cache)
    try:
        from elevenlabs import ElevenLabs

        client = ElevenLabs()
        out = client.text_to_sound_effects.convert(
            text=f"{texto}{SUFIXO}", duration_seconds=duracao_s)
        data = out if isinstance(out, (bytes, bytearray)) else b"".join(out)
        seg = AudioSegment.from_file(io.BytesIO(data))
        seg.export(cache, format="mp3")
        return seg
    except Exception as e:                     # noqa: BLE001 — best-effort
        import sys
        print(f"[muntu] sfx '{texto[:30]}' falhou ({type(e).__name__}: {e})", file=sys.stderr)
        return None
