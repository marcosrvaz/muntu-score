from pydub import AudioSegment
from pydub.generators import Sine

import muntu.trilha as trilha
from muntu.trilha import (
    monta_trilha, _prompt_da_parte, _aplica_stop, _plano_da_parte,
    _asset_citacao, _overlay_citacoes,
)


def _fake_bed(prompt, dur, **k):
    return Sine(440).to_audio_segment(duration=int(dur * 1000))


def test_corta_silencio_inicial():
    # REGRA universal: bed com dead-air no inicio entra no beat (corta o silencio)
    sil = AudioSegment.silent(duration=800)
    tom = Sine(440).to_audio_segment(duration=1000)
    out = trilha._corta_silencio_inicial(sil + tom)
    assert abs(len(out) - 1000) < 120                 # sobra ~1s de tom, sem os 800ms de silencio
    assert len(trilha._corta_silencio_inicial(tom)) == len(tom)   # sem silencio -> intacto
    # cap: nao come mais que o teto (fade-in musical longo preservado)
    long_sil = AudioSegment.silent(duration=trilha.SILENCIO_TETO_MS + 1500)
    out2 = trilha._corta_silencio_inicial(long_sil + tom)
    assert len(out2) >= 1500                           # cortou no maximo o teto


def test_monta_trilha_cobre_duracao_e_tem_audio(monkeypatch):
    monkeypatch.setattr(trilha.musica, "gera_musica", _fake_bed)
    tl = {"partes": [
        {"cena_ini": 1, "cena_fim": 1, "start": 0.0, "end": 3.0, "tipo": "diegetic", "mood": "party"},
        {"cena_ini": 2, "cena_fim": 3, "start": 3.0, "end": 10.0, "tipo": "score", "mood": "brega"}],
        "stop_t": None}
    out = monta_trilha(tl, 10.0)
    assert abs(len(out) - 10000) < 50            # dura == duracao do filme
    assert out.max_dBFS != float("-inf")         # tem audio (partes geradas)


def test_monta_trilha_aplica_stop(monkeypatch):
    monkeypatch.setattr(trilha.musica, "gera_musica", _fake_bed)
    tl = {"partes": [{"cena_ini": 1, "cena_fim": 2, "start": 0.0, "end": 10.0,
                      "tipo": "score", "mood": "x"}], "stop_t": 4.0}
    out = monta_trilha(tl, 10.0)
    janela = out[4200:5000]                      # dentro do STOP [4.0, 5.2]s
    assert janela.max_dBFS == float("-inf") or janela.max_dBFS < -40   # musica calou


def test_monta_trilha_parte_que_falha_nao_derruba(monkeypatch):
    chamadas = {"n": 0}

    def _meio_falha(prompt, dur, **k):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise RuntimeError("402 free tier")
        return Sine(440).to_audio_segment(duration=int(dur * 1000))
    monkeypatch.setattr(trilha.musica, "gera_musica", _meio_falha)
    tl = {"partes": [
        {"cena_ini": 1, "cena_fim": 1, "start": 0.0, "end": 4.0, "tipo": "score", "mood": "a"},
        {"cena_ini": 2, "cena_fim": 2, "start": 4.0, "end": 10.0, "tipo": "score", "mood": "b"}],
        "stop_t": None}
    out = monta_trilha(tl, 10.0)
    assert abs(len(out) - 10000) < 50            # parte 1 falhou (silencio), parte 2 entrou


def test_prompt_da_parte_diegetic_usa_freetext_ignora_pack():
    # diegetico: mesmo com clima que casaria um pack, usa a direcao livre (source music
    # e especifico do filme) + marca "source music".
    s = _prompt_da_parte({"tipo": "diegetic", "clima": "joyful", "mood": "muffled house music"})
    assert "muffled house music" in s and "source music" in s and "instrumental only" in s


def test_prompt_da_parte_score_usa_pack_quando_clima_casa():
    # score + clima 'comedic' casa o pack curado -> usa o prompt_template, NAO o free-text
    s = _prompt_da_parte({"tipo": "score", "clima": "comedic", "mood": "ZZZ_freetext"})
    assert "ZZZ_freetext" not in s                       # pack dirigiu, nao o free-text
    assert "instrumental only" in s and "sits under voiceover" in s


def test_stop_diegetico_nao_apaga_score_seguinte(monkeypatch):
    # power-down na parte diegetica NAO pode apagar o score que vem depois (bug do fim-da-trilha)
    monkeypatch.setattr(trilha.musica, "gera_musica", _fake_bed)
    tl = {"partes": [
        {"cena_ini": 1, "cena_fim": 2, "start": 0.0, "end": 5.0, "tipo": "diegetic", "clima": "comedic", "mood": "x"},
        {"cena_ini": 3, "cena_fim": 4, "start": 5.0, "end": 10.0, "tipo": "score", "clima": "nostalgic", "mood": "y"}],
        "stop_t": 3.0}
    out = monta_trilha(tl, 10.0)
    # o power-down mata a fonte diegetica, mas o SCORE [5-10] tem que sobreviver (era o bug)
    assert out[6000:9000].max_dBFS != float("-inf")


def test_era_retro_forca_a_epoca():
    # filme RETRO -> trilha obrigatoriamente da epoca (injeta a era)
    s = _prompt_da_parte({"tipo": "diegetic", "clima": "comedic", "mood": "party pop"}, era="1980s")
    assert "1980s" in s and "source music" in s


