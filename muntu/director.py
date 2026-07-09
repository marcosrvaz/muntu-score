"""Music Director — o coracao anti-tosco.

Deriva um pulso musical dos cortes do video, monta uma grade em BPM e
quantiza os acentos (stems) pra caírem NA batida em vez do corte cru.
Ver docs/director-design.md — 30 anos de ouvido viram regra aqui.

Puro Python (so numpy). Nenhuma API. A musica (bed) e gerada fora, em musica.
"""
from __future__ import annotations

import json
import os
import sys

# --- Pack: perilhas que o ouvido calibra (default embutido; packs/*.json sobrescreve) ---
PACK_DEFAULT = {
    "nome": "default",
    "bpm_range": [100, 132],
    "tol": 0.05,          # janela "ta na batida" (s). 50ms ~= 1.2 frame @24fps.
    "lead_ms": 0,         # antecipacao do acento (ms). >0 = resolve ON the cut.
    "cap_por_compasso": 2,
    "conf_ritmico": 0.6,  # confianca >= isto -> modo ritmico
    "bed_estilo": "warm corporate bed, soft pads, no drums",
}


def carrega_pack(nome: str = "default", packs_dir: str = "packs") -> dict:
    """Pack de direcao = PACK_DEFAULT + overrides de packs/{nome}.json. Faltou = default."""
    nome = os.path.basename(str(nome))               # nome vem de fora (API Gradio) — sem traversal
    caminho = os.path.join(packs_dir, f"{nome}.json")
    if not os.path.exists(caminho):
        return dict(PACK_DEFAULT)
    try:
        with open(caminho, encoding="utf-8") as f:
            return {**PACK_DEFAULT, **json.load(f)}
    except (OSError, json.JSONDecodeError):
        print(f"[muntu] pack '{nome}' ilegivel; usando default", file=sys.stderr)
        return dict(PACK_DEFAULT)


