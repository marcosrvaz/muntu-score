from muntu.director import (
    estima_bpm, classifica_modo, monta_grade, quantiza, plano_de_score, carrega_pack,
    composition_plan, pack_por_clima,
)


PACK_ARCO = {
    "bpm_range": [90, 120], "tol": 0.05, "conf_ritmico": 0.6,
    "generos": ["warm soft rock", "soul pop"], "negativos": ["harsh"],
    "arco": {"Intro": ["sparse"], "Build": ["rising"], "Climax": ["peak"], "Outro": ["fade"]},
}


def test_composition_plan_estrutura_e_soma_de_duracao():
    brief = {"duracao": 16.0, "cortes": [1.63, 2.67, 5.92, 6.8, 9.22, 10.18, 11.97, 14.14, 15.85], "cenas": []}
    cp = composition_plan(brief, PACK_ARCO)
    assert cp["respect_sections_durations"] is True
    assert cp["sections"][0]["section_name"] == "Intro"
    assert any(s["section_name"] == "Climax" for s in cp["sections"])
    # durações somam exatamente a duração do vídeo (ms)
    assert sum(s["duration_ms"] for s in cp["sections"]) == 16000
    # cada seção >= 3s (limite ElevenLabs)
    assert all(s["duration_ms"] >= 3000 for s in cp["sections"])


def test_composition_plan_injeta_bpm_e_instrumental():
    brief = {"duracao": 16.0, "cortes": [1.63, 2.67, 5.92, 6.8, 9.22, 10.18, 11.97, 14.14, 15.85], "cenas": []}
    cp = composition_plan(brief, PACK_ARCO)
    g = " ".join(cp["positive_global_styles"])
    assert "BPM" in g and "instrumental" in g
    assert "vocals" in cp["negative_global_styles"]


def test_composition_plan_conta_secoes():
    # < 4*SEC_MIN (12s) -> 3 secoes; com folga -> 4 (ganha Outro/resolucao). M6.
    curto = {"duracao": 10.0, "cortes": [3.5, 7.0], "cenas": []}
    longo = {"duracao": 30.0, "cortes": [6.0, 12.0, 18.0, 24.0], "cenas": []}
    assert len(composition_plan(curto, PACK_ARCO)["sections"]) == 3
    cp_l = composition_plan(longo, PACK_ARCO)
    assert len(cp_l["sections"]) == 4
    assert cp_l["sections"][-1]["section_name"] == "Outro"


def test_composition_plan_climax_no_pico_de_energia():
    # cena de alta energia no fim -> clímax na última seção interna
    brief = {"duracao": 18.0, "cortes": [6.0, 12.0],
             "cenas": [{"start": 0, "end": 6, "energia": "baixa"},
                       {"start": 6, "end": 12, "energia": "baixa"},
                       {"start": 12, "end": 18, "energia": "alta"}]}
    cp = composition_plan(brief, PACK_ARCO)
    nomes = [s["section_name"] for s in cp["sections"]]
    assert nomes[-1] == "Climax" or "Climax" in nomes


def test_carrega_pack_natal_sobrescreve_default():
    p = carrega_pack("natal", packs_dir="packs")
    assert p["bpm_range"] == [80, 100]
    assert "christmas" in p["bed_estilo"]


def test_carrega_pack_inexistente_cai_no_default():
    p = carrega_pack("nao_existe_zzz", packs_dir="packs")
    assert p["bpm_range"] == [100, 132]


def test_pack_por_clima_mapeia_mood_para_pack():
    assert pack_por_clima("romantic", "packs") == "romantico"
    assert pack_por_clima("tender", "packs") == "romantico"
    assert pack_por_clima("nostalgic", "packs") == "romantico"
    assert pack_por_clima("joyful", "packs") == "playful"
    assert pack_por_clima("energetic", "packs") == "playful"
    assert pack_por_clima("comedic", "packs") == "playful"
    # climas que antes caiam no default (bug do "mood idiota") agora tem pack proprio.
    # Packs MINOR sao gated por confianca de valence (pesos β): sem confianca por-leitura,
    # a tabela estatica (baixa p/ tense/melancholic) segura o minor -> default (neutro).
    assert pack_por_clima("melancholic", "packs") == "default"                       # gated
    assert pack_por_clima("melancholic", "packs", confianca="alta") == "melancolico"  # destrava
    assert pack_por_clima("tense", "packs") == "default"                             # gated
    assert pack_por_clima("tense", "packs", confianca="alta") == "tenso"             # destrava
    assert pack_por_clima("epic", "packs") == "epico"               # major: sem gate
    assert pack_por_clima("calm", "packs") == "calmo"
    assert pack_por_clima("neutral", "packs") == "default"          # neutral cravado no default


