import os
import subprocess

import pytest
from pydub import AudioSegment
from pydub.generators import Sine

from pipeline import run, _soma_camada, PRE_MIX_DB

SAMPLE = "assets/sample.mp4"


def _tem_audio(path: str) -> bool:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    return "audio" in out.stdout


@pytest.mark.skipif(not os.path.exists(SAMPLE), reason="sample.mp4 placeholder ausente")
def test_pipeline_end_to_end_produz_video_com_audio(tmp_path, monkeypatch):
    # sem credencial -> caminho skeleton (so stems), mesma pipeline/director
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("STABILITY_API_KEY", raising=False)
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    out = str(tmp_path / "scored.mp4")
    r = run(SAMPLE, out_path=out, pack="default")
    assert r == out and os.path.exists(out) and os.path.getsize(out) > 0
    assert _tem_audio(out), "saida deve ter trilha (stream de audio)"


@pytest.mark.skipif(not os.path.exists(SAMPLE), reason="sample.mp4 placeholder ausente")
def test_pipeline_auto_sem_vlm_cai_no_default(tmp_path, monkeypatch):
    # pack='auto' sem VLM (sem token) nao quebra -> resolve pra default, produz video
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("STABILITY_API_KEY", raising=False)
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    out = str(tmp_path / "auto.mp4")
    r = run(SAMPLE, out_path=out, pack="auto")
    assert r == out and os.path.exists(out) and _tem_audio(out)


def test_soma_camada_com_headroom_nao_satura():
    # duas senoides full-scale (-0.5 dBFS) em fase: overlay cru satura o clamp int (flat-top)
    seg = Sine(440).to_audio_segment(duration=200)
    seg = seg.apply_gain(-0.5 - seg.max_dBFS)
    cru = AudioSegment.silent(duration=200).overlay(seg).overlay(seg)
    assert cru.max_dBFS > -0.1  # saturou no teto (0 dBFS)

    # via _soma_camada, com a base ja atenuada uma vez (como run() faz em base = ... + PRE_MIX_DB)
    base = AudioSegment.silent(duration=200) + PRE_MIX_DB
    resultado = _soma_camada(base, seg, gain_db=0)
    resultado = _soma_camada(resultado, seg, gain_db=0)

    assert resultado.max_dBFS < -0.1  # sem flat-top
    assert resultado.max_dBFS < cru.max_dBFS  # nitidamente abaixo da soma crua (que saturou)
