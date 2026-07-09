"""Reader narrativo — o VLM LÊ o filme e o segmenta em PARTES da trilha.

Supera o "1 mood -> 1 musica": um comercial narrativo troca de musica quando a HISTORIA
troca (festa = ambiente diegetico saindo das caixas -> ele sai = score que desenha a
historia). O VLM assiste a montagem (S1..SN) e devolve uma TIMELINE de partes, cada uma
com registro proprio + diegetico/score, o climax e o beat de STOP (o reveal onde a musica
para pra piada respirar). Ver memoria muntu-trilha-por-parte.

O CONTEUDO do mapa mood->musica e craft do usuario (aplicado a jusante como lookup); aqui
so LEMOS a estrutura narrativa. Reusa a infra de visao de mood.py. Gated na mesma key
(MUNTU_MOOD_API_KEY). Best-effort: falha -> {} (o pipeline cai no mood/pack unico).
"""
from __future__ import annotations

import base64
import json
import os

from muntu import mood, tags as tags_mod

MAX_TOKENS = 64000   # segmentacao narrativa + N partes + guidance rica = MUITO raciocinio Gemini;
#                      24000 estourava; 48000 voltou a estourar apos calibrar ironia (prompt
#                      maior -> mais raciocinio) -> finish=length/error -> content vazio -> fallback.
MIN_PARTE_S = 1.5    # parte mais curta que isso vira silencio ao gerar -> funde na vizinha