def test_pack_por_clima_sem_match_cai_no_default():
    assert pack_por_clima("zzz_inexistente", "packs") == "default"  # nenhum pack declara
    assert pack_por_clima(None, "packs") == "default"
    assert pack_por_clima("neutro", "packs") == "default"           # "neutro" (pt) != "neutral"


def test_pack_contextual_nunca_auto_selecionado():
    # natal/surf nao declaram `climas` -> so override manual, nunca auto
    assert pack_por_clima("joyful", "packs") not in ("natal", "surf")


def test_estima_bpm_recupera_pulso_conhecido():
    # cortes numa grade exata de 120 BPM (P=0.5s), fase 0
    cortes = [0.5, 1.0, 2.0, 3.5]
    g = estima_bpm(cortes, bpm_range=(100, 140), tol=0.05)
    assert g["bpm"] == 120
    assert g["confianca"] == 1.0          # todos caem na grade


def test_estima_bpm_lida_com_ruido():
    # mesma grade, cortes levemente fora (editor humano). Sem BPM "verdadeiro":
    # o algoritmo acha um pulso vizinho que encaixa todos os cortes dentro da tol.
    cortes = [0.52, 1.01, 1.98, 3.47]
    g = estima_bpm(cortes, bpm_range=(110, 130), tol=0.05)
    assert 117 <= g["bpm"] <= 123          # banda perto de 120
    assert g["confianca"] >= 0.75          # maioria na grade


def test_estima_bpm_vazio_nao_quebra():
    g = estima_bpm([], bpm_range=(100, 132))
    assert g["confianca"] == 0.0


def test_classifica_modo():
    assert classifica_modo(0.8) == "ritmico"
    assert classifica_modo(0.3) == "livre"


def test_quantiza_snap_na_grade():
    # corte em 1.02 a 120 BPM (P=0.5) -> snap pra 1.0
    assert abs(quantiza(1.02, fase=0.0, bpm=120) - 1.0) < 1e-9


def test_quantiza_com_lead():
    # antecipa 80ms
    t = quantiza(1.0, fase=0.0, bpm=120, lead_ms=80)
    assert abs(t - 0.92) < 1e-9


def test_monta_grade_marca_downbeats():
    g = monta_grade(fase=0.0, bpm=120, duracao=2.0)
    downbeats = [b for b in g["batidas"] if b["downbeat"]]
    assert g["batidas"][0]["downbeat"] is True
    assert len(downbeats) >= 1


def test_plano_de_score_quantiza_acentos_na_grade():
    brief = {"duracao": 4.0, "cortes": [0.51, 1.02, 2.03], "cenas": []}
    plano = plano_de_score(brief)
    assert 116 <= plano["bpm"] <= 124       # pulso perto de 120
    assert plano["acentos"], "deve ter acentos"
    P = 60.0 / plano["bpm"]
    for a in plano["acentos"]:
        # t_audio cai numa linha de grade (multiplo de P a partir da fase).
        # tol de ms: t_audio e fase sao arredondados p/ 3 casas (posicao pydub = ms int).
        k = (a["t_audio"] - plano["fase"]) / P
        assert abs(k - round(k)) < 0.01
    assert plano["bed_prompt"].endswith(f"{plano['bpm']} BPM")


def test_plano_respeita_cap_por_compasso():
    # muitos cortes num compasso; cap default = 2
    brief = {"duracao": 4.0, "cortes": [0.5, 0.75, 1.0, 1.25, 1.5], "cenas": []}
    plano = plano_de_score(brief)
    P = 60.0 / plano["bpm"]
    compasso = 4 * P
    from collections import Counter
    por_comp = Counter(int(a["t_audio"] // compasso) for a in plano["acentos"])
    assert all(v <= 2 for v in por_comp.values())


def test_bed_prompt_preenche_prompt_template():
    # pack com prompt_template (pesquisa moods->prompt): {bpm}/{mode} preenchidos +
    # invariantes de BED presentes.
    pack = carrega_pack("default")           # agora tem prompt_template + mode major
    brief = {"duracao": 4.0, "cortes": [0.5, 1.0, 2.0], "cenas": []}
    plano = plano_de_score(brief, pack)
    bp = plano["bed_prompt"]
    assert "{bpm}" not in bp and "{mode}" not in bp          # placeholders resolvidos
    assert str(plano["bpm"]) in bp                            # BPM numerico injetado
    assert "major key" in bp                                 # mode do pack
    assert "instrumental only" in bp and "sits under voiceover" in bp   # invariantes BED


def test_bed_prompt_fallback_sem_template():
    # pack sem prompt_template mantem o comportamento antigo (bed_estilo + BPM no fim).
    pack = {"bpm_range": [100, 132], "tol": 0.05, "conf_ritmico": 0.6,
            "bed_estilo": "warm bed, no drums"}
    plano = plano_de_score({"duracao": 4.0, "cortes": [0.5, 1.0], "cenas": []}, pack)
    assert plano["bed_prompt"].endswith(f"{plano['bpm']} BPM")
