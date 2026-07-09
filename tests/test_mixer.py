import pytest

from muntu.mixer import mux


def test_mux_input_inexistente_levanta_valueerror_legivel(tmp_path):
    # ffmpeg falha com stderr cru e longo; o app.py so converte ValueError em gr.Error —
    # CalledProcessError vazaria a saida bruta do ffmpeg ate a UI.
    out = str(tmp_path / "out.mp4")
    with pytest.raises(ValueError) as exc:
        mux(str(tmp_path / "nao-existe.mp4"), str(tmp_path / "nao-existe.wav"), out)
    msg = str(exc.value)
    assert "ffmpeg" in msg.lower()
    assert "CalledProcessError" not in msg