def test_era_moderna_nao_forca():
    # filme MODERNO -> nao forca a era; trilha livre (retro so se o mood pedir, via reader)
    s = _prompt_da_parte({"tipo": "diegetic", "clima": "comedic", "mood": "party pop"}, era="modern day")
    assert "modern day" not in s


def test_prompt_da_parte_clima_sem_pack_cai_no_freetext():
    s = _prompt_da_parte({"tipo": "score", "clima": "zzz_inexistente", "mood": "tense strings"})
    assert "tense strings" in s                          # clima nao casou -> direcao livre


def test_gate_minor_sem_confianca_alta_cai_no_ambiguo():
    # 'tense' -> pack tenso (minor). Sem confianca alta -> ambiguo, NAO o minor (evita inverter
    # o clima numa leitura fraca de valence).
    s = _prompt_da_parte({"tipo": "score", "clima": "tense", "confianca_valence": "baixa", "mood": "x"})
    assert "minor key" not in s
    assert "neither clearly major nor minor" in s
    # default 'media' tambem gateia (so 'alta' libera o minor)
    s2 = _prompt_da_parte({"tipo": "score", "clima": "tense", "mood": "x"})
    assert "neither clearly major nor minor" in s2


def test_gate_minor_com_confianca_alta_dispara_o_pack():
    s = _prompt_da_parte({"tipo": "score", "clima": "tense", "confianca_valence": "alta", "mood": "x"})
    assert "minor key" in s                              # pack tenso (minor) disparou


def test_gate_nao_afeta_pack_major():
    # comedic -> playful (major): gate so olha minor, entao dispara sem confianca alta
    s = _prompt_da_parte({"tipo": "score", "clima": "comedic", "mood": "x"})
    assert "major key" in s


def test_stop_diegetico_nao_comico_nao_para(monkeypatch):
    # stop em parte DIEGETICA nao-comica -> NAO para (som do ambiente segue; sem gag)
    monkeypatch.setattr(trilha.musica, "gera_musica", _fake_bed)
    tl = {"partes": [
        {"cena_ini": 1, "cena_fim": 2, "start": 0.0, "end": 5.0, "tipo": "diegetic", "clima": "tender", "mood": "x"},
        {"cena_ini": 3, "cena_fim": 4, "start": 5.0, "end": 10.0, "tipo": "score", "mood": "y"}],
        "stop_t": 2.0}
    out = monta_trilha(tl, 10.0)
    assert out[2200:3000].max_dBFS != float("-inf")   # diegetico continua tocando


def test_stop_diegetico_comico_desliga_a_fonte(monkeypatch):
    # stop em parte DIEGETICA COMICA -> gag: fonte desliga (wind-down) e silencia depois
    monkeypatch.setattr(trilha.musica, "gera_musica", _fake_bed)
    tl = {"partes": [{"cena_ini": 1, "cena_fim": 4, "start": 0.0, "end": 10.0,
                      "tipo": "diegetic", "clima": "comedic", "mood": "x"}], "stop_t": 4.0}
    out = monta_trilha(tl, 10.0)
    assert out[4050:4600].max_dBFS != float("-inf")            # wind-down 'morrendo', nao corte seco
    assert out[6000:9000].max_dBFS == float("-inf") or out[6000:9000].max_dBFS < -50   # fonte off


def test_rabo_morto_detecta_fim_apagado():
    corpo = Sine(440).to_audio_segment(duration=8000)
    vivo = corpo + Sine(440).to_audio_segment(duration=1500)
    morto = corpo + AudioSegment.silent(duration=1500)
    assert trilha._rabo_morto(vivo) is False
    assert trilha._rabo_morto(morto) is True
    assert trilha._rabo_morto(Sine(440).to_audio_segment(duration=2000)) is False  # curta: skip


def test_garante_rabo_vivo_reroll_pega_a_melhor(monkeypatch):
    morto = Sine(440).to_audio_segment(duration=8000) + AudioSegment.silent(duration=1500)
    vivo = Sine(440).to_audio_segment(duration=9500)
    monkeypatch.setattr(trilha.musica, "gera_musica", lambda *a, **k: vivo)
    plan = {"positive_global_styles": ["x"], "sections": []}
    out = trilha._garante_rabo_vivo(morto, "p", plan, 9.5, {"cena_ini": 5})
    assert out[-1500:].dBFS > morto[-1500:].dBFS          # re-roll vivo venceu
    # rabo ja vivo: nao re-gera (gera_musica nao e chamado)
    monkeypatch.setattr(trilha.musica, "gera_musica",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("nao devia gerar")))
    assert trilha._garante_rabo_vivo(vivo, "p", plan, 9.5, {}) is vivo


def test_bed_file_pin_de_camada_2(monkeypatch, tmp_path):
    # PIN de audio: parte com bed_file usa o arquivo travado, NAO gera
    f = tmp_path / "bed_bom.wav"
    Sine(440).to_audio_segment(duration=10000).export(str(f), format="wav")
    monkeypatch.setattr(trilha.musica, "gera_musica",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("nao devia gerar")))
    tl = {"partes": [{"cena_ini": 1, "cena_fim": 4, "start": 0.0, "end": 10.0,
                      "tipo": "score", "mood": "x", "bed_file": str(f)}], "stop_t": None}
    out = monta_trilha(tl, 10.0)
    assert out.max_dBFS != float("-inf")                  # audio do arquivo entrou


