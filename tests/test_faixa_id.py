"""Identificação de faixa (AudD) — parsing e gates, sem rede."""
from muntu import faixa_id, tagueador


def test_indisponivel_sem_token(monkeypatch):
    monkeypatch.delenv("AUDD_API_TOKEN", raising=False)
    assert faixa_id.disponivel() is False
    assert faixa_id.identifica("fake.mp4") == []


def test_match_parseia_resultado():
    payload = {"status": "success", "result": {
        "title": "An der schönen blauen Donau", "artist": "Johann Strauss II",
        "release_date": "1867-02-15",
        "apple_music": {"genreNames": ["Classical", "Music", "Waltz"]}}}
    m = faixa_id._match(payload)
    assert m["titulo"].startswith("An der")
    assert m["ano"] == "1867"
    assert m["generos"] == ["Classical", "Waltz"]      # "Music" cai fora


def test_match_sem_resultado():
    assert faixa_id._match({"status": "success", "result": None}) is None
    assert faixa_id._match("lixo") is None


def test_bloco_faixas_no_prompt():
    faixas = [{"titulo": "Blue Danube", "artista": "Strauss", "ano": "1867",
               "generos": ["Classical"], "em_s": 24.0}]
    bloco = tagueador._bloco_faixas(faixas)
    assert "GROUND TRUTH" in bloco
    assert "Blue Danube" in bloco and "24.0s" in bloco
    assert tagueador._bloco_faixas([]) == ""
    assert tagueador._bloco_faixas(None) == ""
