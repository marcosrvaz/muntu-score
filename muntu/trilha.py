"""Apply — monta a TRILHA por parte a partir da timeline do reader.

Cada parte narrativa (reader.le_timeline) vira sua propria musica: mood -> prompt, gerada e
posicionada no span da parte. Diegetico (som do mundo) = band-limit (soa saindo das caixas);
score = limpo. STOP: a musica cala no beat do reveal pra piada respirar (o foley/room, que
e outra camada, continua). Ver memoria muntu-trilha-por-parte.

O CONTEUDO do mapa mood->musica e craft do usuario: se o mood da parte casa um pack curado
(pack_por_clima), usa o prompt_template dele; senao, usa a direcao livre que o reader deu.

Cada parte = 1 geracao (ElevenLabs), porque generos distintos (house diegetico vs pizzicato
comico) nao cabem numa geracao so. Best-effort por parte: falha -> aquela parte fica em
silencio, o resto da trilha segue.
"""
from __future__ import annotations

import os
import subprocess
import tempfile

from pydub import AudioSegment

from muntu import musica, tons, warp
from muntu.director import SEC_MIN, carrega_pack, estima_bpm, pack_por_clima

DIEGETICO_GAIN_DB = -10    # diegetico = som do AMBIENTE. Festa = musica ALTA no recinto
#                            (band-limit+reverb ja poem "no ambiente"; o nivel e presenca).

MIN_BED_MS = 3000          # ElevenLabs Music nao gera < ~3s -> gera >= 3s e corta no span
DIEGETICO_PAD_MS = 4000    # diegetico: gera MAIS LONGO que a parte e corta no meio da faixa —
#                            faixa gerada no tamanho exato RESOLVE/apaga no proprio fim (fade
#                            natural) e a "festa some cedo"; som do mundo e CORTADO, nao termina
STOP_MS = 1200             # silencio da musica no beat de STOP (a piada respira)
FADE_MS = 90               # transicao entre partes / bordas do stop

# GATE de valence (pesquisa mapa-vlm-mood-clima): mode/valence e o eixo frágil de LER de video
# (β=.39, espalhado, cultura-dependente). Pack MINOR (tenso/melancolico) sobre leitura fraca =
# pior erro (inverte o clima). Sem confianca alta, cai NESTE bed ambiguo — nem minor (misread)
# nem major commitado (que "adoca a tragedia", regra 2). arousal/BPM segue confiavel.
AMBIGUO = ("ambiguous neutral underscore, sustained pads, soft drones, unresolved suspended "
           "harmony, neither clearly major nor minor, supportive texture")


MODERNO = ("modern", "contemporary", "present", "current", "today", "now", "atual", "moderno")


def _e_retro(era: str) -> bool:
    """True se a era e periodo PASSADO (retro) -> trilha obrigatoriamente da epoca. 'modern
    day' etc -> False -> trilha livre (um filme moderno PODE ter trilha retro por escolha).
    Match por TOKEN exato (nao substring: "now" e substring acidental de "unknown"/"renowned"
    e nao pode contar como o token moderno "now"). "unknown" e sentinela explicito: era nao
    lida -> nao forca (nao da pra forcar uma epoca que a leitura nao identificou)."""
    era_l = (era or "").strip().lower()
    if not era_l or era_l == "unknown":
        return False
    tokens = set(era_l.split())
    return not (tokens & set(MODERNO))


def _pack_da_parte(parte: dict, packs_dir: str = "packs"):
    """(pack, gated) da parte SCORE cujo `clima` casa um pack curado. `gated` = o gate de
    valence segurou um pack minor (confianca != alta). Diegetico/sem match -> (None, False)."""
    if parte.get("tipo") == "diegetic":
        return None, False
    clima = (parte.get("clima") or "").strip().lower()
    if not clima:
        return None, False
    # confianca="alta" DESLIGA o gate estatico do pack_por_clima (tabela por mood, path de
    # musica unica): aqui temos confianca POR LEITURA do reader — o gate e local (abaixo) e
    # rende AMBIGUO (bed sem sinal), melhor que cair no default corporate.
    nome = pack_por_clima(clima, packs_dir, confianca="alta")
    if nome == "default":
        return None, False
    pack = carrega_pack(nome, packs_dir)
    conf = (parte.get("confianca_valence") or "media").strip().lower()
    return pack, pack.get("mode") == "minor" and conf != "alta"


