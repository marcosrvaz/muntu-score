"""Warp pos-geracao — trava o tempo do bed na grade (BPM dos cortes).

Camada 2 do design (docs/composition-plan-design.md, "Alinhamento de BPM"): a musica IA
so aproxima o BPM pedido; esta etapa detecta o tempo REAL do bed (librosa.beat_track) e
time-stretch pra bater o BPM da grade — igual o warp do Ableton. Preserva pitch (ffmpeg
rubberband).

Principio: warp e best-effort NO BED (atmosfera). Quem carrega o sync exato continua sendo
os stems/acentos quantizados na grade. Falha (sem librosa, ffmpeg, tempo indetectavel, ou
desvio > cap) -> bed inalterado. Binario nunca quebra.

Cap de stretch = 6% (pesquisa). Desvio maior => provavel erro de oitava (ex: detectou 64 no
lugar de 128) -> dobra/divide o fator ate cair perto de 1.0; se ainda passar do cap, NAO
estica (artefato de stretch e pior que o leve desalinho).
"""
from __future__ import annotations

import os
import subprocess
import tempfile

CAP = 0.06          # stretch maximo (fracao) — alem disso, artefato audivel


def fator_de_warp(tempo_bed: float | None, bpm_grade: float | None,
                  cap: float = CAP) -> float | None:
    """Fator de time-stretch pra levar o tempo do bed ao BPM da grade.

    Dobra a oitava primeiro (detector de tempo erra por 2x/0.5x com frequencia), depois
    aplica o cap. Retorna o fator (ex: 1.033) ou None se nao vale esticar (ja alinhado
    apos oitava, fora do cap, ou entrada invalida).
    """
    if not tempo_bed or not bpm_grade or tempo_bed <= 0 or bpm_grade <= 0:
        return None
    ratio = bpm_grade / tempo_bed
    while ratio > 1.5:          # detectou metade do tempo -> alvo real e metade
        ratio /= 2.0
    while ratio < 0.67:         # detectou o dobro
        ratio *= 2.0
    if abs(ratio - 1.0) > cap:
        return None             # desvio real maior que o cap -> nao estica
    return round(ratio, 4)


def detecta_tempo(bed) -> float | None:
    """Tempo (BPM) do bed via librosa.beat_track. None se librosa ausente ou audio vazio."""
    try:
        import librosa
        import numpy as np
    except ImportError:
        return None
    samples = np.array(bed.get_array_of_samples()).astype(np.float32)
    if bed.channels == 2:
        samples = samples.reshape((-1, 2)).mean(axis=1)
    if samples.size == 0:
        return None
    pico = float(np.abs(samples).max())
    if pico > 0:
        samples = samples / pico
    tempo, _ = librosa.beat.beat_track(y=samples, sr=bed.frame_rate)
    tempo = float(np.atleast_1d(tempo)[0])      # librosa pode devolver array
    return tempo or None


def _rubberband(bed, tempo: float):
    """Time-stretch via ffmpeg rubberband (preserva pitch). tempo>1 = mais rapido/curto."""
    from pydub import AudioSegment

    src = tempfile.mktemp(suffix=".wav")
    dst = tempfile.mktemp(suffix=".wav")
    try:
        bed.export(src, format="wav")
        subprocess.run(
            ["ffmpeg", "-y", "-i", src, "-af", f"rubberband=tempo={tempo}", dst],
            check=True, capture_output=True,
        )
        return AudioSegment.from_wav(dst)
    finally:
        for p in (src, dst):
            if os.path.exists(p):
                os.remove(p)


def warp_bed(bed, bpm_grade: float, cap: float = CAP):
    """Trava o tempo do bed na grade. Best-effort: qualquer falha -> bed original."""
    tempo = detecta_tempo(bed)
    if tempo is None:
        return bed
    fator = fator_de_warp(tempo, bpm_grade, cap)
    if not fator or abs(fator - 1.0) < 1e-3:     # nada a corrigir (ja alinhado)
        return bed
    try:
        return _rubberband(bed, fator)
    except Exception:                            # noqa: BLE001 — warp e best-effort
        return bed
