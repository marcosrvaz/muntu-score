from pydub import AudioSegment


def placement_plan(cuts: list, duracao: float, stem: str = "hit.wav") -> list:
    return [{"t": t, "stem": stem} for t in cuts]


def render_signature(plan: list, duracao: float, stems_dir: str) -> AudioSegment:
    track = AudioSegment.silent(duration=int(duracao * 1000))
    for p in plan:
        hit = AudioSegment.from_wav(f"{stems_dir}/{p['stem']}")
        track = track.overlay(hit, position=int(p["t"] * 1000))
    return track