def test_diegetico_abaixa_nivel_sound_design():
    seg = Sine(1000).to_audio_segment(duration=1000)   # 1kHz passa no band-limit
    out = trilha._diegetico(seg)
    assert out.dBFS < seg.dBFS - 8                      # bem sob a trilha (nivel de sound design)


def test_aplica_stop_preserva_duracao():
    seg = Sine(440).to_audio_segment(duration=8000)
    out = _aplica_stop(seg, 3000, janela=1000)
    assert abs(len(out) - 8000) < 5


def test_comico_film_level_dispara_gag_com_partes_retas(monkeypatch):
    # comedia tocada RETA: nenhuma parte tem clima/mood comico, mas o FILME e comedia
    # (timeline["comico"]=True do reader) -> gag do vinil dispara mesmo assim (era o bug:
    # filme_comico inferido so das partes -> False -> stop diegetico nao parava).
    monkeypatch.setattr(trilha.musica, "gera_musica", _fake_bed)
    tl = {"comico": True, "partes": [
        {"cena_ini": 1, "cena_fim": 3, "start": 0.0, "end": 6.0, "tipo": "diegetic", "clima": "energetic", "mood": "party pop"},
        {"cena_ini": 4, "cena_fim": 6, "start": 6.0, "end": 12.0, "tipo": "score", "clima": "romantic", "mood": "epic 80s ballad"}],
        "stop_t": 3.0}
    out = monta_trilha(tl, 12.0)
    # wind-down estica (~800ms -> ~1.7s); apos ele, silencio ate o fim da parte diegetica
    assert out[5100:5900].max_dBFS == float("-inf") or out[5100:5900].max_dBFS < -50  # fonte off
    assert out[7000:11000].max_dBFS != float("-inf")  # score seguinte intacto


def test_comico_false_do_reader_veta_o_fallback_das_partes(monkeypatch):
    # reader disse NAO-comedia -> gag nao dispara mesmo com parte de clima comedic
    monkeypatch.setattr(trilha.musica, "gera_musica", _fake_bed)
    tl = {"comico": False, "partes": [{"cena_ini": 1, "cena_fim": 4, "start": 0.0, "end": 10.0,
                                       "tipo": "diegetic", "clima": "comedic", "mood": "x"}], "stop_t": 4.0}
    out = monta_trilha(tl, 10.0)
    assert out[6000:9000].max_dBFS != float("-inf")   # diegetico segue tocando (sem gag)


def test_comico_ausente_cai_no_fallback_das_partes(monkeypatch):
    # sem campo comico (timeline antiga/PIN editado a mao) -> heuristica das partes decide
    monkeypatch.setattr(trilha.musica, "gera_musica", _fake_bed)
    tl = {"partes": [{"cena_ini": 1, "cena_fim": 4, "start": 0.0, "end": 10.0,
                      "tipo": "diegetic", "clima": "comedic", "mood": "x"}], "stop_t": 4.0}
    out = monta_trilha(tl, 10.0)
    assert out[6000:9000].max_dBFS == float("-inf") or out[6000:9000].max_dBFS < -50  # gag disparou


def test_plano_da_parte_ancora_apice_no_climax():
    # score de 6.8-16.0 com climax em 14.14 -> Build ate ~14.14 + Apice ate o fim
    p = {"start": 6.8, "end": 16.0, "tipo": "score"}
    plan = _plano_da_parte(p, "balada 80s", 14.14)
    assert plan is not None and len(plan["sections"]) == 3
    assert plan["sections"][0]["section_name"] == "Build"
    assert plan["sections"][1]["section_name"] == "Apice"
    assert plan["sections"][2]["section_name"] == "Cauda"       # descartavel: modelo morre nela
    total = sum(s["duration_ms"] for s in plan["sections"])
    assert abs(total - (9200 + trilha.CAUDA_MS)) <= 1   # parte + cauda descartavel
    # apice respeita SEC_MIN da borda (climax 14.14 -> apice desliza pra 13.0 = end-3.0)
    assert plan["sections"][1]["duration_ms"] >= 3000
    assert plan["positive_global_styles"] == ["balada 80s"]


def test_plano_secoes_alinham_nos_cortes_de_cena():
    # o FILME dita a estrutura: cortes dentro da parte viram fronteiras de secao
    # (musica troca de movimento NO corte); corte < SEC_MIN da fronteira anterior e fundido
    p = {"start": 6.8, "end": 16.0, "tipo": "score", "clima": "romantic",
         "confianca_valence": "alta"}
    # climax 14.14 -> ancora clampa em 13.0 (end-SEC_MIN). Cortes: 3.0 fora da parte;
    # 10.0 sobrevive; 11.5 a 1.5s da ancora -> removido por ela; 15.0 a 1s do fim -> fundido
    cortes = [3.0, 10.0, 11.5, 15.0]
    plan = _plano_da_parte(p, "balada", 14.14, cortes=cortes)
    nomes = [s["section_name"] for s in plan["sections"]]
    assert nomes == ["Build", "Build 2", "Apice", "Cauda"]
    durs = [s["duration_ms"] for s in plan["sections"]]
    assert durs[0] == 3200                       # 6.8 -> 10.0 (corte de cena)
    assert durs[1] == 3000                       # 10.0 -> 13.0 (ancora do apice)
    assert sum(durs[:-1]) == 9200                # parte exata; cauda descartavel a parte
    # sem cortes: degrada pro Build/Apice de antes
    plan2 = _plano_da_parte(p, "balada", 14.14)
    assert [s["section_name"] for s in plan2["sections"]] == ["Build", "Apice", "Cauda"]