def pack_por_clima(clima: str | None, packs_dir: str = "packs",
                   confianca: str | None = None) -> str:
    """Auto-selecao: nome do pack cujo `climas` cobre o clima dominante do VLM.

    Sem match (ou clima None) -> 'default'. Packs contextuais (natal/surf) nao
    declaram `climas` -> nunca sao auto-selecionados; ficam override manual.

    GATE de valence (pesos β, mapa-vlm-mood-clima): pack MINOR sobre leitura fraca de
    valence = pior erro (inverte o clima) -> so dispara com confianca "alta". `confianca`
    = por-leitura (reader, path por-parte); None -> tabela estatica por mood
    (mood.CONFIANCA_VALENCE, path de musica unica). Gated -> 'default' (neutro), nao o minor.
    """
    if not clima or not os.path.isdir(packs_dir):
        return "default"
    for arq in sorted(os.listdir(packs_dir)):
        if not arq.endswith(".json"):
            continue
        try:
            with open(os.path.join(packs_dir, arq), encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if clima in cfg.get("climas", []):
            if cfg.get("mode") == "minor":
                from muntu.mood import CONFIANCA_VALENCE
                conf = confianca or CONFIANCA_VALENCE.get(clima, "baixa")
                if conf != "alta":
                    return "default"           # leitura fraca: neutro, nunca minor commitado
            return cfg.get("nome") or arq[:-5]
    return "default"


def estima_bpm(cortes: list[float], bpm_range=(100, 132), tol: float = 0.05) -> dict:
    """Acha a grade {phi + k*P} que melhor encaixa nos cortes (brute force barato).

    Retorna bpm, fase (offset em s), confianca (fracao de cortes na grade).
    """
    lo, hi = sorted((int(bpm_range[0]), int(bpm_range[1])))
    lo = max(1, lo)                                   # bpm 0 -> ZeroDivisionError no P
    hi = max(lo, hi)
    if not cortes:
        return {"bpm": lo, "fase": 0.0, "confianca": 0.0}

    melhor = None  # (score, bpm, phi, confianca)
    for bpm in range(lo, hi + 1):
        P = 60.0 / bpm
        for fase_step in range(50):                 # varre fase dentro de 1 batida
            phi = fase_step / 50.0 * P
            res = [abs(t - (phi + round((t - phi) / P) * P)) for t in cortes]
            dentro = sum(1 for r in res if r <= tol)
            erro = sum(res)
            score = (dentro, -erro)                  # max cortes na grade, min erro total
            if melhor is None or score > melhor[0]:
                melhor = (score, bpm, phi, dentro / len(cortes))
    _, bpm, phi, confianca = melhor
    return {"bpm": bpm, "fase": phi, "confianca": confianca}


def classifica_modo(confianca: float, limiar: float = 0.6) -> str:
    """ritmico = pulso claro (acentos percussivos); livre = espalhado (so swells/risers)."""
    return "ritmico" if confianca >= limiar else "livre"


def monta_grade(fase: float, bpm: float, duracao: float) -> dict:
    """Linhas de batida cobrindo a duracao. Downbeats a cada 4 batidas carregam peso."""
    P = 60.0 / bpm
    batidas, k = [], 0
    while fase + k * P <= duracao:
        t = fase + k * P
        batidas.append({"t": t, "downbeat": (k % 4 == 0)})
        k += 1
    return {"P": P, "batidas": batidas}


def quantiza(corte: float, fase: float, bpm: float, lead_ms: float = 0.0) -> float:
    """Snap do corte na linha de grade mais proxima (- antecipacao opcional)."""
    P = 60.0 / bpm
    t_audio = fase + round((corte - fase) / P) * P
    return max(0.0, t_audio - lead_ms / 1000.0)


def _proximo_downbeat(t: float, grade: dict) -> bool:
    for b in grade["batidas"]:
        if abs(b["t"] - t) <= 1e-6:
            return b["downbeat"]
    return False


def seleciona_acentos(cortes, grade, fase, bpm, tol, cap_por_compasso,
                      modo, cenas=None):
    """Acento SELETIVO (todo corte = cansa = tosco). Prioriza troca de clima/energia.

    Sem analise de clima (cenas=None) -> heuristica: cortes mais perto da grade primeiro,
    respeitando o cap de densidade por compasso.
    """
    P = 60.0 / bpm
    compasso = 4 * P

    candidatos = []
    for c in cortes:
        t_audio = quantiza(c, fase, bpm)
        dist = abs(c - t_audio)
        forte = _clima_forte(c, cenas) if cenas else (dist <= tol)
        candidatos.append({"corte": c, "t_audio": t_audio, "dist": dist, "forte": forte})

    # forte primeiro, depois mais perto da grade
    candidatos.sort(key=lambda x: (not x["forte"], x["dist"]))

    usados, acentos = {}, []
    for cand in candidatos:
        comp = int(cand["t_audio"] // compasso)
        if usados.get(comp, 0) >= cap_por_compasso:
            continue
        usados[comp] = usados.get(comp, 0) + 1
        downbeat = _proximo_downbeat(cand["t_audio"], grade)
        if modo == "livre":
            tipo = "riser"                       # fora de grade tolera transicao, nao perc
        else:
            tipo = "impact" if (cand["forte"] or downbeat) else "perc"
        acentos.append({
            "t_video": cand["corte"],
            "t_audio": round(cand["t_audio"], 3),
            "tipo": tipo,
            "ganho_db": 0 if tipo == "impact" else -6,
        })
    acentos.sort(key=lambda a: a["t_audio"])
    return acentos


def _clima_dominante(cenas) -> str | None:
    """Clima que mais pesa (por duracao de cena) — molda o mood da musica contínua."""
    if not cenas:
        return None
    peso: dict[str, float] = {}
    for c in cenas:
        cl = c.get("clima")
        if cl:
            peso[cl] = peso.get(cl, 0.0) + (c.get("end", 0) - c.get("start", 0))
    return max(peso, key=peso.get) if peso else None


def _clima_forte(corte, cenas) -> bool:
    """True se o corte marca troca de cena/energia (vem da analise de clima, Task 10)."""
    for i, cena in enumerate(cenas):
        if abs(cena.get("start", -1) - corte) <= 0.15:
            if i == 0:
                return True
            return cenas[i - 1].get("energia") != cena.get("energia")
    return False


def plano_de_score(brief: dict, pack: dict | None = None) -> dict:
    """Saida do Director: bpm, fase, modo, bed_prompt, lista de acentos quantizados.

    brief = saida do analyzer (duracao, cortes, cenas). pack = regras de direcao.
    """
    pack = {**PACK_DEFAULT, **(pack or {})}
    cortes = brief.get("cortes", [])
    duracao = brief.get("duracao", 0.0)
    cenas = brief.get("cenas") or None

    g = estima_bpm(cortes, tuple(pack["bpm_range"]), pack["tol"])
    bpm, fase, conf = g["bpm"], g["fase"], g["confianca"]
    modo = classifica_modo(conf, pack["conf_ritmico"])
    grade = monta_grade(fase, bpm, duracao)

    acentos = seleciona_acentos(
        cortes, grade, fase, bpm, pack["tol"], pack["cap_por_compasso"], modo, cenas)

    # lead_ms do pack aplicado no t_audio final
    if pack["lead_ms"]:
        for a in acentos:
            a["t_audio"] = round(max(0.0, a["t_audio"] - pack["lead_ms"] / 1000.0), 3)

    # mood da musica: pack com prompt_template (pesquisa moods->prompt) preenche {bpm}/{mode}
    # — estrutura hierarquica + invariantes de BED (instrumental only / sits under voiceover
    # / clean ending). Sem template: fallback = clima do VLM + bed_estilo do pack.
    clima_dom = _clima_dominante(cenas)
    tpl = pack.get("prompt_template")
    if tpl:
        bed_prompt = tpl.replace("{bpm}", str(bpm)).replace("{mode}", pack.get("mode", "major"))
        if clima_dom:                          # mood do VLM (comedic/tender/...) lidera o prompt
            bed_prompt = f"{clima_dom}, {bed_prompt}"
    else:
        estilo = f"{clima_dom}, {pack['bed_estilo']}" if clima_dom else pack["bed_estilo"]
        bed_prompt = f"{estilo}, {bpm} BPM"
    return {
        "bpm": bpm,
        "fase": round(fase, 3),
        "confianca": round(conf, 3),
        "modo": modo,
        "bed_prompt": bed_prompt,
        "acentos": acentos,
    }


# ================= Composition Plan (musica com arco — ElevenLabs Music V2) =================
# Ver docs/composition-plan-design.md. Monta seções (intro→build→clímax→outro) alinhadas
# aos cortes do filme, mood por seção. Puro Python.

ARCO_DEFAULT = {
    "Intro":  ["sparse", "gentle", "establishing"],
    "Build":  ["developing", "adding layers", "rising energy"],
    "Climax": ["full arrangement", "emotional peak", "powerful"],
    "Outro":  ["resolving", "winding down", "gentle ending"],
}
SEC_MIN = 3.0          # duração mínima de seção (limite ElevenLabs, s)
_ENERGIA_SCORE = {"baixa": 1, "media": 3, "alta": 5}      # legado (strings)


def _energia_num(cena) -> float:
    """Energia numérica da cena. VLM já dá int 1-5; strings legadas são mapeadas."""
    e = cena.get("energia", 3)
    return float(e) if isinstance(e, (int, float)) else _ENERGIA_SCORE.get(e, 3)


def _energia_em(cenas, t):
    for c in cenas:
        if c.get("start", 0) <= t < c.get("end", 0):
            return _energia_num(c)
    return 3


def _fronteiras_por_clima(cortes, dur, n, cenas, min_sec):
    """Fronteiras nos cortes de MAIOR troca de energia (o mood muda ali). Precisa VLM."""
    scored = []
    for c in cortes:
        if c < min_sec or dur - c < min_sec:
            continue
        shift = abs(_energia_em(cenas, c + 0.01) - _energia_em(cenas, c - 0.01))
        scored.append((shift, c))
    scored.sort(key=lambda x: (-x[0], x[1]))
    escolhidos = []
    for shift, c in scored:
        if shift <= 0:
            break
        if all(abs(c - e) >= min_sec for e in escolhidos):
            escolhidos.append(c)
        if len(escolhidos) == n - 1:
            break
    return sorted([0.0] + escolhidos + [round(dur, 3)]) if len(escolhidos) == n - 1 else None


def _fronteiras_secoes(cortes, dur, n, cenas=None, min_sec=SEC_MIN):
    """n seções → n+1 fronteiras. Com VLM (cenas), corta na troca de energia; senão,
    divisão-igual snapada no corte mais próximo."""
    if dur <= 0:
        return [0.0, max(dur, min_sec)]
    n = max(1, min(n, int(dur // min_sec) or 1))
    if n <= 1:
        return [0.0, dur]

    if cenas:                                    # "assiste o filme": corta onde o mood muda
        por_clima = _fronteiras_por_clima(cortes, dur, n, cenas, min_sec)
        if por_clima:
            return por_clima

    internas = []                                # fallback: divisão-igual snapada no corte
    for i in range(1, n):
        alvo = i * dur / n
        prev = internas[-1] if internas else 0.0
        cand = [c for c in cortes
                if c - prev >= min_sec and dur - c >= min_sec and c > prev]
        best = min(cand, key=lambda c: abs(c - alvo)) if cand \
            else min(max(alvo, prev + min_sec), dur - min_sec)
        internas.append(round(best, 3))
    return sorted(set([0.0] + internas + [round(dur, 3)]))


def _idx_climax(fronteiras, cortes, cenas=None):
    """Índice da seção de pico. Clímax NARRATIVO do VLM (cena climax=True) MANDA — mesmo sinal
    que o foley usa. Sem marcador: maior energia*duração (VLM) ou mais cortes (densidade)."""
    nseg = len(fronteiras) - 1
    if nseg <= 1:
        return 0
    if cenas:                                    # ancora na seção que contém o clímax narrativo
        cx = next((c for c in cenas if c.get("climax")), None)
        if cx is not None:
            t = cx.get("start", 0.0)
            for i in range(nseg):
                if fronteiras[i] <= t < fronteiras[i + 1]:
                    return min(max(i, 1), nseg - 1)   # nunca a Intro
    scores = []
    for i in range(nseg):
        ini, fim = fronteiras[i], fronteiras[i + 1]
        if cenas:
            s = 0.0
            for c in cenas:
                ov = max(0.0, min(fim, c.get("end", 0)) - max(ini, c.get("start", 0)))
                s += _energia_num(c) * ov
            scores.append(s)
        else:
            scores.append(sum(1 for c in cortes if ini <= c < fim))
    cand = list(range(1, nseg))          # clímax nunca é a Intro
    # empate -> seção mais tardia (build emocional costuma picar perto do fim)
    return max(cand, key=lambda i: (scores[i], i)) if cand else 0


def _papeis_secoes(nseg, idx_climax):
    """Nomes das seções: Intro / Build* / Climax / (Outro se nseg>=4)."""
    if nseg <= 1:
        return ["Intro"] * nseg
    nomes = ["Build"] * nseg
    nomes[0] = "Intro"
    ic = idx_climax
    if nseg >= 4:
        nomes[-1] = "Outro"
        if ic >= nseg - 1:
            ic = nseg - 2
    ic = max(1, min(ic, nseg - 1))
    nomes[ic] = "Climax"
    return nomes


def composition_plan(brief: dict, pack: dict | None = None, n_sec: int | None = None) -> dict:
    """Monta o composition_plan do ElevenLabs a partir da análise do vídeo.

    Seções alinhadas aos cortes (respect_sections_durations=true), mood por seção via
    clima (VLM) + gênero do pack. Clímax no pico de energia.
    """
    pack = {**PACK_DEFAULT, **(pack or {})}
    cortes = brief.get("cortes", [])
    dur = brief.get("duracao", 0.0)
    cenas = brief.get("cenas") or []

    # BPM da grade (dos cortes) injetado nos estilos -> música no mesmo tempo dos acentos
    bpm = estima_bpm(cortes, tuple(pack["bpm_range"]), pack["tol"])["bpm"]
    generos = pack.get("generos") or [pack["bed_estilo"]]
    clima_dom = _clima_dominante(cenas)
    pos_global = list(generos) + ([clima_dom] if clima_dom else []) \
        + [f"{bpm} BPM", "steady tempo", "instrumental"]
    neg_global = ["vocals"] + list(pack.get("negativos", []))

    n = n_sec or (4 if dur >= 4 * SEC_MIN else 3)   # peca com folga p/ 4 secoes ganha Outro/resolucao
    fronteiras = _fronteiras_secoes(cortes, dur, n, cenas)
    nseg = len(fronteiras) - 1
    papeis = _papeis_secoes(nseg, _idx_climax(fronteiras, cortes, cenas))
    arco = pack.get("arco") or ARCO_DEFAULT

    sections = []
    for i in range(nseg):
        ini, fim = fronteiras[i], fronteiras[i + 1]
        papel = papeis[i]
        sections.append({
            "section_name": papel,
            "positive_local_styles": list(arco.get(papel, [])),
            "negative_local_styles": [],
            "duration_ms": int(round((fim - ini) * 1000)),
            "lines": [],          # instrumental (ElevenLabs exige o campo, vazio = sem letra)
        })
    # rounding: soma bate a duração total
    total = int(round(dur * 1000))
    if sections:
        sections[-1]["duration_ms"] += total - sum(s["duration_ms"] for s in sections)

    return {
        "positive_global_styles": pos_global,
        "negative_global_styles": neg_global,
        "sections": sections,
        "respect_sections_durations": True,
    }
