from muntu.mood import (
    clima_disponivel, _cenas_de_cortes, aplica_saida, analisa_clima, _parse_json,
)


def test_parse_json_limpo():
    assert _parse_json('{"mood": "comedic", "energias": [2, 5]}') == {
        "mood": "comedic", "energias": [2, 5]}


def test_parse_json_cerca_markdown():
    txt = '```json\n{"mood": "playful", "energias": [1]}\n```'
    assert _parse_json(txt) == {"mood": "playful", "energias": [1]}


def test_parse_json_prosa_em_volta():
    # GLM et al. as vezes embrulham em prosa apesar do json_object
    txt = 'Result: {"mood": "epic", "energias": [5]} done.'
    assert _parse_json(txt) == {"mood": "epic", "energias": [5]}


def test_aplica_saida_clampa_energia_fora_de_faixa():
    cenas = _cenas_de_cortes([4.0], duracao=8.0)                # 2 cenas
    out = aplica_saida(cenas, "tense", [0, 9])                  # fora de 1-5
    assert [c["energia"] for c in out] == [1, 5]


def test_clima_indisponivel_sem_key(monkeypatch):
    monkeypatch.delenv("MUNTU_MOOD_API_KEY", raising=False)
    assert clima_disponivel() is False


def test_cenas_de_cortes_alinha_start_no_corte():
    cenas = _cenas_de_cortes([3.0, 6.0], duracao=9.0)
    assert [(c["start"], c["end"]) for c in cenas] == [(0.0, 3.0), (3.0, 6.0), (6.0, 9.0)]
    # cena 2 e 3 comecam num corte (casa com director._clima_forte)
    assert cenas[1]["start"] == 3.0 and cenas[2]["start"] == 6.0


def test_cenas_de_cortes_sem_corte():
    cenas = _cenas_de_cortes([], duracao=5.0)
    assert cenas == [{"start": 0.0, "end": 5.0}]


def test_aplica_saida_mood_global_e_energia_por_cena():
    cenas = _cenas_de_cortes([4.0, 8.0], duracao=12.0)          # 3 cenas
    out = aplica_saida(cenas, "comedic", [2, 5, 3])
    assert all(c["clima"] == "comedic" for c in out)            # mood do FILME em todas
    assert [c["energia"] for c in out] == [2, 5, 3]


def test_aplica_saida_energia_faltante_vira_3():
    cenas = _cenas_de_cortes([4.0, 8.0], duracao=12.0)          # 3 cenas
    out = aplica_saida(cenas, "playful", [4])                   # so 1 energia
    assert [c["energia"] for c in out] == [4, 3, 3]


def test_aplica_saida_mood_vazio_vira_neutral():
    cenas = _cenas_de_cortes([], duracao=5.0)
    out = aplica_saida(cenas, "", [])
    assert out[0]["clima"] == "neutral" and out[0]["energia"] == 3


def test_aplica_saida_normaliza_case_e_espaco():
    # mood cru do VLM ("Comedic", " SAD ") tem que casar com o vocab lowercased
    cenas = _cenas_de_cortes([], duracao=5.0)
    out = aplica_saida(cenas, " Comedic ", [3])
    assert out[0]["clima"] == "comedic"


def test_aplica_saida_mood_fora_do_vocab_vira_neutral():
    cenas = _cenas_de_cortes([], duracao=5.0)
    out = aplica_saida(cenas, "xyz_fora_do_vocab", [3])
    assert out[0]["clima"] == "neutral"


def test_analisa_clima_sem_key_devolve_vazio(monkeypatch):
    monkeypatch.delenv("MUNTU_MOOD_API_KEY", raising=False)
    assert analisa_clima("qualquer.mp4", [3.0], 6.0) == []