def test_plano_da_parte_none_quando_nao_cabe_arco():
    assert _plano_da_parte({"start": 0.0, "end": 6.0, "tipo": "diegetic"}, "x", 3.0) is None   # diegetico
    assert _plano_da_parte({"start": 0.0, "end": 5.0, "tipo": "score"}, "x", 3.0) is None      # curta (<2*SEC_MIN)
    assert _plano_da_parte({"start": 0.0, "end": 10.0, "tipo": "score"}, "x", 12.0) is None    # climax fora
    assert _plano_da_parte({"start": 0.0, "end": 10.0, "tipo": "score"}, "x", None) is None    # sem climax


def test_prompt_comico_infleta_score_pra_kitsch():
    s = _prompt_da_parte({"tipo": "score", "clima": "romantic", "confianca_valence": "alta",
                          "mood": "x"}, comico=True)
    assert "kitsch" in s and "tongue-in-cheek" in s
    # diegetico NAO ganha o clause (o registro comico da festa e escolha do reader no mood)
    d = _prompt_da_parte({"tipo": "diegetic", "clima": "energetic", "mood": "party"}, comico=True)
    assert "tongue-in-cheek" not in d


def test_kitsch_nao_commita_valence_sobre_o_gate():
    # gate segurou o minor (tense + confianca baixa) -> bed AMBIGUO; kitsch "over-sentimental"
    # commitaria a valence que o gate segurou (regra 2 dos pesos β) -> clause NAO entra
    s = _prompt_da_parte({"tipo": "score", "clima": "tense", "confianca_valence": "baixa",
                          "mood": "x"}, comico=True)
    assert "neither clearly major nor minor" in s
    assert "tongue-in-cheek" not in s and "over-sentimental" not in s


def test_kitsch_nao_commita_valence_sobre_o_gate_retro():
    # mesmo gate, mas filme RETRO: a linha `base = f"{era} {base}"` cria string NOVA ->
    # guard por identidade (`base is not AMBIGUO`) falha e o kitsch vazava sobre o bed
    # AMBIGUO do gate. O guard correto e semantico (`not gated`), nao identidade de objeto.
    s = _prompt_da_parte({"tipo": "score", "clima": "tense", "confianca_valence": "baixa",
                          "mood": "x"}, era="1980s", comico=True)
    assert "neither clearly major nor minor" in s
    assert "tongue-in-cheek" not in s and "over-sentimental" not in s


def test_plano_da_parte_sobe_t_manda_no_arco():
    # direcao explicita "cresce no casamento": sobe_t da parte ancora o Apice, nao o climax
    p = {"start": 6.8, "end": 16.0, "tipo": "score", "clima": "romantic",
         "confianca_valence": "alta", "sobe_t": 11.97}
    plan = _plano_da_parte(p, "balada", 14.14)
    dur_build = plan["sections"][0]["duration_ms"]
    assert abs(dur_build - (11.97 - 6.8) * 1000) < 20     # Build acaba no casamento (sobe_t)
    # sem sobe_t: ancora no climax (clampado a SEC_MIN da borda: 16.0-3.0=13.0)
    p2 = {"start": 6.8, "end": 16.0, "tipo": "score", "clima": "romantic", "confianca_valence": "alta"}
    plan2 = _plano_da_parte(p2, "balada", 14.14)
    assert abs(plan2["sections"][0]["duration_ms"] - (13.0 - 6.8) * 1000) < 20


def test_plano_remove_clean_ending_do_global():
    # "clean ending" (template, musica unica) apaga a faixa no fim — o apice da parte fecha
    # no fim, o beat cairia no silencio. Plano por parte troca por full intensity.
    p = {"start": 6.8, "end": 16.0, "tipo": "score", "clima": "romantic", "confianca_valence": "alta"}
    plan = _plano_da_parte(p, "balada 80s, clean ending.", 14.14)
    g = plan["positive_global_styles"][0]
    assert "clean ending" not in g and "full intensity" in g


def test_citacao_nao_e_mais_tecida_no_plano():
    # overlay GARANTIDO substituiu o weave de prompt: _plano_da_parte nao toca mais em citacoes
    # (o "incorporating X motif" migrava payoff pra Cauda descartada; reconcilia-chunks). Citacao
    # = AUDIO nosso, alinhado ao tom, em _overlay_citacoes + tons.py.
    p = {"start": 6.8, "end": 16.0, "tipo": "score", "clima": "romantic",
         "confianca_valence": "alta", "sobe_t": 11.97}
    plan = _plano_da_parte(p, "balada", 14.14)
    estilos = [e for s in plan["sections"] for e in s["positive_local_styles"]]
    assert not any("melodic motif" in e for e in estilos)        # weave removido


def test_asset_citacao_mapeia_wedding_e_valida_arquivo(tmp_path):
    # keyword casa -> caminho; arquivo ausente -> None; sem keyword -> None
    assert _asset_citacao("sem relacao", assets_dir=str(tmp_path)) is None
    assert _asset_citacao("uplifting wedding march", assets_dir="/dir/que/nao/existe") is None
    (tmp_path / "marcha_nupcial.mp3").write_bytes(b"")
    p = _asset_citacao("uplifting ceremonial wedding march", assets_dir=str(tmp_path))
    assert p is not None and p.endswith("marcha_nupcial.mp3")


