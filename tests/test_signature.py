import os

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
