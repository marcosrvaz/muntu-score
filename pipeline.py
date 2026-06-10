import os

from muntu.analyzer import analyze
from muntu.signature import placement_plan, render_signature
from muntu.mixer import mux


def run(video_path: str, out_path: str = "outputs/scored.mp4",
        stems_dir: str = "assets/stems/default") -> str:
    os.makedirs("outputs", exist_ok=True)
    brief = analyze(video_path)
    plan = placement_plan(brief["cortes"], brief["duracao"])
    sig = render_signature(plan, brief["duracao"], stems_dir)
    sig.export("outputs/_audio.wav", format="wav")
    return mux(video_path, "outputs/_audio.wav", out_path)
