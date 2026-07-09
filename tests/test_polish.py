import os

import pytest
from pydub import AudioSegment
from pydub.generators import Sine

import pipeline
from pipeline import run, _finaliza, HEADROOM_DB

SAMPLE = "assets/sample.mp4"


def test_finaliza_normaliza_sem_clipar():
    loud = Sine(440).to_audio_segment(duration=500)      # tom alto
    out = _finaliza(loud)
    assert out.max_dBFS <= -HEADROOM_DB + 0.5            # teto respeitado, nao estoura


def test_finaliza_silencio_nao_quebra():
    out = _finaliza(AudioSegment.silent(duration=1000))
    assert out.max_dBFS == float("-inf")                # segue silencio, sem exception


def test_run_formato_invalido_levanta_valueerror(tmp_path):
    fake = tmp_path / "nao_e_video.txt"
    fake.write_text("isto nao e um mp4")
    with pytest.raises(ValueError):
        run(str(fake), out_path=str(tmp_path / "out.mp4"))


@pytest.mark.skipif(not os.path.exists(SAMPLE), reason="sample.mp4 ausente")
def test_run_cama_falha_degrada_pro_skeleton(tmp_path, monkeypatch):
    # key presente (musica_disponivel True) mas gen falha (ex: free tier 402) -> nao crasha
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.setattr(pipeline.musica, "musica_disponivel", lambda: True)

    def _falha(*a, **k):
        raise RuntimeError("Music API is not available for free users")
    monkeypatch.setattr(pipeline.musica, "gera_musica", _falha)

    out = str(tmp_path / "scored.mp4")
    assert run(SAMPLE, out_path=out) == out
    assert os.path.exists(out) and os.path.getsize(out) > 0


@pytest.mark.skipif(not os.path.exists(SAMPLE), reason="sample.mp4 ausente")
def test_run_sem_cortes_nao_quebra(tmp_path, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("STABILITY_API_KEY", raising=False)
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.setattr(pipeline, "analyze",
                        lambda p: {"duracao": 5.0, "cortes": [], "cenas": [], "bpm_sugerido": 120})
    out = str(tmp_path / "scored.mp4")
    assert run(SAMPLE, out_path=out) == out
    assert os.path.exists(out) and os.path.getsize(out) > 0