def test_overlay_citacoes_cola_marcha_no_beat(tmp_path, monkeypatch):
    from muntu import tons
    # asset real (mp3 curto) na tmp; ASSETS_DIR aponta pra la
    Sine(440).to_audio_segment(duration=500).export(str(tmp_path / "marcha_nupcial.mp3"),
                                                    format="mp3")
    monkeypatch.setattr(trilha, "ASSETS_DIR", str(tmp_path))
    monkeypatch.setattr(tons, "detecta_tom", lambda seg: None)   # sem tom -> nao transpoe
    bed = AudioSegment.silent(duration=2000)
    parte = {"start": 10.0, "end": 12.0, "tipo": "score"}
    # citacao DENTRO da parte -> colada (RMS sobe do silencio)
    out = _overlay_citacoes(bed, [{"t": 11.0, "melodia": "wedding march"}], parte)
    assert out.dBFS > bed.dBFS
    # citacao FORA da parte -> bed inalterado
    out2 = _overlay_citacoes(bed, [{"t": 99.0, "melodia": "wedding"}], parte)
    assert out2.dBFS == bed.dBFS
    # sem citacoes -> bed inalterado (mesmo objeto)
    assert _overlay_citacoes(bed, None, parte) is bed


def test_sobe_estilos_entram_no_apice():
    # direcao criativa extra do apice (PIN/reader): ex. citacao da marcha nupcial no casamento
    p = {"start": 6.8, "end": 16.0, "tipo": "score", "clima": "romantic",
         "confianca_valence": "alta", "sobe_t": 11.97,
         "sobe_estilos": ["quoting the bridal chorus in the same key", "", 42]}
    plan = _plano_da_parte(p, "balada", 14.14)
    apice = plan["sections"][1]["positive_local_styles"]
    assert "quoting the bridal chorus in the same key" in apice
    assert 42 not in apice and "" not in apice            # nao-string/vazio filtrados
    # Build NAO ganha os extras (sao do apice)
    assert "quoting the bridal chorus in the same key" not in plan["sections"][0]["positive_local_styles"]


def test_gate_estatico_no_pack_por_clima():
    from muntu.director import pack_por_clima
    # path de musica unica (sem reader): tense tem confianca estatica BAIXA -> minor gated -> default
    assert pack_por_clima("tense") == "default"
    assert pack_por_clima("melancholic") == "default"
    # confianca por-leitura alta (reader) destrava o pack minor
    assert pack_por_clima("tense", confianca="alta") == "tenso"
    # major nao gateia (romantic estatica alta; comedic idem)
    assert pack_por_clima("romantic") == "romantico"
    assert pack_por_clima("comedic") == "playful"


def test_pack_da_parte_gate_local_continua_ambiguo():
    # per-parte: reader deu tense com confianca baixa -> pack resolve mas gated=True (AMBIGUO),
    # NAO cai no default (gate estatico bypassado com confianca="alta" na resolucao)
    pack, gated = trilha._pack_da_parte({"tipo": "score", "clima": "tense",
                                         "confianca_valence": "baixa"})
    assert pack is not None and pack.get("nome") == "tenso" and gated is True


def test_plano_da_parte_usa_arco_do_pack():
    # parte romantic (pack curado, sem gate) -> arco do PACK dirige as secoes (convencao
    # inteira por clima, pesquisa climas-trilha): sax no pico, nao o arco generico
    p = {"start": 6.8, "end": 16.0, "tipo": "score", "clima": "romantic", "confianca_valence": "alta"}
    plan = _plano_da_parte(p, "balada", 14.14)
    apice = plan["sections"][1]["positive_local_styles"]
    assert any("saxophone" in e for e in apice)          # arco do romantico, nao ARCO_PARTE
    # sem pack (clima nao casa) -> arco generico (+ sustain: apice fecha a parte, sem decay)
    plan2 = _plano_da_parte({"start": 0.0, "end": 10.0, "tipo": "score", "clima": "zzz",
                             "mood": "x"}, "y", 5.0)
    apice2 = plan2["sections"][1]["positive_local_styles"]
    assert set(trilha.ARCO_PARTE["Apice"]).issubset(set(apice2))
    assert any("no fade-out" in e for e in apice2)


def test_provider_default_elevenlabs_pin_pode_forcar(monkeypatch):
    # default = provedor padrao (elevenlabs) em TUDO — A/B 2026-07-07: festa Stability
    # perdeu de ouvido; provider alternativo SO por opt-in explicito no PIN
    provs = []

    def _spy(prompt, dur, provider=None, **k):
        provs.append(provider)
        return Sine(440).to_audio_segment(duration=int(dur * 1000))
    monkeypatch.setattr(trilha.musica, "gera_musica", _spy)
    tl = {"partes": [
        {"cena_ini": 1, "cena_fim": 3, "start": 0.0, "end": 6.0, "tipo": "diegetic", "mood": "party"},
        {"cena_ini": 4, "cena_fim": 6, "start": 6.0, "end": 12.0, "tipo": "score", "mood": "ballad"}],
        "stop_t": None}
    monta_trilha(tl, 12.0)
    assert provs == [None, None]                # default em tudo
    provs.clear()
    tl["partes"][0]["provider"] = "stability"   # PIN forca explicito
    monta_trilha(tl, 12.0)
    assert provs[0] == "stability"


