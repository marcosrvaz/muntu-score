"""Assinatura sonora: renderiza stems fixos (hit/perc/riser) nos acentos do director.

LEGADO (hits nos cortes OFF, decisao 2026-07: estetica trailer): sem consumidor no
pipeline; mantido pra eventual modo "hits" futuro. Testes cobrem o contrato pra
reativacao. Nao expandir sem reativar.
"""
import os

from pydub import AudioSegment


def placement_plan(cuts: list, duracao: float, stem: str = "hit.wav") -> list:
    return [{"t": t, "stem": stem} for t in cuts]


def render_signature(plan: list, duracao: float, stems_dir: str) -> AudioSegment:
    track = AudioSegment.silent(duration=int(duracao * 1000))
    for p in plan:
        hit = AudioSegment.from_wav(os.path.join(stems_dir, os.path.basename(str(p["stem"]))))
        track = track.overlay(hit, position=int(p["t"] * 1000))
    return track


def render_acentos(acentos: list, duracao: float, stems_dir: str,
                   stem: str = "hit.wav") -> AudioSegment:
    """Renderiza os acentos do director nos `t_audio` (ja quantizados na grade).

    Cada acento carrega `ganho_db` (impact=0, perc=-6). O stem e o de assinatura;
    selecao por papel/manifest e Task 9 (por ora, stem unico default).
    """
    track = AudioSegment.silent(duration=int(duracao * 1000))
    for a in acentos:
        hit = AudioSegment.from_wav(
            os.path.join(stems_dir, os.path.basename(str(a.get("stem", stem))))
        )
        ganho = a.get("ganho_db", 0)
        if ganho:
            hit = hit + ganho
        track = track.overlay(hit, position=int(a["t_audio"] * 1000))
    return track
