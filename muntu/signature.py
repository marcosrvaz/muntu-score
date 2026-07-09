from pydub import AudioSegment


def placement_plan(cuts: list, duracao: float, stem: str = "hit.wav") -> list:
    return [{"t": t, "stem": stem} for t in cuts]


def render_signature(plan: list, duracao: float, stems_dir: str) -> AudioSegment:
    track = AudioSegment.silent(duration=int(duracao * 1000))
    for p in plan:
        hit = AudioSegment.from_wav(f"{stems_dir}/{p['stem']}")
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
        hit = AudioSegment.from_wav(f"{stems_dir}/{a.get('stem', stem)}")
        ganho = a.get("ganho_db", 0)
        if ganho:
            hit = hit + ganho
        track = track.overlay(hit, position=int(a["t_audio"] * 1000))
    return track
