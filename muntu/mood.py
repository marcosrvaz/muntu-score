"""Analise de clima MULTI-FRAME via VLM.

O mood da trilha vem de ASSISTIR o filme, nao de olhar 1 frame — single-frame erra a
historia (le comedia como romance; ver memoria muntu-mood-precisa-assistir). Aqui:
amostra 1 frame por cena -> monta uma MONTAGEM rotulada (S1..SN, ordem cronologica) ->
o VLM le a sequencia inteira -> mood dominante (registro real: comedia, etc.)
+ energia por cena.

Alimenta a auto-selecao de pack ([[muntu-sfx-cena-nao-mood]]: mood -> trilha) e a
selecao de acentos do director (troca de energia -> acento forte).

Backend = qualquer endpoint OpenAI-compatible de visao (OpenRouter, GLM/Z.ai, etc.),
configurado por env:
  - `MUNTU_MOOD_API_KEY` — key. Sem ela, `clima_disponivel()` = False e `analisa_clima`
    devolve [] -> director cai na heuristica de grade. Binario intacto.
  - `MUNTU_MOOD_URL` — chat completions (default OpenRouter).
  - `MUNTU_MOOD_MODEL` — slug do modelo (default Claude Haiku 4.5 via OpenRouter).

O modelo precisa LER a historia (comedia vs romance), nao so ver 1 frame — por isso um
VLM com raciocinio narrativo (~US$0,0025/video no Haiku; ~0 marginal se vier de assinatura).
"""
from __future__ import annotations

import base64
import json
import math
import os

MODEL = os.environ.get("MUNTU_MOOD_MODEL", "anthropic/claude-haiku-4.5")
MOOD_URL = os.environ.get("MUNTU_MOOD_URL", "https://openrouter.ai/api/v1/chat/completions")

# vocabulario de mood casado com os packs (climas). "comedic"/"playful" -> pack playful.
MOODS = ("romantic", "tender", "nostalgic", "melancholic", "joyful", "playful",
         "comedic", "energetic", "tense", "calm", "epic", "neutral")

# Confianca ESTATICA de valence por mood (tabela β de mapa-vlm-mood-clima-muntu-2026-07):
# quao facil o VLM crava o SINAL emocional daquele mood lendo video. Gate no path de musica
# unica (auto-mood): pack MINOR (tenso/melancolico) sobre leitura fraca = pior erro (inverte
# o clima) -> so dispara com "alta". O path por-parte usa a confianca POR LEITURA do reader.
CONFIANCA_VALENCE = {
    "romantic": "alta", "tender": "alta", "nostalgic": "media", "melancholic": "baixa",
    "joyful": "alta", "playful": "alta", "comedic": "alta", "energetic": "media",
    "tense": "baixa", "calm": "media", "epic": "alta", "neutral": "media",
}

PROMPT = (
    "These are N frames from ONE TV commercial, shown in a single image labeled S1..SN in "
    "chronological order (left-to-right, top-to-bottom).\n"
    "Judge the STORY across ALL frames, not any single one. A commercial can be COMEDIC or "
    "playful even when one frame looks romantic, serious, or sad — read the overall register "
    "from what actually happens across the sequence (a running gag, a twist, an absurd "
    "situation, an emotional build).\n"
    f"Return the dominant MOOD (one of: {', '.join(MOODS)}) and each scene's ENERGY "
    "(1=still/quiet/intimate, 5=intense/climactic/peak).\n"
    "Also read the STORY ARC: write a one-sentence narrative of what happens, and identify "
    "the CLIMAX — the single crucial peak moment of the story (the payoff / punchline / "
    "emotional peak), as the scene number (1..N). The climax is a NARRATIVE judgment, not "
    "just the loudest frame.\n"
    'Return ONLY a JSON object: {"mood": "<one mood>", "energias": [<int per scene, in '
    'order>], "narrativa": "<one sentence>", "climax": <scene number 1..N>}.'
)

CELL_W, CELL_H = 320, 180          # tamanho de cada frame na montagem
MAX_COLS = 4                        # grade ate 4 colunas


def clima_disponivel() -> bool:
    return bool(os.environ.get("MUNTU_MOOD_API_KEY"))


def _cenas_de_cortes(cortes: list[float], duracao: float) -> list[dict]:
    """Spans de cena a partir dos cortes. Cena i>=1 comeca num corte (casa com
    director._clima_forte, que procura cena.start ~= corte)."""
    bounds = [0.0] + list(cortes) + [duracao]
    return [{"start": bounds[i], "end": bounds[i + 1]}
            for i in range(len(bounds) - 1) if bounds[i + 1] > bounds[i]]


def _extrai_frame(video_path: str, t: float):
    """Le 1 frame do video no tempo t (s) como array BGR (cv2). None se falhar."""
    import cv2

    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
    ok, frame = cap.read()
    cap.release()
    return frame if ok else None


def _monta_montagem(frames: list) -> bytes:
    """Tila os frames (BGR) numa grade rotulada S1..SN -> JPEG. Da o filme inteiro
    ao VLM numa imagem so (1 call, ve a historia)."""
    import cv2
    import numpy as np

    n = len(frames)
    cols = min(MAX_COLS, n)
    rows = math.ceil(n / cols)
    canvas = np.zeros((rows * CELL_H, cols * CELL_W, 3), dtype=np.uint8)
    for i, fr in enumerate(frames):
        cell = cv2.resize(fr, (CELL_W, CELL_H))
        cv2.putText(cell, f"S{i + 1}", (8, 28), cv2.FONT_HERSHEY_SIMPLEX,
                    0.9, (0, 255, 0), 2, cv2.LINE_AA)
        r, c = divmod(i, cols)
        canvas[r * CELL_H:(r + 1) * CELL_H, c * CELL_W:(c + 1) * CELL_W] = cell
    ok, buf = cv2.imencode(".jpg", canvas)
    if not ok:
        raise RuntimeError("falha ao codificar a montagem")
    return buf.tobytes()