def _bpm_da_parte(parte: dict, pack: dict, cortes: list[float] | None) -> int:
    """BPM 'roubado' dos cortes: dentro do range do pack (calibrado pelas refs), o BPM
    cuja GRADE encaixa nos cortes de cena da parte (estima_bpm, grid search puro Python) —
    os beats caem no corte. Menos de 2 cortes na parte -> meio do range."""
    rng = tuple(pack.get("bpm_range", [110, 110]))
    dentro = [c - parte["start"] for c in (cortes or []) if parte["start"] < c < parte["end"]]
    if len(dentro) >= 2:
        return int(estima_bpm(dentro, rng, pack.get("tol", 0.05))["bpm"])
    return sum(rng) // 2


def _prompt_da_parte(parte: dict, era: str = "", packs_dir: str = "packs",
                     comico: bool = False, cortes: list[float] | None = None) -> str:
    """Prompt de geracao da parte. SCORE com `clima` (vocab do reader) que casa um pack curado
    -> usa o prompt_template do mapa do usuario. DIEGETICO (source music, especifico do filme)
    ou sem match -> direcao livre (`mood`); ganha a `era` do filme (som do mundo = ano das
    imagens). + invariantes de BED + marca diegetico. `comico` (film-level, do reader) inflete
    o score curado pra kitsch — comedia romantica toca a balada DELIBERADAMENTE cafona.
    Kitsch NAO se aplica sobre o bed AMBIGUO do gate (over-sentimental commitaria a valence
    que o gate segurou — regra 2 dos pesos β)."""
    mood = (parte.get("mood") or "").strip()
    diegetic = parte.get("tipo") == "diegetic"
    pack, gated = _pack_da_parte(parte, packs_dir)
    base = None
    if pack is not None:                        # score: o mapa de climas curado dirige
        if gated:
            base = AMBIGUO                       # GATE: minor sem confianca alta -> ambiguo
        else:
            tpl = pack.get("prompt_template")
            if tpl:
                bpm = _bpm_da_parte(parte, pack, cortes)   # BPM do range que ENCAIXA nos cortes
                base = tpl.replace("{bpm}", str(bpm)).replace("{mode}", pack.get("mode", "major"))
            else:
                base = pack.get("bed_estilo")
    if not base:                                # diegetico ou clima sem pack -> direcao livre
        base = mood or "gentle neutral underscore"
    # filme genuinamente RETRO -> trilha OBRIGATORIAMENTE da epoca (diegetic E score). Filme
    # moderno -> NAO forca: trilha retro e escolha que DEPENDE DO MOOD, e ja vem do mood/clima
    # que o reader (LLM) leu — nao forcado aqui.
    if _e_retro(era) and era.lower() not in base.lower():
        base = f"{era} {base}"
    if comico and not diegetic and not gated:
        # filme e COMEDIA (reader, film-level): o score curado toca DELIBERADAMENTE cafona —
        # kitsch, melodrama tongue-in-cheek (a comedia romantica leva a serio demais de proposito).
        # NUNCA sobre o AMBIGUO do gate: "over-sentimental" commitaria a valence que o gate segurou.
        base = f"{base}, deliberately kitsch and cheesy, over-sentimental tongue-in-cheek melodrama"
    if diegetic:
        # festa ja esta tocando cheia quando a cena abre -> sem intro/build (senao "entra tarde");
        # energia CONSTANTE — sem breakdown/vale no meio (senao "a festa some cedo")
        base = (f"{base}, steady and already playing at full swing, constant energy throughout, "
                f"no intro build-up, no breakdown or quiet section "
                f"(source music heard from speakers in the room)")
    if "instrumental only" not in base:         # template de pack ja traz as invariantes
        # SEM "under voiceover": comercial sem locucao pede MUSICA COMPLETA (banda), nao
        # cama rala — "sits under voiceover" instruia o modelo a ser sparse (feedback 07-07)
        base = f"{base}, instrumental only"
    return base