PROMPT = (
    "You are a FILM MUSIC SUPERVISOR watching ONE short TV commercial as a montage of N "
    "scenes labeled S1..SN in chronological order (left-to-right, top-to-bottom).\n"
    "A real score is NOT one mood for the whole film — it changes register as the STORY "
    "turns. Segment the film into NARRATIVE PARTS: each part = one or more CONSECUTIVE "
    "scenes that share a single musical treatment. For each part decide:\n"
    "  - tipo: decide this FIRST, per part. \"diegetic\" = music playing INSIDE the scene's "
    "world from a source on screen or clearly implied — a PARTY / club / bar / dance floor "
    "(the venue's speakers), a car (radio), a store (in-store music), a live band. If a scene "
    "shows a party, people dancing or drinking, a club or a bar, the music there is almost "
    "ALWAYS diegetic — mark it diegetic, do NOT default to score. \"score\" = music laid OVER "
    "the story (composer's, not audible in the world). When a plausible in-world source is "
    "visible, PREFER diegetic.\n"
    "  - mood: a short, specific musical register/genre for this part — DIRECTION, describe "
    "the feel/genre. Fit the ACTUAL tone of the film, ANY genre (comedy, romance, drama, "
    "tension, luxury, epic, nostalgia, horror...). Examples across the range: \"muffled "
    "house music from party speakers\", \"tender 80s romantic ballad\", \"tense pulsing "
    "synth underscore\", \"elegant minimalist piano for a luxury brand\", \"brooding "
    "cinematic strings\", \"triumphant orchestral brass\", \"warm nostalgic acoustic "
    "guitar\", \"quirky comedic pizzicato\".\n"
    "  For DIEGETIC parts the mood MUST match (a) the scene's ERA/period — READ the decade "
    "from on-screen cues (clothing, hair, styling, film grain/look, props, technology): an "
    "80s look means 80s music, retro footage means that era's music, modern means current; "
    "and (b) the film's tone — in a comedic film make the party/source music festive AND "
    "lightly comedic/kitsch (e.g. cheesy party pop, reggaeton, campy disco), not a neutral bed. "
    "It has to feel like it belongs to that world and that year.\n"
    "  For SCORE parts the register can be ANY era/style that serves the film's MOOD. Comedy "
    "can be heightened MANY ways — pick what fits, NOT a default: quirky orchestral pizzicato, "
    "surf rock, a cheesy 1980s retro romantic (saxophone), or gentle/soft music played "
    "straight against the absurdity. Choose the comedic register the film actually calls for.\n"
    "  - clima: the SINGLE closest mood word from this fixed list, to look up a curated "
    "music preset: "
    + ", ".join(mood.MOODS) +
    ".\n"
    "  - confianca_valence: \"alta\" ONLY if the scene clearly shows its emotional SIGN "
    "(clearly upbeat/positive OR clearly dark/negative); \"media\"/\"baixa\" if ambiguous or "
    "subtle. Energy/pace is usually readable; the positive-vs-negative sign is the risky "
    "call — be honest.\n"
    "  - ironia: how the musical register relates to the scene: \"sincero\" (music takes "
    "the emotion straight), \"kitsch\" (deliberately cheesy/campy — the rom-com that takes "
    "itself TOO seriously on purpose), \"deadpan\" (straight music played AGAINST absurdity "
    "— the comedy of contrast), \"parodia\" (mocks a recognizable genre). In a COMEDY film "
    "every score part MUST take a comedic stance — kitsch, deadpan or parodia — never plain "
    "sincero: a sincere register in a comedy loses the joke (a romantic scene in a comedy "
    "is brega/kitsch or deadpan, not a sincere love ballad). When the comedy comes from "
    "treating an absurd premise with FULL sincere emotion (a life story, a romance, an epic "
    "journey — played completely straight), that sincere treatment IS the joke: tag it "
    "kitsch and make the register deliberately cheesy/over-sentimental (e.g. an epic 80s "
    "power ballad with saxophone), NOT deadpan. Deadpan applies ONLY when the footage itself "
    "stays dry, minimal and restrained — no emotional montage, no swelling arc. A "
    "sincere-looking life montage built on an absurd premise = kitsch, always.\n"
    "  - cultura: a cultural/regional musical reference when the scene calls for one "
    "(\"brega\", \"bossa nova\", \"sertanejo\", \"balkan brass\", \"surf rock\", \"mariachi\"); "
    "empty string if none.\n"
    "  - instrumentacao: up to 3 signature instruments that DEFINE the register "
    "([\"saxophone\"], [\"pizzicato strings\", \"ukulele\"]); [] if no strong signature.\n"
    "  - papel: the narrative role of the part (setup / turn / development / payoff / ...).\n"
    "Also identify (film-level):\n"
    "  - era: the film's visual PERIOD read from the footage (clothing, hair, styling, film "
    "look): e.g. \"1980s\", \"1960s\", \"modern day\". Keeps diegetic/source music of the right year.\n"
    "  - comico: true if the FILM is a comedy — played for laughs (an absurd premise, a gag, "
    "a punchline) — even when individual parts use a straight/non-comedic musical register "
    "(comedy is often scored straight against the absurdity); false otherwise.\n"
    "  - climax: the scene number of the story's peak (payoff / punchline / emotional peak).\n"
    "  - stop: the scene number of the KEY dramatic beat where the MUSIC should STOP for a "
    "moment (a reveal, a shock, a sudden realization, a hard narrative turn — of ANY genre) "
    "so the silence lands the moment — or null if the film has no such beat.\n"
    "  - pontuacoes: 0-2 SFX PUNCTUATION marks tied to narrative beats — a single short sound "
    "that lands a joke or a dramatic turn (classic film language: a vinyl needle scratch when "
    "the music is cut, a comedic wolf howl on a romantic gag, a record rewind, a dramatic "
    "sting). Only when the film clearly calls for one; empty list otherwise. Each = scene "
    "number + a short SFX description in plain words.\n"
    "  - citacoes: 0-2 musical QUOTES for classic ceremonial/festive situations shown on "
    "screen whose iconic melody is PUBLIC DOMAIN — wedding → Bridal Chorus (Here Comes the "
    "Bride); funeral → Chopin's Funeral March; Christmas → Jingle Bells; graduation → Pomp "
    "and Circumstance; circus → Entry of the Gladiators; birthday → Happy Birthday. The score "
    "will QUOTE that melody in its own key at that scene (classic scoring language). Only "
    "when the situation is unmistakable on screen AND the melody is public domain; empty "
    "list otherwise. Each = scene number + melody name + the situation.\n"
    'Return ONLY JSON: {"narrativa": "<one sentence>", "era": "<period, e.g. 1980s / modern day>", '
    '"comico": <bool>, "climax": <int>, "stop": <int|null>, '
    '"pontuacoes": [{"cena": <int>, "sfx": "<short SFX description>", "motivo": "<why>"}], '
    '"citacoes": [{"cena": <int>, "melodia": "<public-domain melody name>", "motivo": "<situation>"}], '
    '"partes": [{"cena_ini": <int>, "cena_fim": <int>, "tipo": "diegetic"|"score", '
    '"clima": "<one word from the list>", "confianca_valence": "alta"|"media"|"baixa", '
    '"mood": "<register>", '
    '"ironia": "sincero"|"kitsch"|"deadpan"|"parodia", "cultura": "<ref or empty>", '
    '"instrumentacao": ["<instrument>"], '
    '"papel": "<role>"}]} — partes must cover S1..SN in order, no gaps.'
)


def timeline_disponivel() -> bool:
    """Mesmo gate do VLM de mood (le o filme)."""
    return mood.clima_disponivel()


