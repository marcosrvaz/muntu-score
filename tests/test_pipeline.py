import json
import os
import subprocess

import pytest
from pydub import AudioSegment
from pydub.generators import Sine

import pipeline
from pipeline import run, _soma_camada, PRE_MIX_DB

SAMPLE = "assets/sample.mp4"


def _sem_provedores(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("STABILITY_API_KEY", raising=False)
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.delenv("MUNTU_MOOD_API_KEY", raising=False)


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


@pytest.mark.skipif(not os.path.exists(SAMPLE), reason="sample.mp4 placeholder ausente")
def test_pontuacao_sem_t_valido_nao_gasta_api_nem_derruba_run(tmp_path, monkeypatch, capsys):
    # PIN com 1 pontuacao sem "t" (malformada) + 1 valida -> a invalida deve ser pulada
    # ANTES de chamar gera_sfx (nao gasta API), sem derrubar o run.
    _sem_provedores(monkeypatch)
    chamadas = []

    def fake_gera_sfx(texto, duracao_s=1.5):
        chamadas.append(texto)
        return AudioSegment.silent(duration=100)

    monkeypatch.setattr(pipeline.sfx_gen, "sfx_disponivel", lambda: True)
    monkeypatch.setattr(pipeline.sfx_gen, "gera_sfx", fake_gera_sfx)

    timeline = {"partes": [], "pontuacoes": [
        {"sfx": "sem-tempo"},                    # malformada: sem "t"
        {"sfx": "com-tempo", "t": 1.0},          # valida
    ]}
    tl_path = tmp_path / "timeline.json"
    tl_path.write_text(json.dumps(timeline), encoding="utf-8")

    out = str(tmp_path / "scored.mp4")
    r = run(SAMPLE, out_path=out, pack="default", timeline_path=str(tl_path))

    assert r == out and os.path.exists(out)
    assert chamadas == ["com-tempo"]  # so a pontuacao valida gastou a API
    assert "sem tempo valido" in capsys.readouterr().err


@pytest.mark.skipif(not os.path.exists(SAMPLE), reason="sample.mp4 placeholder ausente")
def test_run_wav_intermediario_derivado_do_out_path_nao_sobra(tmp_path, monkeypatch):
    _sem_provedores(monkeypatch)
    out = str(tmp_path / "scored_x1y2.mp4")
    run(SAMPLE, out_path=out, pack="default")
    audio_esperado = str(tmp_path / "scored_x1y2_audio.wav")
    assert os.path.exists(out)
    assert not os.path.exists(audio_esperado)  # limpo apos o mux (try/finally)


@pytest.mark.skipif(not os.path.exists(SAMPLE), reason="sample.mp4 placeholder ausente")
def test_run_nao_escreve_no_wav_global_compartilhado(tmp_path, monkeypatch):
    # o bug: "outputs/_audio.wav" era um path global fixo -> 2 requests concorrentes (HF Space
    # multi-sessao) se sobrescreviam. Com out_path em tmp_path, o wav global nunca deve existir.
    _sem_provedores(monkeypatch)
    global_wav = "outputs/_audio.wav"
    os.makedirs("outputs", exist_ok=True)
    if os.path.exists(global_wav):
        os.remove(global_wav)
    out = str(tmp_path / "scored_g1.mp4")
    run(SAMPLE, out_path=out, pack="default")
    assert os.path.exists(out)
    assert not os.path.exists(global_wav)


@pytest.mark.skipif(not os.path.exists(SAMPLE), reason="sample.mp4 placeholder ausente")
def test_run_out_paths_distintos_nao_colidem(tmp_path, monkeypatch):
    _sem_provedores(monkeypatch)
    out_a = str(tmp_path / "req_a.mp4")
    out_b = str(tmp_path / "req_b.mp4")
    run(SAMPLE, out_path=out_a, pack="default")
    run(SAMPLE, out_path=out_b, pack="default")
    assert os.path.exists(out_a) and os.path.exists(out_b)
    assert os.path.getsize(out_a) > 0 and os.path.getsize(out_b) > 0