def _reverb_sala(seg: AudioSegment) -> AudioSegment:
    """Ambiencia de sala leve via ffmpeg aecho (aproxima 'saindo das caixas num ambiente').
    Best-effort: falha (sem ffmpeg/filtro) -> seg original."""
    fd_src, src = tempfile.mkstemp(suffix=".wav")
    fd_dst, dst = tempfile.mkstemp(suffix=".wav")
    os.close(fd_src)
    os.close(fd_dst)
    try:
        seg.export(src, format="wav")
        subprocess.run(["ffmpeg", "-y", "-i", src, "-af", "aecho=0.8:0.9:40|75:0.3|0.2", dst],
                       check=True, capture_output=True)
        return AudioSegment.from_wav(dst)
    except Exception:                              # noqa: BLE001 — reverb e best-effort
        return seg
    finally:
        for p in (src, dst):
            if os.path.exists(p):
                os.remove(p)


def _diegetico(seg: AudioSegment) -> AudioSegment:
    """Faz a musica soar DENTRO do mundo (saindo das caixas num AMBIENTE): band-limit (alto-
    falante pequeno) + reverb de sala + nivel bem baixo (como ambience/sound design, NAO
    trilha de filme). Feedback do usuario 2026-07-07: diegetico nao e trilha, e som do ambiente."""
    seg = seg.high_pass_filter(300).low_pass_filter(3400)
    seg = _reverb_sala(seg)
    return seg + DIEGETICO_GAIN_DB


def _aplica_stop(trilha: AudioSegment, stop_ms, janela: int = STOP_MS) -> AudioSegment:
    """Cala a MUSICA numa janela (a partir de stop_ms) SEM mudar a duracao total: concat
    antes + silencio + depois, fades curtos p/ nao clicar. O foley/room (outra camada)
    continua, entao o beat toca diegetico e o silencio da trilha faz a piada."""
    if stop_ms is None or stop_ms < 0 or stop_ms >= len(trilha):
        return trilha
    fim = min(stop_ms + janela, len(trilha))
    antes = trilha[:stop_ms].fade_out(FADE_MS)
    depois = trilha[fim:].fade_in(FADE_MS)
    return antes + AudioSegment.silent(duration=fim - stop_ms) + depois


def _wind_down(seg: AudioSegment, passos: int = 10) -> AudioSegment:
    """Desligar a FONTE (vinil/toca-discos): pitch+speed despencam em degraus. O som 'morre'
    esticando -> fica mais longo que a entrada (quem chama re-corta). Best-effort."""
    if len(seg) < passos:
        return seg
    fatia = len(seg) // passos
    out = AudioSegment.empty()
    for i in range(passos):
        ped = seg[i * fatia:(i + 1) * fatia]
        taxa = max(3000, int(ped.frame_rate * (1.0 - i / passos * 0.9)))   # 1.0 -> ~0.19
        out += ped._spawn(ped.raw_data, overrides={"frame_rate": taxa}).set_frame_rate(seg.frame_rate)
    return out


def _stop_diegetico(trilha: AudioSegment, stop_ms: int, ate_ms: int, wind_ms: int = 800) -> AudioSegment:
    """Stop DIEGETICO = a FONTE e desligada por alguem: wind-down de pitch/speed a partir de
    stop_ms + silencio ATE `ate_ms` (fim da parte diegetica). O que vem depois (score) NAO e
    apagado. Soa 'alguem desligou o vinil', nao 'a trilha parou'. Preserva a duracao total."""
    if stop_ms < 0 or stop_ms >= len(trilha):
        return trilha
    ate_ms = min(max(ate_ms, stop_ms), len(trilha))
    winded = _wind_down(trilha[stop_ms:stop_ms + wind_ms]).fade_out(120)
    vao = ate_ms - stop_ms                          # so o resto da PARTE diegetica
    corpo = (winded + AudioSegment.silent(duration=vao))[:vao]
    return trilha[:stop_ms] + corpo + trilha[ate_ms:]   # score depois de ate_ms intacto


