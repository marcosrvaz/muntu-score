import os

import pytest
from pydub import AudioSegment
from pydub.generators import Sine

from muntu.signature import placement_plan, render_acentos, render_signature


def test_placement_at_cuts():
    cuts = [1.0, 2.5, 4.0]
    plan = placement_plan(cuts, duracao=5.0)
    assert [p["t"] for p in plan] == cuts
    assert all(p["stem"] == "hit.wav" for p in plan)


def test_render_signature_bloqueia_path_traversal(tmp_path, monkeypatch):
    stems_dir = str(tmp_path / "stems")
    os.makedirs(stems_dir)
    caminhos = []

    def fake_from_wav(path):
        caminhos.append(path)
        from pydub import AudioSegment
        return AudioSegment.silent(duration=100)

    monkeypatch.setattr("muntu.signature.AudioSegment.from_wav", fake_from_wav)

    plan = [{"t": 0.0, "stem": "../fora.wav"}]
    render_signature(plan, duracao=1.0, stems_dir=stems_dir)

    assert len(caminhos) == 1
    assert os.path.dirname(caminhos[0]) == stems_dir


def test_render_acentos_bloqueia_path_traversal(tmp_path, monkeypatch):
    stems_dir = str(tmp_path / "stems")
    os.makedirs(stems_dir)
    caminhos = []

    def fake_from_wav(path):
        caminhos.append(path)
        from pydub import AudioSegment
        return AudioSegment.silent(duration=100)

    monkeypatch.setattr("muntu.signature.AudioSegment.from_wav", fake_from_wav)

    acentos = [{"t_audio": 0.0, "stem": "../../etc/fora.wav", "ganho_db": 0}]
    render_acentos(acentos, duracao=1.0, stems_dir=stems_dir)

    assert len(caminhos) == 1
    assert os.path.dirname(caminhos[0]) == stems_dir


def test_render_acentos_aplica_ganho_db(tmp_path, monkeypatch):
    stems_dir = str(tmp_path / "stems")
    os.makedirs(stems_dir)

    def fake_from_wav(path):
        return Sine(440).to_audio_segment(duration=100)

    monkeypatch.setattr("muntu.signature.AudioSegment.from_wav", fake_from_wav)

    overlays = []
    original_overlay = AudioSegment.overlay

    def fake_overlay(self, seg, **kwargs):
        overlays.append(seg)
        return original_overlay(self, seg, **kwargs)

    monkeypatch.setattr("muntu.signature.AudioSegment.overlay", fake_overlay)

    base_dbfs = fake_from_wav("").dBFS
    acentos = [{"t_audio": 0.0, "stem": "hit.wav", "ganho_db": -6}]
    render_acentos(acentos, duracao=1.0, stems_dir=stems_dir)

    assert len(overlays) == 1
    assert overlays[0].dBFS == pytest.approx(base_dbfs - 6, abs=0.01)


def test_render_acentos_stem_override_por_acento(tmp_path, monkeypatch):
    stems_dir = str(tmp_path / "stems")
    os.makedirs(stems_dir)
    caminhos = []

    def fake_from_wav(path):
        caminhos.append(path)
        return AudioSegment.silent(duration=100)

    monkeypatch.setattr("muntu.signature.AudioSegment.from_wav", fake_from_wav)

    acentos = [{"t_audio": 0.0, "stem": "riser.wav", "ganho_db": 0}]
    render_acentos(acentos, duracao=1.0, stems_dir=stems_dir, stem="hit.wav")

    assert len(caminhos) == 1
    assert os.path.basename(caminhos[0]) == "riser.wav"


def test_render_acentos_t_audio_alem_da_duracao_nao_estende_track(tmp_path, monkeypatch):
    stems_dir = str(tmp_path / "stems")
    os.makedirs(stems_dir)

    def fake_from_wav(path):
        return AudioSegment.silent(duration=200)

    monkeypatch.setattr("muntu.signature.AudioSegment.from_wav", fake_from_wav)

    acentos = [{"t_audio": 5.0, "stem": "hit.wav", "ganho_db": 0}]
    track = render_acentos(acentos, duracao=1.0, stems_dir=stems_dir)

    assert len(track) == 1000
