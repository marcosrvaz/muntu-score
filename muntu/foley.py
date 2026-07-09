"""Camada de FOLEY — sound design por corte, guiado pela CENA REAL (nao pelo mood).

Divisao de sinais (decisao do usuario 2026-07-06, ver memoria muntu-sfx-cena-nao-mood +
pesquisa sound-design-ia-2026-06):

- **mood** guia a TRILHA (musica/musica — musica).
- **cena real** guia o FOLEY (o som fisico que casa com a acao na tela — aqui).

Motor = MMAudio v2 (Replicate, `zsxkib/mmaudio-t4`): ve os frames do corte e gera audio
sincronizado ao movimento. `negative_prompt="music"` -> foley NAO gera musica (a musica e
outra camada). E o unico video->foley com API (ElevenLabs video-to-sound e so web).

Hierarquia anti-commodity: foley VARIA nos cortes comuns; o stem de ASSINATURA crava o
climax + o fechamento (brand sting) — o diferencial Muntu e a curadoria, nao o gerador.
Ver `seleciona_assinatura`.

Gated no `REPLICATE_API_TOKEN` (mesmo token do VLM de mood). Best-effort: falha (sem key/
credito, ffmpeg, timeout, formato) -> o corte cai no stem/beep. Binario nunca quebra.
Cache por (video, mtime, corte) — nao paga 2x pelo mesmo corte.
"""
from __future__ import annotations

import hashlib
import io
import os
import subprocess
import tempfile

from pydub import AudioSegment

# slug puro resolve a ultima versao no client atual; pina via env se der 404 (best-effort
# degrada de qualquer forma). Ex: MUNTU_FOLEY_MODEL="zsxkib/mmaudio-t4:<hash>"
MODEL = os.environ.get("MUNTU_FOLEY_MODEL", "zsxkib/mmaudio")
CACHE_DIR = "outputs/cache/foley"
JANELA_PRE, JANELA_POS = 1.25, 1.25      # s ao redor do corte — foley "ve" a acao
NEG_PROMPT = ("music, musical, melody, soundtrack, score, singing, "
              "speech, voice, talking, dialogue, narration")   # so foley fisico (musica+voz = outras camadas)
NUM_STEPS = 25                            # default do modelo; menos = mais barato/rapido
FOLEY_GAIN_DB = -3                        # foley senta sob os acentos de assinatura


def foley_disponivel() -> bool:
    """True se ha token Replicate + lib. Mesmo gate do VLM de mood."""
    if not os.environ.get("REPLICATE_API_TOKEN"):
        return False
    try:
        import replicate  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------- puros (testaveis sem API/ffmpeg) ----------------

def _janela(corte: float, duracao: float,
            pre: float = JANELA_PRE, pos: float = JANELA_POS) -> tuple[float, float]:
    """Bordas da janela de video ao redor do corte, presas em [0, duracao]."""
    return max(0.0, corte - pre), min(duracao, corte + pos)


def _energia_da_cena(t: float, cenas) -> float:
    for c in (cenas or []):
        if c.get("start", 0) <= t < c.get("end", 0):
            e = c.get("energia", 3)
            return float(e) if isinstance(e, (int, float)) else 3.0
    return 3.0


def seleciona_assinatura(acentos: list, cenas=None) -> set:
    """Indices dos acentos que FICAM com stem de assinatura (climax + fechamento).

    O resto vira foley. Climax = maior energia de cena (VLM) ou, sem VLM, o acento
    'impact' mais tardio (build emocional pica perto do fim). Fechamento = ultimo acento.
    """
    if not acentos:
        return set()
    n = len(acentos)
    fim = max(range(n), key=lambda i: acentos[i]["t_audio"])
    if cenas:
        climax = max(range(n),
                     key=lambda i: (_energia_da_cena(acentos[i]["t_video"], cenas),
                                    acentos[i]["t_audio"]))
    else:
        impactos = [i for i in range(n) if acentos[i].get("tipo") == "impact"]
        climax = max(impactos or list(range(n)), key=lambda i: acentos[i]["t_audio"])
    return {climax, fim}