ARCO_PARTE = {
    "Build": ["developing", "adding layers", "rising energy", "building toward the peak"],
    "Apice": ["full arrangement", "emotional peak", "powerful soaring swell", "grand finale"],
}


def _plano_da_parte(parte: dict, prompt: str, climax_t, packs_dir: str = "packs",
                    cortes: list[float] | None = None) -> dict | None:
    """Composition_plan da PARTE score: Build -> APICE, com o apice ancorado no climax
    narrativo (reader) — a trilha SOBE apontando pro beat (ex.: o casal vai pra musica), nao
    fica chapada. So vale pra score (diegetico e som de ambiente, sem arco) com folga pra
    2 secoes (>= 2*SEC_MIN) e climax DENTRO da parte. None -> geracao simples (sem plano).
    O pack curado carrega a convencao INTEIRA por clima, arco incluso (pesquisa climas-trilha):
    parte com pack (e sem gate) usa o arco do pack (Build/Climax — ex. romantico = "soaring
    saxophone" no pico); sem pack/gated -> arco generico."""
    dur = parte["end"] - parte["start"]
    if parte.get("tipo") == "diegetic" or dur < 2 * SEC_MIN or climax_t is None:
        return None
    if not (parte["start"] < climax_t < parte["end"]):
        return None
    pack, gated = _pack_da_parte(parte, packs_dir)
    arco = (pack or {}).get("arco") if not gated else None
    estilos_build = list((arco or {}).get("Build") or ARCO_PARTE["Build"])
    estilos_apice = list((arco or {}).get("Climax") or ARCO_PARTE["Apice"])
    # negativos do pack em TODA secao (nao so global): sem eles o modelo desvia o apice pro
    # generico "epico" (tambores orquestrais no lugar do sax — feedback 2026-07-07)
    negativos = list((pack or {}).get("negativos") or []) if not gated else []
    # o Apice fecha a parte -> NAO deixa a faixa resolver/decair no fim ("clean ending" do
    # template): o beat de apice (ex. a musica) cai no decay e o pico aterrissa cedo demais
    estilos_apice.append("sustained full energy through the very end, no fade-out")
    # direcao criativa EXTRA do apice (PIN/reader manda, apply executa) — ex. citacao musical
    # ("quote da marcha nupcial na mesma tonalidade" num casamento), reprise de tema
    for e in parte.get("sobe_estilos") or []:
        if isinstance(e, str) and e.strip():
            estilos_apice.append(e.strip())
    # onde a trilha comeca a SUBIR: `sobe_t` da parte (direcao explicita — ex. "cresce no
    # casamento e intensifica na musica", PIN/reader) tem prioridade; senao ancora no climax.
    sobe_t = parte.get("sobe_t")
    ancora = sobe_t if isinstance(sobe_t, (int, float)) and parte["start"] < sobe_t < parte["end"] \
        else climax_t
    # apice comeca na ancora, mas cada secao respeita SEC_MIN (limite ElevenLabs): se a
    # ancora cai perto da borda, o apice desliza o minimo pra caber — o swell chega no beat.
    apice_ini = min(max(ancora, parte["start"] + SEC_MIN), parte["end"] - SEC_MIN)
    # FRONTEIRAS DE SECAO = CORTES DE CENA dentro da parte (+ a ancora do apice): o FILME
    # dita a estrutura musical, nao o modelo — a musica troca de movimento NOS cortes
    # (respect_sections_durations). Fronteira mais perto que SEC_MIN da anterior/do fim e
    # fundida (limite ElevenLabs). Deterministico: cortes vem do analyzer, exatos.
    apice_ini = round(apice_ini, 3)
    fr = [parte["start"]]
    for b in sorted({round(c, 3) for c in (cortes or [])
                     if parte["start"] < c < parte["end"]}):
        if b - fr[-1] >= SEC_MIN and parte["end"] - b >= SEC_MIN:
            fr.append(b)
    fr.append(parte["end"])
    # a ANCORA do apice tem prioridade sobre corte vizinho: remove fronteiras internas a
    # menos de SEC_MIN dela e a insere (o swell TEM que trocar exatamente no beat)
    fr = [b for b in fr if b in (parte["start"], parte["end"]) or abs(b - apice_ini) >= SEC_MIN]
    if apice_ini not in fr:
        fr = sorted(fr + [apice_ini])
    # o template de pack pede "clean ending" (certo p/ musica unica de filme inteiro) — mas o
    # APICE desta parte fecha no fim: "clean ending" global faz o modelo APAGAR a faixa nos
    # ultimos ~2s e o beat (ex. a musica) cai no silencio; contradiz o "no fade-out" local e
    # as vezes ganha. Remove a contradicao na raiz do prompt global.
    prompt = prompt.replace("clean ending", "ending at full intensity")
    total = int(round(dur * 1000))
    sections, n_build = [], 0
    for i in range(len(fr) - 1):
        ini, fim = fr[i], fr[i + 1]
        apice = ini >= apice_ini - 1e-6
        if apice:
            nome = "Apice" if not any(s["section_name"].startswith("Apice") for s in sections) \
                else f"Apice {sum(1 for s in sections if s['section_name'].startswith('Apice')) + 1}"
        else:
            n_build += 1
            nome = "Build" if n_build == 1 else f"Build {n_build}"
        estilos = list(estilos_apice if apice else estilos_build)
        sections.append({"section_name": nome, "positive_local_styles": estilos,
                         "negative_local_styles": list(negativos),
                         "duration_ms": int(round((fim - ini) * 1000)), "lines": []})
    # rounding: soma das secoes (sem cauda) bate a duracao da parte
    sections[-1]["duration_ms"] += total - sum(s["duration_ms"] for s in sections)
    # CAUDA descartavel (mesmo truque do pad diegetico): o modelo INSISTE em resolver/
    # apagar o fim da peca (2 re-rolls morreram) -> damos 4s extras no clima do apice pra
    # ele morrer NELES; o corte em dur_ms cai em plena energia. Deterministico, nao aposta.
    sections.append({"section_name": "Cauda", "positive_local_styles": list(estilos_apice),
                     "negative_local_styles": list(negativos),
                     "duration_ms": CAUDA_MS, "lines": []})
    return {
        "positive_global_styles": [prompt],
        "negative_global_styles": ["vocals"] + list(negativos),
        "sections": sections,
        "respect_sections_durations": True,
    }


