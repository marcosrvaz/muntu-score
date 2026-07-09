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


def test_normaliza_audio_valida_sfx_e_vo():
    data = {"sfx": {"ambiencia": "indoor party", "eventos": ["glass clink", ""],
                    "assinatura": "cork pop"},
            "vo": {"genero": "male", "idade": "middle-aged", "tom": "deadpan-comico",
                   "timbre": "warm", "pace": "slow", "sotaque": "neutro BR", "energia": 2}}
    out = tagueador._normaliza_audio(data)
    assert out["sfx"]["eventos"] == ["glass clink"]
    assert out["vo"]["tom"] == "deadpan-comico"


def test_normaliza_audio_sem_vo():
    out = tagueador._normaliza_audio({"sfx": {"ambiencia": "street"}, "vo": None})
    assert out["vo"] is None
    assert out["sfx"]["ambiencia"] == "street"
    assert tagueador._normaliza_audio("lixo") == {"sfx": None, "vo": None}
