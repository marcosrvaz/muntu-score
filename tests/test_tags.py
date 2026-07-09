"""Tag-schema — vocabulário compartilhado (valida_tags/descritor)."""
from muntu import tags


def test_valida_tags_musica_default_de_lixo():
    # entrada lixo -> schema default, nunca levanta (best-effort)
    out = tags.valida_tags(None)
    assert out["ironia"] == "sincero"
    assert out["mode"] == "ambiguous"
    assert out["instrumentacao"] == []
    assert out["bpm"] is None


def test_valida_tags_clampa_enums_e_listas():
    out = tags.valida_tags({
        "ironia": "KITSCH", "mode": "banana", "funcao": "payoff",
        "instrumentacao": ["sax", "", "piano", "tuba", "extra"],
        "bpm": 118.0, "campo_desconhecido": "x",
    })
    assert out["ironia"] == "kitsch"          # case-insensitive
    assert out["mode"] == "ambiguous"          # fora do vocab -> default
    assert out["funcao"] == "payoff"
    assert out["instrumentacao"] == ["sax", "piano", "tuba"]   # máx 3, vazio fora
    assert out["bpm"] == 118
    assert "campo_desconhecido" not in out


def test_valida_tags_vo_clampa_energia():
    assert tags.valida_tags({"energia": 99}, "vo")["energia"] == 5
    assert tags.valida_tags({"energia": "x"}, "vo")["energia"] == 3


def test_normaliza_ironia():
    assert tags.normaliza_ironia("deadpan") == "deadpan"
    assert tags.normaliza_ironia("") == "sincero"
    assert tags.normaliza_ironia(None) == "sincero"
    assert tags.normaliza_ironia(42) == "sincero"


def test_descritor_ordem_fixa_e_omite_vazios():
    d = tags.descritor({"era": "1980s", "registro": "power ballad", "ironia": "kitsch",
                        "instrumentacao": ["saxophone"], "bpm": 72})
    assert d == "1980s, power ballad, kitsch, saxophone, 72 BPM"
    # sincero/ambiguous = neutros -> omitidos
    assert "sincero" not in tags.descritor({"registro": "piano"})
    assert "ambiguous" not in tags.descritor({"registro": "piano"})


def test_descritor_sfx_e_vo():
    assert tags.descritor({"ambiencia": "party crowd", "eventos": ["glass clink"]},
                          "sfx") == "party crowd, glass clink"
    assert "energy 4/5" in tags.descritor({"genero": "female", "energia": 4}, "vo")