RABO_MS = 1500             # janela de checagem do fim da faixa
RABO_DELTA_DB = 12         # rabo este tanto abaixo do corpo = "morto" (modelo apagou o fim)
CAUDA_MS = 4000            # secao extra descartavel no fim do plano (o modelo resolve NELA)


def _rabo_morto(bed: AudioSegment) -> bool:
    """True se o FIM da faixa morreu (fade/resolucao do modelo): rabo bem abaixo do corpo.
    O gerador as vezes apaga os ultimos ~2s apesar do estilo 'no fade-out' — e o beat de
    apice (ex. a musica) cai no silencio. Deteccao objetiva, nao aposta de prompt."""
    if len(bed) <= 2 * RABO_MS:
        return False
    corpo, rabo = bed[:-RABO_MS], bed[-RABO_MS:]
    if rabo.dBFS == float("-inf"):
        return True
    return corpo.dBFS - rabo.dBFS > RABO_DELTA_DB


def _garante_rabo_vivo(bed: AudioSegment, prompt: str, plan: dict, dur_s: float,
                       parte: dict, corte_ms: int | None = None) -> AudioSegment:
    """Rabo morto NO PONTO DE CORTE (corte_ms; a cauda alem dele morre por design) ->
    re-gera 1x (nudge no plano = cache novo) e fica com a rolagem de rabo mais vivo.
    Geracao e dado, nao controle: checa o resultado em vez de confiar no estilo."""
    corte = corte_ms or len(bed)
    if not _rabo_morto(bed[:corte]):
        return bed
    import sys
    print(f"[muntu] parte S{parte.get('cena_ini')}: fim da faixa morto; re-rolando 1x",
          file=sys.stderr)
    plan2 = dict(plan)
    plan2["positive_global_styles"] = list(plan.get("positive_global_styles", [])) + \
        ["the final seconds stay at full arrangement and full volume"]
    try:
        bed2 = musica.gera_musica(prompt, dur_s, provider=parte.get("provider"),
                                  composition_plan=plan2)
    except Exception:                            # noqa: BLE001 — re-roll e best-effort
        return bed
    return bed2 if bed2[:corte][-RABO_MS:].dBFS > bed[:corte][-RABO_MS:].dBFS else bed


