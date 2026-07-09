"""Tagueador — VLM/audio-model etiqueta ads REAIS no tag-schema (spike do crux)."""
from muntu import tagueador


def test_normaliza_musica_valida_cada_parte():
    data = {"partes": [
        {"span": "opening party", "era": "1980s", "registro": "cheesy synth pop",
         "ironia": "KITSCH", "cultura": "brega", "instrumentacao": ["synth", "sax"],
         "mode": "major", "bpm": 118},
        {"span": "payoff", "registro": "quirky pizzicato", "ironia": "banana"},
    ]}
    out = tagueador._normaliza_musica(data)
    assert len(out) == 2
    assert out[0]["ironia"] == "kitsch" and out[0]["bpm"] == 118
    assert out[1]["ironia"] == "sincero"           # enum inválido -> default
    assert out[0]["span"] == "opening party"


def test_normaliza_musica_lixo_nao_levanta():
    assert tagueador._normaliza_musica({}) == []
    assert tagueador._normaliza_musica({"partes": ["x", None]}) == []
