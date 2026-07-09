"""Tonalidade + transposicao para overlays melodicos casarem a CAMA gerada.

Overlays NOSSOS (marcha de citacao, sax isolada) precisam tocar no MESMO tom da cama IA
(senao dissonam). O modelo gera a cama num tom que nao controlamos direito -> detectamos o
tom real (librosa: chroma + Krumhansl-Schmuckler) e transpomos o overlay (ffmpeg rubberband,
filtro `pitch=` — MESMA ferramenta do warp, so que pitch em vez de tempo).

Best-effort em TUDO: tom nulo/incerto -> NAO transpoe (uma transposicao sobre deteccao errada
introduz mais dissonancia do que deixar como esta). Overlays sao acentos; se nao conseguir
alinhar, overlay roda no tom original (ou e skipado pelo caller) — nunca derruba o binario.
"""
from __future__ import annotations

import os
import subprocess
import tempfile

from pydub import AudioSegment

# Krumhansl-Schmuckler: perfil de correlacao (grau 0 = tonica). Maior (Krumhansl 1990) e
# menor (Krumhansl & Castellano 1983; variantes na literatura, todas proximas). Indice 0-11 = C..B.
_PERFIL_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
_PERFIL_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
_NOTAS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

_LIMIAR_CORR = 0.40     # abaixo disso o tom e incerto -> None (nao arrisca transpor)


def _chroma_medio(seg) -> "list[float] | None":
    """Vetor chroma medio (12 dims, C..B). None se librosa/numpy ausentes ou audio vazio."""
    try:
        import librosa
        import numpy as np
    except ImportError:
        return None
    s = np.array(seg.get_array_of_samples()).astype(np.float32)
    if seg.channels == 2:
        s = s.reshape((-1, 2)).mean(axis=1)
    if s.size == 0:
        return None
    pico = float(np.abs(s).max())
    if pico > 0:
        s = s / pico
    chroma = librosa.feature.chroma_cqt(y=s, sr=seg.frame_rate, hop_length=512)
    return list(chroma.mean(axis=1))


def detecta_tom(seg) -> "str | None":
    """Tom dominante ('C major' / 'A minor') por Krumhansl-Schmuckler sobre o chroma medio.
    None se libs ausente, audio vazio, ou correlacao abaixo do limiar (tom incerto)."""
    ch = _chroma_medio(seg)
    if ch is None:
        return None
    try:
        import numpy as np
    except ImportError:
        return None
    ch = np.asarray(ch, dtype=float)
    if ch.sum() <= 0:
        return None
    melhor, melhor_corr = None, _LIMIAR_CORR
    for i in range(12):
        rot = np.roll(ch, -i)                 # alinha nota i como grau 0 (tonica)
        for perfil, modo in ((_PERFIL_MAJOR, "major"), (_PERFIL_MINOR, "minor")):
            corr = float(np.corrcoef(rot, perfil)[0, 1])
            if corr > melhor_corr:
                melhor_corr, melhor = corr, f"{_NOTAS[i]} {modo}"
    return melhor


def semitonos(de: "str | None", para: "str | None") -> int:
    """Delta em semitons (mod 12, menor distancia, -6..+6) da tonica de `de` -> `para`.
    Ignora modo (maior<->menor): transpoe so a tonica — best-effort (nao converte modo).
    0 se igual/invalido/parse falhar."""
    if not de or not para:
        return 0

    def _tonica(k: str) -> int | None:
        try:
            return _NOTAS.index(k.strip().split()[0])
        except (ValueError, IndexError):
            return None

    d, p = _tonica(de), _tonica(para)
    if d is None or p is None:
        return 0
    delta = (p - d) % 12
    return delta - 12 if delta > 6 else delta


def transpor(seg: AudioSegment, semitonos: float) -> AudioSegment:
    """Pitch-shift preservando tempo, via filtro ffmpeg `rubberband=pitch=` (mesmo filtro do
    warp). `rubberband pitch=` e um FATOR de escala (default 1, NAO semitons — probe
    2026-07-07: pitch=2 = +1 oitava). Logo fator = 2**(semitonos/12). Best-effort: 0 ou falha
    -> seg original."""
    if not semitonos:
        return seg
    fator = 2 ** (semitonos / 12)
    src, dst = tempfile.mktemp(suffix=".wav"), tempfile.mktemp(suffix=".wav")
    try:
        seg.export(src, format="wav")
        subprocess.run(
            ["ffmpeg", "-y", "-i", src, "-af", f"rubberband=pitch={fator}", dst],
            check=True, capture_output=True,
        )
        return AudioSegment.from_wav(dst)
    except Exception:                             # noqa: BLE001 — transposicao e best-effort
        return seg
    finally:
        for p in (src, dst):
            if os.path.exists(p):
                os.remove(p)


def alinha_tom(seg: AudioSegment, tom_alvo: "str | None") -> AudioSegment:
    """Transpoe `seg` ao `tom_alvo` (detecta o tom atual do proprio seg). Best-effort:
    tom_alvo nulo, ou tom de `seg` incerto -> seg inalterado (nao arrisca)."""
    if not tom_alvo:
        return seg
    de = detecta_tom(seg)
    if not de:
        return seg
    return transpor(seg, semitonos(de, tom_alvo))
