"""Tagueador — LLM/VLM etiqueta comerciais REAIS no tag-schema (learn-from-ads).

O "aprendizado" do sistema É a extração: nada de treinar modelo — o VLM assiste a
montagem (música/cena) e o áudio-model OUVE o ad (SFX/VO) e devolvem tags no schema
de muntu/tags.py. Este módulo é o SPIKE do crux (spec §2.7): validar que o modelo lê
registro fino (ironia, cultura, traço de voz) ANTES de construir banco. Reusa a infra
de visão de mood.py; gated na mesma key. Best-effort: falha -> [] / {}.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile

from muntu import mood, tags

MAX_TOKENS = 48000   # ad longo (100+ cenas, ex. Sky La famiglia) truncava em 16k
#                      (finish=length -> musica []) — mesmo sintoma do reader; espelha o fix.


PROMPT_MUSICA = (
    "You are a MUSIC SUPERVISOR analyzing ONE real TV commercial. You SEE the film as a "
    "montage of N scenes labeled S1..SN (chronological) AND you HEAR its full soundtrack "
    "(attached audio). Tag the music ACTUALLY PLAYING in the audio, part by part — the "
    "visuals only give story context; NEVER guess the music from the footage. This builds "
    "a reference library of how real ads score story.\n"
    "IMPORTANT: atmospheric/analog-synth textures ARE music (score) when they carry an "
    "emotional arc or pitch material — do NOT dismiss a synth score as 'ambience/wind'; "
    "only pure non-musical room tone counts as no-music.\n"
    "A film may open with a LONG music-free stretch (only narration/wind/room tone) before "
    "the score enters — if music enters at ANY point, you MUST tag it (span approximate is "
    "fine). Return an empty partes list ONLY if the ENTIRE film truly has no music.\n"
    "For each musical part (a stretch with one musical treatment) return:\n"
    "  - span: which scenes it covers, free text (e.g. \"S1-S3, the party opening\").\n"
    "  - era: the SOUND's period (\"1980s\", \"1960s\", \"modern\").\n"
    "  - registro: short specific register/genre description of what you HEAR in the "
    "audio (\"cheesy 80s power ballad\", \"quirky comedic pizzicato\").\n"
    "  - ironia: \"sincero\" (straight emotion) | \"kitsch\" (deliberately cheesy/campy) | "
    "\"deadpan\" (straight music AGAINST absurdity) | \"parodia\" (mocks a genre).\n"
    "  - cultura: cultural/regional reference (\"brega\", \"bossa nova\", \"balkan brass\", "
    "\"surf rock\") or \"\".\n"
    "  - funcao: setup | build | payoff | reveal | transicao | assinatura.\n"
    "  - instrumentacao: up to 3 signature instruments.\n"
    "  - mode: major | minor | ambiguous.  - bpm: estimated int or null.\n"
    'Return ONLY JSON: {"partes": [{"span": "...", "era": "...", "registro": "...", '
    '"ironia": "...", "cultura": "...", "funcao": "...", "instrumentacao": [...], '
    '"mode": "...", "bpm": <int|null>}]}'
)


def disponivel() -> bool:
    """Mesmo gate do reader/mood (le o filme)."""
    return mood.clima_disponivel()


def _chama(content: list, max_tokens: int = MAX_TOKENS) -> dict:
    """POST OpenRouter (mesmo backend do reader) com content multimodal arbitrário."""
    import httpx
    r = httpx.post(
        url=mood.MOOD_URL,
        headers={"Authorization": f"Bearer {os.environ['MUNTU_MOOD_API_KEY']}"},
        json={"model": mood.MODEL, "max_tokens": max_tokens,
              "messages": [{"role": "user", "content": content}]},
        timeout=240.0,
    )
    r.raise_for_status()
    choice = r.json()["choices"][0]
    finish = choice.get("finish_reason")
    if finish and finish != "stop":
        # diagnostico honesto: length = subir max_tokens; content_filter/safety = outro bicho
        import sys
        print(f"[muntu] tagueador finish_reason={finish}", file=sys.stderr)
    return mood._parse_json(choice["message"]["content"])


def _normaliza_musica(data: dict) -> list[dict]:
    """Saída do VLM -> lista de TAGS_MUSICA validadas (+span). Item ilegível cai fora."""
    out = []
    for p in (data.get("partes") or []) if isinstance(data, dict) else []:
        if not isinstance(p, dict):
            continue
        t = tags.valida_tags(p, "music")
        t["span"] = (p.get("span") or "").strip()
        out.append(t)
    return out


def _bloco_faixas(faixas: list[dict] | None) -> str:
    """Matches do fingerprinting (faixa_id) -> bloco de ground truth no prompt. O Gemini
    descreve registro mas não nomeia faixa; o AudD nomeia — quando há match, o modelo
    DEVE ancorar era/cultura/registro na faixa real, não no que acha que ouviu."""
    if not faixas:
        return ""
    linhas = []
    for fx in faixas:
        gen = f" [{', '.join(fx['generos'])}]" if fx.get("generos") else ""
        ano = f" ({fx['ano']})" if fx.get("ano") else ""
        linhas.append(f"- \"{fx.get('titulo', '')}\" — {fx.get('artista', '')}{ano}{gen}"
                      f" heard around {fx.get('em_s', '?')}s")
    return ("\nCANDIDATE track IDs from audio fingerprinting — the matcher sometimes "
            "returns FALSE positives. For each candidate: if it matches what you actually "
            "HEAR at that position, anchor era/cultura/registro on it and NAME it in the "
            "registro; if it contradicts your ears, IGNORE it silently:\n"
            + "\n".join(linhas) + "\n")


def tagueia_musica(video_path: str, cortes: list[float], duracao: float,
                   faixas: list[dict] | None = None) -> list[dict]:
    """Ad real -> tags de música por parte OUVINDO a trilha (montagem dá só o contexto
    de história). Calibração do spike 2026-07-09: só-frames fazia o modelo CHUTAR a
    música pelo visual (BK "epic fanfare" e Mariachis "indie rock" — ambos errados de
    ouvido). `faixas` (fingerprinting) entram como ground truth no prompt.
    [] se indisponível/falha (best-effort)."""
    if not disponivel():
        return []
    wav = None
    try:
        m = mood.montagem_do_filme(video_path, cortes, duracao)
        if m is None:
            return []
        b64 = base64.standard_b64encode(m).decode("utf-8")
        wav = _extrai_audio(video_path, sr=32000)  # música pede banda; mp3 = payload 4x menor
        with open(wav, "rb") as f:
            b64_wav = base64.standard_b64encode(f.read()).decode("utf-8")
        return _normaliza_musica(_chama([
            {"type": "text", "text": PROMPT_MUSICA + _bloco_faixas(faixas)},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            {"type": "input_audio", "input_audio": {"data": b64_wav, "format": "mp3"}},
        ]))
    except Exception as e:                     # noqa: BLE001 — best-effort
        import sys
        print(f"[muntu] tagueador musica falhou ({type(e).__name__}: {e})", file=sys.stderr)
        return []
    finally:
        if wav and os.path.exists(wav):
            os.remove(wav)


PROMPT_AUDIO = (
    "You are a SOUND DESIGNER + VOICE CASTING DIRECTOR listening to the full audio of ONE "
    "real TV commercial. Tag what you HEAR (ignore the music — another pass covers it):\n"
    "1) sfx: {\"ambiencia\": \"<bed/room tone, e.g. 'indoor party crowd'>\", "
    "\"eventos\": [up to 3 short foley/event sounds], \"assinatura\": \"<the ONE sound that "
    "lands the climax, or ''>\"}.\n"
    "2) vo: the voiceover/narration VOICE (null if there is NO spoken voiceover): "
    "{\"genero\": \"male|female|neutral\", \"idade\": \"young adult|middle-aged|elderly\", "
    "\"tom\": \"autoritario|caloroso|hype|luxo-sussurro|deadpan-comico\", "
    "\"timbre\": \"deep|warm|gravelly|smooth|raspy|breathy\", "
    "\"pace\": \"fast|measured|slow\", \"sotaque\": \"<accent, e.g. 'neutro BR'>\", "
    "\"energia\": <1-5>}.\n"
    'Return ONLY JSON: {"sfx": {...}, "vo": {...}|null}'
)


def _extrai_audio(video_path: str, sr: int = 16000, fmt: str = "mp3") -> str:
    """Trilha de áudio do ad -> arquivo mono temp. mp3 128k, não wav: ad de 105s em wav
    32kHz vira ~9MB de base64 e o modelo não processa o áudio inteiro (MP Marte: música
    entra depois do vento e ficou invisível 4 rodadas). 16kHz basta pra fala/SFX; MÚSICA
    pede 32kHz (a 16k o registro fino some — caso Pepsi/Danúbio). Chamador apaga."""
    fd, dst = tempfile.mkstemp(suffix=f".{fmt}")
    os.close(fd)
    cmd = ["ffmpeg", "-y", "-i", video_path, "-ac", "1", "-ar", str(sr)]
    if fmt == "mp3":
        cmd += ["-b:a", "128k"]
    subprocess.run(cmd + [dst], check=True, capture_output=True)
    return dst


def _normaliza_audio(data) -> dict:
    """Saída do modelo -> {sfx, vo} validados. vo null preservado (ad sem locução)."""
    if not isinstance(data, dict):
        return {"sfx": None, "vo": None}
    sfx = tags.valida_tags(data["sfx"], "sfx") if isinstance(data.get("sfx"), dict) else None
    vo = tags.valida_tags(data["vo"], "vo") if isinstance(data.get("vo"), dict) else None
    return {"sfx": sfx, "vo": vo}


def tagueia_audio(video_path: str) -> dict:
    """Ad real -> tags de SFX + VO OUVINDO o áudio (não os frames — traço de voz é
    análise de áudio, spec §2.2). {"sfx": None, "vo": None} se indisponível/falha."""
    if not disponivel():
        return {"sfx": None, "vo": None}
    wav = None
    try:
        wav = _extrai_audio(video_path)
        with open(wav, "rb") as f:
            b64 = base64.standard_b64encode(f.read()).decode("utf-8")
        return _normaliza_audio(_chama([
            {"type": "text", "text": PROMPT_AUDIO},
            {"type": "input_audio", "input_audio": {"data": b64, "format": "mp3"}},
        ]))
    except Exception as e:                     # noqa: BLE001 — best-effort
        import sys
        print(f"[muntu] tagueador audio falhou ({type(e).__name__}: {e})", file=sys.stderr)
        return {"sfx": None, "vo": None}
    finally:
        if wav and os.path.exists(wav):
            os.remove(wav)


def _analisa_video(video_path: str) -> tuple[list[float], float]:
    """Cortes+duração via analyzer (import tardio: cv2/scenedetect pesados)."""
    from muntu.analyzer import analyze
    brief = analyze(video_path)
    return brief["cortes"], brief["duracao"]


def tagueia_ad(video_path: str) -> dict:
    """Ad completo -> ID de faixa (fingerprinting) + tags de música (vídeo+áudio) +
    SFX/VO (áudio). O deliverable do spike."""
    from muntu import faixa_id
    cortes, duracao = _analisa_video(video_path)
    faixas = faixa_id.identifica(video_path)
    audio = tagueia_audio(video_path)
    return {"video": video_path,
            "faixas": faixas,
            "musica": tagueia_musica(video_path, cortes, duracao, faixas=faixas),
            "sfx": audio["sfx"], "vo": audio["vo"]}