def test_diegetico_gera_mais_longo_e_corta_no_span(monkeypatch):
    # diegetico: gera parte+PAD e corta -> o fim natural (fade) da faixa gerada fica FORA do
    # span (era o "festa some cedo"); a parte na trilha dura exato o span dela
    pedidos = []

    def _bed_espiao(prompt, dur, **k):
        pedidos.append(dur)
        return Sine(440).to_audio_segment(duration=int(dur * 1000))
    monkeypatch.setattr(trilha.musica, "gera_musica", _bed_espiao)
    tl = {"partes": [
        {"cena_ini": 1, "cena_fim": 3, "start": 0.0, "end": 6.0, "tipo": "diegetic", "mood": "party"},
        {"cena_ini": 4, "cena_fim": 6, "start": 6.0, "end": 12.0, "tipo": "score", "mood": "ballad"}],
        "stop_t": None}
    out = monta_trilha(tl, 12.0)
    assert pedidos[0] == (6000 + trilha.DIEGETICO_PAD_MS) / 1000.0   # diegetico pediu com pad
    # score SEM plano tambem pede com folga (SILENCIO_TETO_MS): senao o corte de silencio
    # inicial pode deixar a parte curta e o FIM dela toca em silencio (buraco no rabo)
    assert pedidos[1] == (6000 + trilha.SILENCIO_TETO_MS) / 1000.0
    assert abs(len(out) - 12000) < 50                                # trilha dura o filme


def test_prompt_diegetico_pede_energia_constante():
    s = _prompt_da_parte({"tipo": "diegetic", "clima": "energetic", "mood": "party pop"})
    assert "constant energy" in s and "no breakdown" in s and "already playing" in s


def test_stop_na_fronteira_fecha_diegetico_com_gag(monkeypatch):
    # stop EXATAMENTE onde a parte diegetica acaba (reader marca a cena do reveal; o start
    # dela = fim da festa) -> wind-down fecha a festa + respiro antes do score (era o bug:
    # stop caia na parte score -> corte limpo, sem gag).
    monkeypatch.setattr(trilha.musica, "gera_musica", _fake_bed)
    tl = {"comico": True, "partes": [
        {"cena_ini": 1, "cena_fim": 3, "start": 0.0, "end": 5.0, "tipo": "diegetic", "clima": "energetic", "mood": "party"},
        {"cena_ini": 4, "cena_fim": 6, "start": 5.0, "end": 12.0, "tipo": "score", "clima": "romantic", "mood": "ballad"}],
        "stop_t": 5.0}
    out = monta_trilha(tl, 12.0)
    assert abs(len(out) - 12000) < 50
    assert out[5100:6100].max_dBFS == float("-inf") or out[5100:6100].max_dBFS < -40  # respiro pos-beat
    assert out[7000:11000].max_dBFS != float("-inf")  # score entra depois do respiro


def test_stop_fronteira_tolera_float_nao_identico(monkeypatch):
    # stop_t vem de fonte diferente do end da parte (round-trip JSON/float) -> igualdade EXATA
    # falha (5.0000001 != 5.0): o gag de fronteira nao disparava e caia no _aplica_stop generico
    # (corte limpo, sem wind-down). Tolerancia resolve. Silencio sozinho nao distingue os dois
    # caminhos (ambos calam a mesma janela) -> espiona _stop_diegetico pra confirmar o ROTEAMENTO.
    monkeypatch.setattr(trilha.musica, "gera_musica", _fake_bed)
    chamado = {"n": 0}
    orig = trilha._stop_diegetico

    def _espiao(*a, **k):
        chamado["n"] += 1
        return orig(*a, **k)
    monkeypatch.setattr(trilha, "_stop_diegetico", _espiao)
    tl = {"comico": True, "partes": [
        {"cena_ini": 1, "cena_fim": 3, "start": 0.0, "end": 5.0, "tipo": "diegetic", "clima": "energetic", "mood": "party"},
        {"cena_ini": 4, "cena_fim": 6, "start": 5.0, "end": 12.0, "tipo": "score", "clima": "romantic", "mood": "ballad"}],
        "stop_t": 5.0 + 1e-7}
    out = monta_trilha(tl, 12.0)
    assert chamado["n"] == 1                       # roteou como fronteira (gag), nao _aplica_stop generico
    assert abs(len(out) - 12000) < 50
    assert out[5100:6100].max_dBFS == float("-inf") or out[5100:6100].max_dBFS < -40  # respiro pos-beat (gag)
    assert out[7000:11000].max_dBFS != float("-inf")  # score entra depois do respiro


def test_wind_ate_o_corte_via_stop_fim_t(monkeypatch):
    # stop_fim_t (corte da cena) manda no tamanho do wind-down: pitch desce a cena inteira
    monkeypatch.setattr(trilha.musica, "gera_musica", _fake_bed)
    chamadas = {}
    orig = trilha._stop_diegetico
    def _espiao(tr, stop_ms, ate_ms, wind_ms=800):
        chamadas["wind"] = wind_ms
        return orig(tr, stop_ms, ate_ms, wind_ms=wind_ms)
    monkeypatch.setattr(trilha, "_stop_diegetico", _espiao)
    tl = {"comico": True, "stop_t": 4.0, "stop_fim_t": 5.9,
          "partes": [{"cena_ini": 1, "cena_fim": 4, "start": 0.0, "end": 10.0,
                      "tipo": "diegetic", "clima": "energetic", "mood": "x"}]}
    monta_trilha(tl, 10.0)
    assert chamadas["wind"] == 1900                       # 4.0 -> 5.9 = cena inteira