def _chama(b64: str) -> dict:
    import sys
    import time

    import httpx

    kwargs = dict(
        url=mood.MOOD_URL,
        headers={"Authorization": f"Bearer {os.environ['MUNTU_MOOD_API_KEY']}"},
        json={
            "model": mood.MODEL,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ]}],
        },
        timeout=180.0,
    )
    r = httpx.post(**kwargs)
    if r.status_code == 429 or r.status_code >= 500:
        print(f"[muntu] reader status={r.status_code}, 1 retry em 2s", file=sys.stderr)
        time.sleep(2)
        r = httpx.post(**kwargs)
    r.raise_for_status()
    choice = r.json()["choices"][0]
    finish = choice.get("finish_reason")
    if finish and finish != "stop":
        print(f"[muntu] reader finish_reason={finish} (resposta possivelmente truncada; "
              "calibrar MAX_TOKENS)", file=sys.stderr)
    return mood._parse_json(choice["message"]["content"])


def _cobre(partes: list[dict], cenas: list[dict], duracao: float) -> list[dict]:
    """Ordena por inicio e cola as partes numa cobertura contigua 0..duracao (sem buraco).
    Lista vazia -> 1 parte score cobrindo o filme todo."""
    if not partes:
        return [{"cena_ini": 1, "cena_fim": len(cenas), "start": 0.0, "end": round(duracao, 3),
                 "tipo": "score", "clima": "", "confianca_valence": "media", "mood": "", "papel": ""}]
    partes = sorted(partes, key=lambda p: p["start"])
    partes[0]["start"] = 0.0
    for i in range(1, len(partes)):
        partes[i]["start"] = partes[i - 1]["end"]      # cola no fim da anterior
        if partes[i]["end"] < partes[i]["start"]:       # parte engolida por sobreposicao ->
            partes[i]["end"] = partes[i]["start"]       # vira 0s (_merge_curtas absorve depois)
    partes[-1]["end"] = round(duracao, 3)
    return partes


def _t_de_cena(num, cenas: list[dict]):
    """Tempo (s) de inicio da cena 1-based; None se fora do range."""
    return round(cenas[num - 1]["start"], 3) if isinstance(num, int) and 1 <= num <= len(cenas) else None


def _e_num(x) -> bool:
    """int/float que NAO seja bool (bool e subclasse de int -> True passaria como cena 1)."""
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _merge_curtas(partes: list[dict], min_s: float = MIN_PARTE_S) -> list[dict]:
    """Funde partes curtas demais (< min_s) na anterior (sliver de 0.2s = silencio ao gerar).
    Primeira parte curta funde na seguinte. Preserva cobertura contigua."""
    if len(partes) <= 1:
        return partes
    out = [dict(partes[0])]
    for p in partes[1:]:
        if p["end"] - p["start"] < min_s:
            out[-1]["end"] = p["end"]                  # estende a anterior; descarta o sliver
            out[-1]["cena_fim"] = p["cena_fim"]
        else:
            out.append(dict(p))
    if len(out) > 1 and out[0]["end"] - out[0]["start"] < min_s:
        out[1]["start"], out[1]["cena_ini"] = out[0]["start"], out[0]["cena_ini"]
        out = out[1:]
    return out


def _beats(itens, campo: str, cenas: list[dict]) -> list[dict]:
    """Normaliza beats {cena, <campo>, motivo} do VLM -> + tempo. Descarta cena fora do
    range, campo vazio ou item nao-dict. Compartilhado por pontuacoes (sfx) e citacoes
    (melodia)."""
    out = []
    for p in itens or []:
        c = p.get("cena") if isinstance(p, dict) else None
        t = _t_de_cena(int(c), cenas) if _e_num(c) else None
        valor = (p.get(campo) or "").strip() if isinstance(p, dict) else ""
        if t is not None and valor:
            out.append({"cena": int(c), "t": t, campo: valor,
                        "motivo": (p.get("motivo") or "").strip()})
    return out


