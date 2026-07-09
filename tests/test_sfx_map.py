from muntu import sfx_map


def test_prompt_ped_brevidade():
    # prova de ouvido 2026-07-07: tag curta >= ensaio no ElevenLabs text-to-SFX;
    # o prompt deve pedir TAGS, nao paragrafos (paragrafo estourava token).
    assert "MAX ~10 WORDS" in sfx_map.PROMPT
    assert "NOT a paragraph" in sfx_map.PROMPT


def test_gera_mapa_happy(monkeypatch):
    monkeypatch.setattr(sfx_map, "mapa_disponivel", lambda: True)
    monkeypatch.setattr(
        sfx_map.mood, "_cenas_de_cortes",
        lambda cortes, dur: [{"start": 0.0, "end": 3.0}, {"start": 3.0, "end": 6.0}],
    )
    monkeypatch.setattr(sfx_map.mood, "montagem_do_filme", lambda v, c, d: b"x")
    monkeypatch.setattr(
        sfx_map, "_chama",
        lambda b64: {"cenas": [
            {"ambiencia": "indoor party hall", "foley": "hand opens foil can"},
            {"ambiencia": "outdoor city street", "foley": ""},
        ]},
    )
    ev = sfx_map.gera_mapa("fake.mp4", [0.0, 3.0], 6.0)
    assert len(ev) == 2
    assert ev[0]["t"] == 0.0 and ev[0]["dur"] == 3.0
    assert ev[0]["ambiencia"] == "indoor party hall"
    assert ev[0]["foley"] == "hand opens foil can"
    assert ev[1]["t"] == 3.0 and ev[1]["foley"] == ""


def test_gera_mapa_indisponivel(monkeypatch):
    monkeypatch.setattr(sfx_map, "mapa_disponivel", lambda: False)
    assert sfx_map.gera_mapa("x.mp4", [0.0], 1.0) == []


def test_gera_mapa_best_effort(monkeypatch):
    # _chama estourando -> [] (camada SFX off, binario intacto)
    monkeypatch.setattr(sfx_map, "mapa_disponivel", lambda: True)
    monkeypatch.setattr(
        sfx_map.mood, "_cenas_de_cortes",
        lambda cortes, dur: [{"start": 0.0, "end": 1.0}],
    )
    monkeypatch.setattr(sfx_map.mood, "montagem_do_filme", lambda v, c, d: b"x")

    def boom(_b64):
        raise RuntimeError("boom")

    monkeypatch.setattr(sfx_map, "_chama", boom)
    assert sfx_map.gera_mapa("x.mp4", [0.0], 1.0) == []