def test_bpm_da_parte_encaixa_nos_cortes():
    # cortes a cada 0.75s = grade de 80 BPM; range do pack [70,90] -> estima_bpm crava 80
    pack = {"bpm_range": [70, 90], "tol": 0.05}
    parte = {"start": 6.0, "end": 12.0, "tipo": "score"}
    cortes = [6.75, 7.5, 8.25, 9.0, 9.75]
    assert trilha._bpm_da_parte(parte, pack, cortes) == 80
    # < 2 cortes na parte -> meio do range
    assert trilha._bpm_da_parte(parte, pack, [6.75]) == 80  # (70+90)//2
    assert trilha._bpm_da_parte(parte, pack, None) == 80


def test_warp_liga_no_score_com_pack_e_nao_no_diegetico(monkeypatch):
    # warp pos-geracao trava o BPM real na grade dos cortes — so score com pack (diegetico
    # e som de ambiente; bed_file pinado nao se mexe)
    monkeypatch.setattr(trilha.musica, "gera_musica", _fake_bed)
    monkeypatch.setattr(trilha.musica, "_prov", lambda p=None: "elevenlabs")
    monkeypatch.setattr(trilha.musica, "cama_disponivel", lambda p=None: True, raising=False)
    warps = []

    def _spy(bed, bpm, **k):
        warps.append(bpm)
        return bed
    monkeypatch.setattr(trilha.warp, "warp_bed", _spy)
    tl = {"climax_t": 8.0, "partes": [
        {"cena_ini": 1, "cena_fim": 3, "start": 0.0, "end": 6.0, "tipo": "diegetic", "mood": "party"},
        {"cena_ini": 4, "cena_fim": 8, "start": 6.0, "end": 16.0, "tipo": "score",
         "clima": "romantic", "confianca_valence": "alta", "mood": "ballad"}], "stop_t": None}
    monta_trilha(tl, 16.0, cortes=[6.75, 7.5, 8.25, 9.0])
    assert len(warps) == 1                     # so a parte score
    assert 70 <= warps[0] <= 90                # BPM do range do pack romantico


def test_garante_rabo_vivo_reroll_propaga_provider(monkeypatch):
    # PIN camada 1: re-roll do rabo morto tem que respeitar o provider pinado da parte, senao
    # a parte volta pro provedor default no re-roll (bug: chamada do re-roll nao passava provider)
    morto = Sine(440).to_audio_segment(duration=8000) + AudioSegment.silent(duration=1500)
    chamadas = []

    def _spy(prompt, dur_s, provider=None, **k):
        chamadas.append(provider)
        return Sine(440).to_audio_segment(duration=int(dur_s * 1000))
    monkeypatch.setattr(trilha.musica, "gera_musica", _spy)
    plan = {"positive_global_styles": ["x"], "sections": []}
    trilha._garante_rabo_vivo(morto, "p", plan, 9.5, {"cena_ini": 5, "provider": "elevenlabs"})
    assert chamadas == ["elevenlabs"]


def test_plano_por_parte_usa_provider_pinado_nao_o_global(monkeypatch):
    # composition_plan tem que ser decidido pelo provider DA PARTE (PIN), nao pelo provedor
    # global (bug: musica._prov(None) checava so o default do ambiente — parte pinada em
    # elevenlabs perdia o arco se o default do ambiente fosse outro provedor, ex. stability).
    # Global forcado explicitamente pra "stability" (nao depende de DEFAULT_PROVIDER do modulo).
    monkeypatch.setenv("MUNTU_BED_PROVIDER", "stability")
    monkeypatch.setattr(trilha.musica, "gera_musica", _fake_bed)
    chamadas = []
    orig = trilha._plano_da_parte

    def _espiao(*a, **k):
        chamadas.append(True)
        return orig(*a, **k)
    monkeypatch.setattr(trilha, "_plano_da_parte", _espiao)
    tl = {"climax_t": 8.0, "partes": [
        {"cena_ini": 1, "cena_fim": 4, "start": 0.0, "end": 16.0, "tipo": "score",
         "clima": "romantic", "confianca_valence": "alta", "mood": "ballad",
         "provider": "elevenlabs"}], "stop_t": None}
    monta_trilha(tl, 16.0)
    assert chamadas   # _plano_da_parte foi chamado (hoje, com o bug, nao seria)


def test_stop_roteamento_sem_tipo_nao_derruba_p_stop(monkeypatch):
    # PIN editado a mao: parte sem campo "tipo" que CONTEM o stop_t -> roteamento do stop
    # acessava p_stop["tipo"] direto (KeyError). Resto do modulo ja usa .get.
    monkeypatch.setattr(trilha.musica, "gera_musica", _fake_bed)
    tl = {"partes": [{"cena_ini": 1, "cena_fim": 2, "start": 0.0, "end": 10.0, "mood": "x"}],
          "stop_t": 4.0}
    out = monta_trilha(tl, 10.0)                  # nao pode levantar KeyError
    assert abs(len(out) - 10000) < 50


def test_stop_roteamento_sem_tipo_nao_derruba_p_fecha(monkeypatch):
    # PIN sem "tipo": parte cujo FIM bate o stop_t (candidata a p_fecha) -> o generator
    # acessava p["tipo"] direto antes do .get existir (KeyError).
    monkeypatch.setattr(trilha.musica, "gera_musica", _fake_bed)
    tl = {"partes": [{"cena_ini": 1, "cena_fim": 2, "start": 0.0, "end": 4.0, "mood": "x"}],
          "stop_t": 4.0}
    out = monta_trilha(tl, 10.0)                  # nao pode levantar KeyError
    assert abs(len(out) - 10000) < 50


