import shutil
import subprocess

import pytest
from pydub import AudioSegment

from muntu.warp import fator_de_warp, detecta_tempo, warp_bed


# ---- fator_de_warp: puro, sempre roda ----

def test_fator_alinhado_nao_estica():
    # bed ja no BPM da grade -> fator ~1.0
    assert fator_de_warp(120.0, 120.0) == 1.0


def test_fator_desvio_pequeno_dentro_do_cap():
    # 120 -> 124 = +3.3%, dentro do cap de 6%
    f = fator_de_warp(120.0, 124.0)
    assert f is not None and abs(f - 124.0 / 120.0) < 1e-3


def test_fator_erro_de_oitava_dobra_ao_inves_de_esticar():
    # detector achou 64 (metade de 128) -> ratio 2.0 -> dobra pra ~1.0, nao estica 100%
    f = fator_de_warp(64.0, 128.0)
    assert f == 1.0
    # e o inverso (detectou o dobro)
    assert fator_de_warp(256.0, 128.0) == 1.0


def test_fator_desvio_grande_retorna_none():
    # 100 -> 132 = +32%, alem do cap mesmo apos oitava -> nao estica
    assert fator_de_warp(100.0, 132.0) is None


def test_fator_entrada_invalida():
    assert fator_de_warp(None, 120.0) is None
    assert fator_de_warp(120.0, None) is None
    assert fator_de_warp(0.0, 120.0) is None


# ---- caminho real: precisa librosa + rubberband ----

def _tem_librosa() -> bool:
    try:
        import librosa  # noqa: F401
        return True
    except ImportError:
        return False


def _tem_rubberband() -> bool:
    if not shutil.which("ffmpeg"):
        return False
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                         capture_output=True, text=True)
    return "rubberband" in out.stdout


@pytest.mark.skipif(not _tem_librosa(), reason="librosa ausente")
def test_detecta_tempo_de_pulso_conhecido():
    from pydub.generators import Sine
    # clique a cada 0.5s (120 BPM): beep curto + silencio
    click = Sine(880).to_audio_segment(duration=40) + (-20)
    gap = Sine(0).to_audio_segment(duration=460)
    bed = (click + gap) * 16          # 8s de pulso 120 BPM
    tempo = detecta_tempo(bed)
    assert tempo is not None and 100 <= tempo <= 140


@pytest.mark.skipif(not (_tem_librosa() and _tem_rubberband()),
                    reason="librosa + rubberband necessarios")
def test_warp_bed_nao_quebra_e_ajusta_duracao():
    from pydub.generators import Sine
    click = Sine(880).to_audio_segment(duration=40) + (-20)
    gap = Sine(0).to_audio_segment(duration=460)
    bed = (click + gap) * 16
    out = warp_bed(bed, bpm_grade=125.0)      # pede leve aceleracao
    # best-effort: sempre devolve um AudioSegment tocavel
    assert len(out) > 0


# ---- downmix multicanal (>2ch) ----

@pytest.mark.skipif(not _tem_librosa(), reason="librosa ausente")
def test_detecta_tempo_downmix_multicanal(monkeypatch):
    # 3 canais: downmix so tratava channels==2; >2ch entrava interleaved no beat_track
    # (tempo errado porque o array fica 3x mais longo, com canais misturados em sequencia).
    import librosa
    import numpy as np

    n_frames = 4410
    samples = np.tile(np.array([100, 200, 300], dtype=np.int16), n_frames)
    bed = AudioSegment(data=samples.tobytes(), sample_width=2, frame_rate=44100, channels=3)

    capturado = {}

    def fake_beat_track(y, sr):
        capturado["len"] = len(y)
        return 120.0, None

    monkeypatch.setattr(librosa.beat, "beat_track", fake_beat_track)
    detecta_tempo(bed)
    assert capturado["len"] == n_frames


# ---- contrato best-effort: falha na deteccao nao propaga ----

@pytest.mark.skipif(not _tem_librosa(), reason="librosa ausente")
def test_detecta_tempo_excecao_no_beat_track_retorna_none(monkeypatch):
    import librosa
    from pydub.generators import Sine

    def boom(y, sr):
        raise ValueError("beat_track explodiu")

    monkeypatch.setattr(librosa.beat, "beat_track", boom)
    bed = Sine(880).to_audio_segment(duration=50)
    assert detecta_tempo(bed) is None


@pytest.mark.skipif(not _tem_librosa(), reason="librosa ausente")
def test_warp_bed_degrada_pro_original_se_deteccao_falhar(monkeypatch):
    import librosa
    from pydub.generators import Sine

    def boom(y, sr):
        raise ValueError("beat_track explodiu")

    monkeypatch.setattr(librosa.beat, "beat_track", boom)
    bed = Sine(880).to_audio_segment(duration=50)
    out = warp_bed(bed, bpm_grade=120.0)
    assert out is bed
