from muntu.reader import (
    _normaliza, _cobre, _merge_curtas, timeline_disponivel,
    salva_timeline, carrega_timeline, timeline_scratch_path,
)

CENAS = [{"start": 0.0, "end": 2.0}, {"start": 2.0, "end": 5.0},
         {"start": 5.0, "end": 9.0}, {"start": 9.0, "end": 12.0}]      # 4 cenas, 12s


def test_normaliza_converte_cenas_em_tempos_e_cobre():
    data = {"narrativa": "x", "era": "1980s", "climax": 3, "stop": 2, "partes": [
        {"cena_ini": 1, "cena_fim": 1, "tipo": "diegetic", "clima": "Joyful", "mood": "party", "papel": "setup"},
        {"cena_ini": 2, "cena_fim": 4, "tipo": "score", "clima": "comedic", "mood": "brega", "papel": "dev"}]}
    t = _normaliza(data, CENAS, 12.0)
    assert t["climax_cena"] == 3 and t["stop_cena"] == 2
    assert t["climax_t"] == 5.0 and t["stop_t"] == 2.0        # tempos das cenas 3 e 2
    assert t["comico"] is None                                # ausente -> None (fallback partes)
    assert t["partes"][0]["tipo"] == "diegetic" and t["partes"][0]["start"] == 0.0
    assert t["era"] == "1980s"                               # ano do filme (LLM) pro diegetico
    assert t["partes"][0]["clima"] == "joyful"               # vocab lowercased
    assert t["partes"][1]["confianca_valence"] == "media"    # ausente -> default media (gateia minor)
    assert t["partes"][1]["tipo"] == "score" and t["partes"][1]["mood"] == "brega"
    # cobertura contigua 0..12, sem buraco entre as partes
    assert t["partes"][0]["end"] == t["partes"][1]["start"]
    assert t["partes"][-1]["end"] == 12.0


def test_normaliza_tipo_default_score_e_stop_null():
    data = {"partes": [{"cena_ini": 1, "cena_fim": 4, "mood": "x"}], "stop": None}
    t = _normaliza(data, CENAS, 12.0)
    assert t["partes"][0]["tipo"] == "score"          # default quando ausente
    assert t["stop_cena"] is None


def test_normaliza_partes_vazio_cai_em_1_parte_score():
    t = _normaliza({"partes": []}, CENAS, 12.0)
    assert len(t["partes"]) == 1
    assert t["partes"][0]["tipo"] == "score"
    assert t["partes"][0]["start"] == 0.0 and t["partes"][0]["end"] == 12.0


def test_normaliza_clampa_cena_fora_do_range():
    t = _normaliza({"partes": [{"cena_ini": 0, "cena_fim": 99, "tipo": "score"}]}, CENAS, 12.0)
    assert t["partes"][0]["cena_ini"] == 1 and t["partes"][0]["cena_fim"] == 4


def test_cobre_cola_buraco_entre_partes():
    # partes com buraco (fim=5, proximo start=9) -> cola sem gap
    partes = [{"cena_ini": 1, "cena_fim": 2, "start": 0.0, "end": 5.0, "tipo": "score", "mood": "", "papel": ""},
              {"cena_ini": 4, "cena_fim": 4, "start": 9.0, "end": 12.0, "tipo": "score", "mood": "", "papel": ""}]
    out = _cobre(partes, CENAS, 12.0)
    assert out[1]["start"] == out[0]["end"]           # sem buraco
    assert out[-1]["end"] == 12.0


def test_merge_curtas_funde_sliver_na_anterior():
    # parte de 0.2s (viraria silencio ao gerar) e absorvida na anterior; cobertura ate o fim
    partes = [{"cena_ini": 1, "cena_fim": 4, "start": 0.0, "end": 6.8, "tipo": "diegetic"},
              {"cena_ini": 5, "cena_fim": 9, "start": 6.8, "end": 15.8, "tipo": "score"},
              {"cena_ini": 10, "cena_fim": 10, "start": 15.8, "end": 16.0, "tipo": "score"}]
    out = _merge_curtas(partes)
    assert len(out) == 2
    assert out[-1]["end"] == 16.0 and out[-1]["cena_fim"] == 10