def _normaliza(data: dict, cenas: list[dict], duracao: float) -> dict:
    """Valida a saida do VLM: cena_ini/fim (1-based) -> tempos, tipo diegetic|score,
    cobertura contigua, climax/stop numericos (cena + tempo). cenas=[] (filme sem cena
    legivel) -> partes=[] sem crashar. Parte individual ilegivel (cena_ini nao numerico,
    item que nao e objeto) e descartada isolada -> nao derruba as partes validas."""
    import sys

    n = len(cenas)
    partes = []
    for p in (data.get("partes", []) if cenas else []):
        try:
            ini = max(1, min(int(p.get("cena_ini", 1)), n))
            fim = max(ini, min(int(p.get("cena_fim", ini)), n))
        except (AttributeError, TypeError, ValueError) as e:
            print(f"[muntu] parte ilegivel descartada ({e}): {p!r}", file=sys.stderr)
            continue
        tipo = "diegetic" if str(p.get("tipo", "score")).lower().startswith("dieg") else "score"
        partes.append({
            "cena_ini": ini, "cena_fim": fim,
            "start": round(cenas[ini - 1]["start"], 3),
            "end": round(cenas[fim - 1]["end"], 3),
            "tipo": tipo,
            "clima": (p.get("clima") or "").strip().lower(),   # vocab -> lookup do pack curado
            "confianca_valence": (p.get("confianca_valence") or "media").strip().lower(),  # gate minor
            "mood": (p.get("mood") or "").strip(),             # direcao free-text (refino/diegetico)
            "papel": (p.get("papel") or "").strip(),
            # tags ricas (learn-from-ads camada 1): o que o clima não segura.
            # Ausentes (timeline PINada antiga) -> defaults; ver muntu/tags.py
            "ironia": tags_mod.normaliza_ironia(p.get("ironia")),
            "cultura": (p.get("cultura") or "").strip().lower() if isinstance(p.get("cultura"), str) else "",
            "instrumentacao": [str(i).strip() for i in (p.get("instrumentacao") or [])
                               if isinstance(i, str) and i.strip()][:3],
        })
    climax, stop = data.get("climax"), data.get("stop")
    climax = int(climax) if _e_num(climax) else None
    stop = int(stop) if _e_num(stop) else None
    # PONTUACOES: beats de SFX que o reader marcou (agulha de vinil, uivo comico...) —
    # cena -> tempo; sem sfx ou cena fora do range = descartada
    pontuacoes = _beats(data.get("pontuacoes"), "sfx", cenas)
    # CITACOES: situacao classica na tela (casamento/funeral/Natal...) -> quote de melodia
    # de dominio publico na tonalidade do score (linguagem classica de scoring)
    citacoes = _beats(data.get("citacoes"), "melodia", cenas)
    comico = data.get("comico")
    return {
        "narrativa": (data.get("narrativa") or "").strip(),
        "era": (data.get("era") or "").strip(),          # ano do filme (visual) -> diegetico
        "comico": comico if isinstance(comico, bool) else None,   # filme e comedia? (film-level;
        #                                                           None = reader nao disse -> fallback partes)
        "climax_cena": climax,
        "stop_cena": stop,
        "climax_t": _t_de_cena(climax, cenas),
        "stop_t": _t_de_cena(stop, cenas),
        # fim da cena do stop = o CORTE seguinte: o wind-down diegetico (vitrola desligando)
        # ocupa stop_t..stop_fim_t inteiro, e a agulha cai exatamente no corte
        "stop_fim_t": (round(cenas[stop - 1]["end"], 3)
                       if isinstance(stop, int) and 1 <= stop <= len(cenas) else None),
        "pontuacoes": pontuacoes,
        "citacoes": citacoes,
        "partes": [] if not cenas else _merge_curtas(_cobre(partes, cenas, duracao)),
    }


def timeline_scratch_path(video_path: str) -> str:
    """outputs/timeline_<stem>.json — auto-dump da ultima leitura do filme.
    E o SCRATCH (sobrescrito a cada read). Pra travar (PIN) uma leitura boa, preservar
    este arquivo com outro nome e re-rodar com `run(..., timeline_path=<esse nome>)`.
    Separa 'ler o filme' de 'gerar audio' -> reprodutibilidade contra a estocasticidade do VLM."""
    stem = os.path.splitext(os.path.basename(video_path))[0]
    return os.path.join("outputs", f"timeline_{stem}.json")


def salva_timeline(timeline: dict, path: str) -> None:
    """Grava a timeline (JSON). Best-effort: erro de IO nao quebra o pipeline."""
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(timeline, f, ensure_ascii=False, indent=2)
    except OSError as e:                       # noqa: BLE001 — dump e best-effort
        import sys
        print(f"[muntu] nao gravei timeline scratch ({e})", file=sys.stderr)


def carrega_timeline(path: str) -> dict:
    """Le uma timeline PINada (JSON) -> regenera so o audio, sem re-ler o filme.
    {} se nao existe/invalida (best-effort -> pipeline cai na musica unica)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def le_timeline(video_path: str, cortes: list[float], duracao: float) -> dict:
    """Le o filme -> timeline narrativa {narrativa, climax_cena, stop_cena, partes[]}.
    Auto-grava a leitura em timeline_scratch_path (pra inspecao/PIN posterior).
    {} se indisponivel/falha (best-effort). `partes` = trilha por parte (diegetic|score)."""
    if not timeline_disponivel():
        return {}
    cenas = mood._cenas_de_cortes(cortes, duracao)
    try:
        m = mood.montagem_do_filme(video_path, cortes, duracao)   # extraida 1x, compartilhada
        if m is None:
            return {}
        b64 = base64.standard_b64encode(m).decode("utf-8")
        tl = _normaliza(_chama(b64), cenas, duracao)
        salva_timeline(tl, timeline_scratch_path(video_path))   # captura pra travar depois
        return tl
    except Exception as e:                     # noqa: BLE001 — best-effort
        import sys
        print(f"[muntu] reader indisponivel ({type(e).__name__}: {e})", file=sys.stderr)
        return {}