COMICO = {"comedic", "playful", "joyful"}


def _e_comico(parte: dict) -> bool:
    """True se a parte lê como comedia (clima do vocab OU pista no mood free-text). So aí o
    gag de vinil desligando faz sentido — filme serio nao ganha scratch."""
    clima = (parte.get("clima") or "").lower()
    mood = (parte.get("mood") or "").lower()
    return clima in COMICO or any(w in mood for w in ("comedic", "comic", "funny", "playful", "quirky"))


# --- CITACOES: overlay GARANTIDO (marcha/sax) substitui a aposta de prompt ---
# A citacao deixa de ser texto no composition_plan ("incorporating X motif" — o modelo ora
# ignora, ora migra o payoff pra Cauda descartada; reconcilia-chunks 2026-07-07) e vira AUDIO
# nosso: asset de dominio publico alinhado ao TOM da cama da parte, colado no beat (citacao.t).
# Mapa melodia->arquivo; asset ausente -> no-op (citacao e acento, nao nucleo). Ver tons.py.
ASSETS_DIR = "assets/citacoes"
CITACAO_ASSETS = {           # keyword (substring do melodia) -> arquivo PD em ASSETS_DIR
    "wedding": "marcha_nupcial.mp3",
    "nupcial": "marcha_nupcial.mp3",
    "bride": "marcha_nupcial.mp3",
    # futuras citacoes PD: "jingle bells", "funeral" (Chopin Marche funebre)
}
MARCHA_GAIN_DB = -3          # quote melodico no nivel do bed; PIN ajusta por citacao (gain_db)


def _asset_citacao(melodia: str | None, assets_dir: str = ASSETS_DIR) -> str | None:
    """Caminho do asset PD p/ a citacao (match por keyword no melodia), se o arquivo existir."""
    m = (melodia or "").lower()
    for kw, arq in CITACAO_ASSETS.items():
        if kw in m:
            p = os.path.join(assets_dir, arq)
            return p if os.path.exists(p) else None
    return None


def _overlay_citacoes(bed: AudioSegment, citacoes: list[dict] | None,
                      parte: dict) -> AudioSegment:
    """Cola cada citacao (com asset PD) no beat, ALINHADA AO TOM da cama desta parte. Best-effort:
    sem asset, asset corrompido, ou tom incerto -> bed inalterado. Citacao fora da parte: ignora."""
    if not citacoes:
        return bed
    # filtra ANTES de detectar o tom (caro, roda librosa): so vale a pena se sobrar citacao
    # dentro da parte E com asset existente — senao detecta_tom rodaria a toa em toda parte.
    aplicaveis = []
    for c in citacoes:
        t = c.get("t")
        if not (isinstance(t, (int, float)) and parte["start"] <= t < parte["end"]):
            continue
        asset = _asset_citacao(c.get("melodia"), ASSETS_DIR)
        if not asset:
            continue
        aplicaveis.append((t, asset, c))
    if not aplicaveis:
        return bed
    tom = tons.detecta_tom(bed)                       # tom da cama desta parte (1x)
    for t, asset, c in aplicaveis:
        try:
            seg = AudioSegment.from_file(asset)
        except Exception:                             # noqa: BLE001 — asset corrompido -> skip
            continue
        seg = tons.alinha_tom(seg, tom)
        gain = c.get("gain_db", MARCHA_GAIN_DB)
        # PIN pode vir com tipo invalido (string mal formada, bool etc) — nao pode derrubar a
        # trilha inteira (roda FORA do try best-effort do loop de partes)
        if not isinstance(gain, (int, float)) or isinstance(gain, bool):
            gain = MARCHA_GAIN_DB
        bed = bed.overlay(seg + gain, position=int((t - parte["start"]) * 1000))
    return bed