def test_timeline_disponivel_segue_key(monkeypatch):
    monkeypatch.delenv("MUNTU_MOOD_API_KEY", raising=False)
    assert timeline_disponivel() is False
    monkeypatch.setenv("MUNTU_MOOD_API_KEY", "x")
    assert timeline_disponivel() is True


def test_normaliza_pontuacoes_cena_vira_tempo_e_filtra_invalidas():
    data = {"partes": [], "pontuacoes": [
        {"cena": 2, "sfx": "vinyl needle scratch", "motivo": "musica corta"},
        {"cena": 3, "sfx": "comedic wolf howl"},
        {"cena": 99, "sfx": "fora do range"},            # cena inexistente -> descartada
        {"cena": 1, "sfx": ""},                          # sem sfx -> descartada
        "lixo"]}                                         # nao-dict -> descartada
    t = _normaliza(data, CENAS, 12.0)
    assert len(t["pontuacoes"]) == 2
    assert t["pontuacoes"][0] == {"cena": 2, "t": 2.0, "sfx": "vinyl needle scratch", "motivo": "musica corta"}
    assert t["pontuacoes"][1]["t"] == 5.0 and t["pontuacoes"][1]["motivo"] == ""


def test_normaliza_sem_pontuacoes_vira_lista_vazia():
    assert _normaliza({"partes": []}, CENAS, 12.0)["pontuacoes"] == []
    assert _normaliza({"partes": []}, CENAS, 12.0)["citacoes"] == []


def test_normaliza_citacoes_cena_vira_tempo():
    # situacao classica (casamento) -> quote de melodia de dominio publico, cena -> tempo
    data = {"partes": [], "citacoes": [
        {"cena": 3, "melodia": "Bridal Chorus", "motivo": "casamento"},
        {"cena": 99, "melodia": "fora"},                 # cena inexistente -> descartada
        {"cena": 2, "melodia": ""}]}                     # sem melodia -> descartada
    t = _normaliza(data, CENAS, 12.0)
    assert t["citacoes"] == [{"cena": 3, "t": 5.0, "melodia": "Bridal Chorus", "motivo": "casamento"}]


def test_normaliza_comico_bool_passa_nao_bool_vira_none():
    assert _normaliza({"comico": True, "partes": []}, CENAS, 12.0)["comico"] is True
    assert _normaliza({"comico": False, "partes": []}, CENAS, 12.0)["comico"] is False
    assert _normaliza({"comico": "sim", "partes": []}, CENAS, 12.0)["comico"] is None


def test_scratch_path_deriva_do_stem():
    assert timeline_scratch_path("outputs/real.mp4") == "outputs/timeline_real.json"
    assert timeline_scratch_path("/a/b/pringles.mov") == "outputs/timeline_pringles.json"


def test_pin_roundtrip_salva_e_carrega(tmp_path):
    # PIN: gravar uma timeline lida e recarregar identica (regenera so o audio)
    p = str(tmp_path / "timeline_x.json")
    tl = _normaliza({"narrativa": "y", "climax": 3, "stop": 2, "partes": [
        {"cena_ini": 1, "cena_fim": 4, "tipo": "score", "clima": "comedic", "mood": "pizzicato"}]}, CENAS, 12.0)
    salva_timeline(tl, p)
    assert carrega_timeline(p) == tl


def test_carrega_timeline_inexistente_vira_vazio():
    assert carrega_timeline("nao/existe.json") == {}


def test_carrega_timeline_json_invalido_vira_vazio(tmp_path):
    p = tmp_path / "lixo.json"
    p.write_text("{ nao e json valido", encoding="utf-8")
    assert carrega_timeline(str(p)) == {}


def test_carrega_timeline_nao_dict_vira_vazio(tmp_path):
    p = tmp_path / "lista.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")     # JSON valido mas nao e timeline
    assert carrega_timeline(str(p)) == {}


def test_normaliza_stop_fim_t_e_o_corte_da_cena():
    t = _normaliza({"partes": [], "stop": 2}, CENAS, 12.0)
    assert t["stop_t"] == 2.0 and t["stop_fim_t"] == 5.0   # cena 2 = [2.0, 5.0)
    t2 = _normaliza({"partes": [], "stop": None}, CENAS, 12.0)
    assert t2["stop_fim_t"] is None
