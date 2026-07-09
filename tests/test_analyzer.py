import scenedetect

import muntu.analyzer as analyzer_mod
from muntu.analyzer import analyze


def test_analyze_returns_brief():
    brief = analyze("assets/sample.mp4")
    assert brief["duracao"] > 0
    assert isinstance(brief["cortes"], list)
    # cortes em ordem crescente, dentro da duracao
    assert brief["cortes"] == sorted(brief["cortes"])
    assert all(0 <= t <= brief["duracao"] for t in brief["cortes"])
    assert "bpm_sugerido" not in brief   # campo morto (nenhum consumidor)


def test_analyze_reusa_o_video_ja_aberto_na_deteccao(monkeypatch):
    # bug antigo: open_video(path) + detect(path, ...) decodificavam o arquivo 2x (detect()
    # reabre por conta propria). O fix passa o VideoStream ja aberto pro SceneManager.
    video_aberto = analyzer_mod.open_video("assets/sample.mp4")
    monkeypatch.setattr(analyzer_mod, "open_video", lambda path: video_aberto)

    recebido = {}
    original_detect_scenes = scenedetect.SceneManager.detect_scenes

    def spy(self, video, **kw):
        recebido["video"] = video
        return original_detect_scenes(self, video=video, **kw)

    monkeypatch.setattr(scenedetect.SceneManager, "detect_scenes", spy)
    analyze("assets/sample.mp4")
    assert recebido["video"] is video_aberto   # mesmo objeto, nao reaberto por path