def _parse_json(txt: str) -> dict:
    """Extrai o objeto {..} tolerando cerca markdown/prosa em volta — modelos menos
    rigidos que o Claude escapam do json_object (GLM et al.)."""
    if not txt:                       # content vazio (finish=length: raciocinio estourou o teto)
        raise ValueError("content vazio do VLM (finish=length? sobe max_tokens)")
    txt = txt.strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        if txt[:4].lower() == "json":
            txt = txt[4:]
    i, j = txt.find("{"), txt.rfind("}")
    if i != -1 and j > i:
        txt = txt[i:j + 1]
    return json.loads(txt)


def _le_historia(montagem: bytes) -> dict:
    """VLM le a montagem -> {mood, energias}. response_format pede JSON; _parse_json
    tolera embrulho de modelos menos rigidos."""
    import httpx

    b64 = base64.standard_b64encode(montagem).decode("utf-8")
    data_uri = f"data:image/jpeg;base64,{b64}"
    resp = httpx.post(
        MOOD_URL,
        headers={"Authorization": f"Bearer {os.environ['MUNTU_MOOD_API_KEY']}"},
        json={
            "model": MODEL,
            "max_tokens": 24000,         # modelos de raciocinio (GLM/Gemini) gastam MUITO token
            #                              pensando; teto alto evita content vazio (finish=length)
            #                              na montagem de N cenas. SEM response_format: Gemini via
            #                              OpenRouter zera o content com ele.
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": data_uri}},
            ]}],
        },
        timeout=120.0,
    )
    resp.raise_for_status()
    txt = resp.json()["choices"][0]["message"]["content"]
    return _parse_json(txt)


def aplica_saida(cenas: list[dict], mood: str, energias: list,
                 narrativa: str = "", climax: int | None = None) -> list[dict]:
    """Aplica mood global + energia por cena + marca a cena de CLIMAX (narrativa do VLM).

    O mood e do FILME (registro da historia) — casa com _clima_dominante do director.
    `climax` = numero de cena 1..N (julgamento narrativo, nao energia crua); marca
    `cena["climax"]=True` na cena do pico. `narrativa` fica na cena de climax pra downstream.
    """
    m = str(mood or "").strip().lower()
    mood = m if m in MOODS else "neutral"   # normaliza case/espaco do VLM; fora do vocab -> "neutral" (casa com packs)
    energias = energias if isinstance(energias, list) else []   # VLM as vezes manda dict/None
    for i, cena in enumerate(cenas):
        e = energias[i] if i < len(energias) else 3
        cena["clima"] = mood
        cena["energia"] = max(1, min(5, int(e))) if isinstance(e, (int, float)) else 3
        cena["climax"] = False
    if isinstance(climax, (int, float)) and cenas:
        idx = min(max(int(climax) - 1, 0), len(cenas) - 1)   # 1-based -> index, clampado
        cenas[idx]["climax"] = True
        cenas[idx]["narrativa"] = narrativa
    return cenas


_MONTAGEM_CACHE: dict = {}
_MONTAGEM_CACHE_MAX = 8    # sessao Gradio longa acumula JPEGs em RAM sem teto; cap simples


def _cache_montagem(chave: tuple, montagem: bytes) -> None:
    """Insere no cache respeitando o teto (FIFO: remove a chave mais antiga ao estourar)."""
    if len(_MONTAGEM_CACHE) >= _MONTAGEM_CACHE_MAX:
        del _MONTAGEM_CACHE[next(iter(_MONTAGEM_CACHE))]
    _MONTAGEM_CACHE[chave] = montagem


def montagem_do_filme(video_path: str, cortes: list[float], duracao: float):
    """Montagem (S1..SN, 1 frame por cena) do filme — extraida 1 VEZ por (video, cortes)
    e reusada por mood/reader/sfx_map (eram 3 extracoes identicas por run). bytes | None."""
    chave = (video_path, tuple(round(c, 3) for c in cortes), round(duracao, 3))
    if chave in _MONTAGEM_CACHE:
        return _MONTAGEM_CACHE[chave]
    frames = []
    for cena in _cenas_de_cortes(cortes, duracao):
        fr = _extrai_frame(video_path, (cena["start"] + cena["end"]) / 2.0)
        if fr is None:
            return None
        frames.append(fr)
    m = _monta_montagem(frames)
    _cache_montagem(chave, m)
    return m


def analisa_clima(video_path: str, cortes: list[float], duracao: float) -> list[dict]:
    """Assiste o filme (multi-frame) -> cenas com clima+energia. [] se indisponivel/falha."""
    if not clima_disponivel():
        return []
    cenas = _cenas_de_cortes(cortes, duracao)
    try:
        m = montagem_do_filme(video_path, cortes, duracao)
        if m is None:
            return []                          # sem frame -> cai na heuristica
        data = _le_historia(m)
        cenas = aplica_saida(cenas, data.get("mood", "neutral"), data.get("energias", []),
                             data.get("narrativa", ""), data.get("climax"))
        nar = data.get("narrativa", "")
        if nar:
            import sys
            cx = next((i + 1 for i, c in enumerate(cenas) if c.get("climax")), "?")
            print(f"[muntu] narrativa: {nar} (climax=cena {cx})", file=sys.stderr)
        return cenas
    except Exception as e:                     # noqa: BLE001 — VLM e best-effort
        import sys
        print(f"[muntu] mood indisponivel ({type(e).__name__}: {e})", file=sys.stderr)
        return []