SILENCIO_LIMIAR_DB = -50.0    # abaixo disso = silencio/quase-silencio (dead-air, count-in)
SILENCIO_TETO_MS = 2000       # cap: nao come um fade-in musical longo (so o dead-air do inicio)


def _corta_silencio_inicial(bed: AudioSegment) -> AudioSegment:
    """REGRA universal: corta o silencio/quase-silencio do INICIO de QUALQUER bed (gerado,
    biblioteca ou pinned) pra musica entrar no beat, nao depois. Gen-IA e faixa de catalogo as
    vezes comecam com dead-air/count-in (ex.: balada pinned = 750ms de -inf; A entrava tarde).
    Cap em SILENCIO_TETO_MS (preserva fade-in musical intencional). Best-effort: erro -> intacto."""
    try:
        from pydub.silence import detect_leading_silence

        n = min(detect_leading_silence(bed, silence_threshold=SILENCIO_LIMIAR_DB), SILENCIO_TETO_MS)
        return bed[n:] if n > 0 else bed
    except Exception:                              # noqa: BLE001 — best-effort
        return bed


def monta_trilha(timeline: dict, duracao: float, packs_dir: str = "packs",
                 cortes: list[float] | None = None) -> AudioSegment:
    """Timeline do reader -> trilha completa (musica por parte + STOP). Silencio se sem partes.
    musica.gera_musica e best-effort por parte: falha -> aquela parte fica em silencio."""
    partes = timeline.get("partes", [])
    era = timeline.get("era", "")                # ano do filme (LLM) -> diegetico coincide
    fc = timeline.get("comico")                  # comedia e do FILME (reader, film-level):
    filme_comico = fc if isinstance(fc, bool) else any(_e_comico(p) for p in partes)
    climax_t = timeline.get("climax_t")
    trilha = AudioSegment.silent(duration=int(duracao * 1000))
    for parte in partes:
        ini_ms = int(parte["start"] * 1000)
        dur_ms = int((parte["end"] - parte["start"]) * 1000)
        if dur_ms <= 0:
            continue
        prompt = _prompt_da_parte(parte, era, packs_dir, comico=filme_comico, cortes=cortes)
        # composition_plan so existe no ElevenLabs — decisao e POR PARTE (PIN de provider),
        # nao pelo provedor global (senao uma parte pinada em elevenlabs perde o arco quando
        # o default do ambiente e outro provedor, e vice-versa: degrada em silencio).
        prov_parte = musica._prov(parte.get("provider"))
        if prov_parte == "elevenlabs":
            plan = _plano_da_parte(parte, prompt, climax_t, packs_dir, cortes=cortes)
        else:
            plan = None
            import sys
            print(f"[muntu] parte S{parte.get('cena_ini')}: provedor '{prov_parte}' sem "
                  "composition_plan (arco desligado)", file=sys.stderr)
        gera_ms = max(MIN_BED_MS, dur_ms)
        if parte.get("tipo") == "diegetic":     # corta no MEIO da faixa (energia cheia)
            gera_ms += DIEGETICO_PAD_MS
        elif plan is None:                      # score sem plano: gera dur_ms EXATO -> o corte
            gera_ms += SILENCIO_TETO_MS         # de silencio inicial (ate SILENCIO_TETO_MS)
            #                                     deixava a parte curta (buraco no FIM); mesmo
            #                                     truque do pad diegetico, cortado DEPOIS abaixo
        try:
            bed_file = parte.get("bed_file")    # PIN de camada 2: audio TRAVADO — aceita
            #                                     QUALQUER audio (mp3 pronto/biblioteca incluso)
            if bed_file and os.path.exists(bed_file):
                bed = AudioSegment.from_file(bed_file)
                # bed_offset (s): de ONDE da musica pronta entrar (pula intro, pega refrão).
                # Editar musica existente = mesmo encanamento (corte+warp+diegetico+stop).
                off = parte.get("bed_offset")
                if isinstance(off, (int, float)) and off > 0:
                    bed = bed[int(off * 1000):]
            else:
                # Provider POR PARTE via PIN (parte["provider"]). Default = ElevenLabs em
                # TUDO — A/B 2026-07-07: festa Stability perdeu de ouvido; o split diegetico
                # ->stability foi revertido (mecanismo fica, opt-in explicito no PIN).
                bed = musica.gera_musica(prompt, gera_ms / 1000.0, composition_plan=plan,
                                          provider=parte.get("provider"))
                if plan is not None:            # apice fecha a parte: rabo morto = beat no silencio
                    bed = _garante_rabo_vivo(bed, prompt, plan, gera_ms / 1000.0, parte,
                                             corte_ms=dur_ms)
                # WARP pos-geracao (score com pack): a geracao so APROXIMA o BPM pedido;
                # librosa mede o tempo REAL -> rubberband trava na grade dos cortes (cap 6%,
                # best-effort). Fecha o circuito deterministico do BPM: beat cai NO corte.
                pack, gated = _pack_da_parte(parte, packs_dir)
                if plan is not None and pack is not None and not gated:
                    bed = warp.warp_bed(bed, _bpm_da_parte(parte, pack, cortes))
        except Exception as e:                  # noqa: BLE001 — musica por parte e best-effort
            import sys
            print(f"[muntu] parte S{parte.get('cena_ini')} sem musica ({e})", file=sys.stderr)
            continue
        bed = _corta_silencio_inicial(bed)      # REGRA: entra no beat, sem dead-air (todo bed)
        bed = bed[:dur_ms]
        if parte.get("tipo") == "diegetic":     # som do mundo: reverb + baixo (reverb alonga -> re-corta)
            bed = _diegetico(bed)[:dur_ms]
        bed = bed.fade_in(FADE_MS).fade_out(FADE_MS)
        bed = _overlay_citacoes(bed, timeline.get("citacoes"), parte)
        trilha = trilha.overlay(bed, position=ini_ms)
    # STOP roteado por tipo/mood:
    #  - score (nao-diegetico) -> corte musical limpo (a trilha para pro beat).
    #  - diegetico + COMICO -> gag: a fonte desliga (wind-down de vinil/pitch) — "alguem cortou".
    #  - stop NA FRONTEIRA fechando uma parte diegetica -> gag idem (o reader marca o stop na
    #    cena do reveal; _t_de_cena da o START dela — que e exatamente onde a festa acaba).
    #  - diegetico nao-comico -> sem stop (som do ambiente segue; nao narra, nao vira gag serio).
    # Comedia e do FILME, nao da parte (filme_comico ja calculado no topo): comedia costuma
    # ser tocada RETA (registro serio contra o absurdo) — reader film-level; fallback partes.
    stop_t = timeline.get("stop_t")
    if stop_t is not None:
        ms = int(stop_t * 1000)
        p_stop = next((p for p in partes if p["start"] <= stop_t < p["end"]), None)
        # fronteira com tolerancia: stop_t e end podem vir de fontes distintas (_t_de_cena vs
        # timeline) e divergir por float (4.999999 vs 5.0) — igualdade exata perderia o gag.
        p_fecha = next((p for p in partes
                        if abs(p.get("end", -1) - stop_t) < 1e-3 and p.get("tipo") == "diegetic"), None)
        if p_stop and p_stop.get("tipo") == "diegetic":
            if filme_comico:
                # o wind-down (vitrola desligando) ocupa do beat ATE O CORTE da cena
                # (stop_fim_t do reader) — pitch desce a cena inteira, nao 0.8s fixo
                fim_cena = timeline.get("stop_fim_t")
                wind = int((fim_cena - stop_t) * 1000) if isinstance(fim_cena, (int, float)) \
                    and stop_t < fim_cena <= p_stop["end"] else 800
                trilha = _stop_diegetico(trilha, ms, int(p_stop["end"] * 1000), wind_ms=wind)
        elif p_fecha and filme_comico:
            # fronteira: a festa acaba EXATAMENTE no beat -> wind-down fecha a parte diegetica
            # (desliga a fonte) + a piada respira antes do score entrar.
            wind_ms = min(800, ms)
            trilha = _stop_diegetico(trilha, ms - wind_ms, ms, wind_ms=wind_ms)
            trilha = _aplica_stop(trilha, ms)
        elif p_stop:
            trilha = _aplica_stop(trilha, ms)
    return trilha