def _cache_key(video_path: str, corte: float, prompt: str = "") -> str:
    try:
        mt = int(os.path.getmtime(video_path))
    except OSError:
        mt = 0
    return f"{os.path.basename(video_path)}|{mt}|{round(corte, 3)}|{prompt}"


def _cache_path(chave: str, cache_dir: str) -> str:
    h = hashlib.sha1(chave.encode()).hexdigest()[:16]
    return os.path.join(cache_dir, h + ".mp3")


# ---------------- gated (API/ffmpeg) ----------------

def _extrai_janela(video_path: str, inicio: float, fim: float) -> str:
    """Recorta o trecho de VIDEO (sem audio) ao redor do corte -> mp4 temporario."""
    dst = tempfile.mktemp(suffix=".mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-ss", f"{inicio}", "-i", video_path, "-t", f"{max(0.1, fim - inicio)}",
         "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", dst],
        check=True, capture_output=True,
    )
    return dst


def _baixa(out) -> bytes:
    """Normaliza a saida do replicate.run (FileOutput / url / lista) -> bytes."""
    if isinstance(out, (list, tuple)):
        out = out[0]
    if hasattr(out, "read"):                 # FileOutput
        return out.read()
    url = out if isinstance(out, str) else getattr(out, "url", None)
    if url:
        import requests
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        return r.content
    raise RuntimeError("saida MMAudio em formato inesperado")


RETRY_429 = 4                             # tier throttled (6/min burst 1) espera o reset e re-tenta
RETRY_ESPERA_S = 12                       # 6/min = 1 a cada ~10s; 12s folga


def _gera_mmaudio(clip_path: str, prompt: str, duration: float) -> AudioSegment:
    import re
    import time

    import replicate

    for tentativa in range(RETRY_429):
        try:
            with open(clip_path, "rb") as v:
                out = replicate.run(MODEL, input={
                    "video": v,
                    "prompt": prompt,
                    "negative_prompt": NEG_PROMPT,
                    "duration": max(1.0, round(duration, 2)),
                    "num_steps": NUM_STEPS,
                })
            return AudioSegment.from_file(io.BytesIO(_baixa(out)))   # mp4 (video+audio) -> audio
        except Exception as e:                       # noqa: BLE001
            msg = str(e)
            if ("429" in msg or "throttl" in msg.lower()) and tentativa < RETRY_429 - 1:
                m = re.search(r"resets in ~(\d+)", msg)
                time.sleep(max(RETRY_ESPERA_S, (int(m.group(1)) + 2) if m else 0))
                continue
            raise
    raise RuntimeError("mmaudio: retries de 429 esgotados")


def gera_foley_de_corte(video_path: str, corte: float, duracao: float,
                        prompt: str = "", cache_dir: str = CACHE_DIR) -> AudioSegment | None:
    """Foley da janela ao redor do corte. None (best-effort) se indisponivel ou falhar.

    O audio devolvido cobre a JANELA (nao o corte cru); posicione em `_janela(corte,...)[0]`
    pra preservar a sincronia interna do modelo (o som da acao cai onde a acao esta).
    """
    if not foley_disponivel():
        return None
    os.makedirs(cache_dir, exist_ok=True)
    cache = _cache_path(_cache_key(video_path, corte, prompt), cache_dir)
    if os.path.exists(cache):
        return AudioSegment.from_file(cache)

    inicio, fim = _janela(corte, duracao)
    clip = None
    try:
        clip = _extrai_janela(video_path, inicio, fim)
        seg = _gera_mmaudio(clip, prompt, fim - inicio)
        seg.export(cache, format="mp3")
        return seg
    except Exception as e:                   # noqa: BLE001 — foley e best-effort
        import sys
        print(f"[muntu] foley corte {corte:.1f}s falhou ({type(e).__name__}: {e})", file=sys.stderr)
        return None
    finally:
        if clip and os.path.exists(clip):
            os.remove(clip)