def test_overlay_citacoes_gain_invalido_usa_default(tmp_path, monkeypatch):
    # PIN com gain_db mal formado (unidade colada, "-3dB") derrubava a trilha inteira
    # (_overlay_citacoes roda FORA do try best-effort do loop de partes; pydub faz float(gain)
    # e levanta ValueError). Tipo invalido -> usa MARCHA_GAIN_DB, sem levantar.
    from muntu import tons
    Sine(440).to_audio_segment(duration=500).export(str(tmp_path / "marcha_nupcial.mp3"),
                                                    format="mp3")
    monkeypatch.setattr(trilha, "ASSETS_DIR", str(tmp_path))
    monkeypatch.setattr(tons, "detecta_tom", lambda seg: None)
    bed = AudioSegment.silent(duration=2000)
    parte = {"start": 10.0, "end": 12.0, "tipo": "score"}
    out = _overlay_citacoes(bed, [{"t": 11.0, "melodia": "wedding march", "gain_db": "-3dB"}], parte)
    assert out.dBFS > bed.dBFS                    # citacao colou (default aplicado, nao levantou)
    # bool passa isinstance(int) em Python: sem o guard explicito viraria gain de 1dB (True==1),
    # nao o default -3dB — silenciosamente errado, nao so um crash.
    out2 = _overlay_citacoes(AudioSegment.silent(duration=2000),
                             [{"t": 11.0, "melodia": "wedding march", "gain_db": True}], parte)
    esperado = _overlay_citacoes(AudioSegment.silent(duration=2000),
                                 [{"t": 11.0, "melodia": "wedding march"}], parte)
    assert abs(out2.dBFS - esperado.dBFS) < 0.01


def test_overlay_citacoes_fora_da_parte_nao_detecta_tom(monkeypatch):
    # detecta_tom (caro) so deve rodar se existir citacao aplicavel (dentro da parte + asset
    # existente). Citacao fora da parte -> tons.detecta_tom NAO chamado.
    from muntu import tons
    chamado = {"n": 0}

    def _spy(seg):
        chamado["n"] += 1
        return None
    monkeypatch.setattr(tons, "detecta_tom", _spy)
    bed = AudioSegment.silent(duration=2000)
    parte = {"start": 10.0, "end": 12.0, "tipo": "score"}
    out = _overlay_citacoes(bed, [{"t": 99.0, "melodia": "wedding"}], parte)
    assert chamado["n"] == 0
    assert out is bed


def test_e_retro_token_exato_nao_substring_fragil():
    # bug: match por SUBSTRING pega falso-positivo ("now" e substring de "renowned"). Fix:
    # comparacao por token exato. Casos legitimos (ja testados) continuam intactos.
    assert trilha._e_retro("now") is False           # token moderno legitimo -> nao-retro
    assert trilha._e_retro("unknown") is False        # era desconhecida -> nao forca (sentinel)
    assert trilha._e_retro("1980s") is True           # retro real, comportamento inalterado
    assert trilha._e_retro("renowned styling") is True   # falso-positivo do mecanismo antigo


def test_score_sem_plano_nao_deixa_buraco_de_silencio_no_fim(monkeypatch):
    # score SEM composition_plan gera exatamente dur_ms; _corta_silencio_inicial pode comer
    # ate SILENCIO_TETO_MS do INICIO do bed gerado -> bed fica < dur_ms -> rabo da parte em
    # silencio (buraco no FIM). Fix: gerar com folga extra (como o diegetico ja faz com
    # DIEGETICO_PAD_MS) e cortar em dur_ms DEPOIS do corte de silencio.
    def _bed_com_silencio_inicial(prompt, dur, **k):
        ms = int(dur * 1000)
        return AudioSegment.silent(duration=1500) + Sine(440).to_audio_segment(duration=ms - 1500)
    monkeypatch.setattr(trilha.musica, "gera_musica", _bed_com_silencio_inicial)
    tl = {"partes": [{"cena_ini": 1, "cena_fim": 1, "start": 0.0, "end": 6.0,
                      "tipo": "score", "mood": "x"}], "stop_t": None}
    out = monta_trilha(tl, 6.0)
    assert out[-500:].max_dBFS != float("-inf")   # fim da parte tem audio, nao rabo mudo


def test_bed_offset_pula_intro_da_musica_pronta(monkeypatch, tmp_path):
    # mp3 pronto: 3s de "intro" silenciosa + 7s de musica; bed_offset=3.0 entra na musica
    f = tmp_path / "musica_pronta.wav"
    (AudioSegment.silent(duration=3000) + Sine(440).to_audio_segment(duration=7000)).export(str(f), format="wav")
    monkeypatch.setattr(trilha.musica, "gera_musica",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("nao devia gerar")))
    tl = {"partes": [{"cena_ini": 1, "cena_fim": 4, "start": 0.0, "end": 6.0, "tipo": "score",
                      "mood": "x", "bed_file": str(f), "bed_offset": 3.0}], "stop_t": None}
    out = monta_trilha(tl, 6.0)
    assert out[0:1000].max_dBFS != float("-inf")   # sem offset seria a intro silenciosa
