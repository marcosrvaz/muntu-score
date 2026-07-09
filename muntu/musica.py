"""Task 8 — musica-base (bed) instrumental. 2 provedores licenciados:

- **stability** (default) — Stable Audio 2.5 via API oficial Stability (`STABILITY_API_KEY`).
  Pay-per-use, sem assinatura. "The pick" pra beds instrumentais (pesquisa jul/2026).
- **elevenlabs** — ElevenLabs Music V2 (`ELEVENLABS_API_KEY`, plano pago). Vence instrumentais.

Escolhe via env `MUNTU_BED_PROVIDER`. Suno VETADO (litigio Sony/UMG + sem API publica +
brand-safety — [[geradores-musica-ia-2026-06]]). A musica e ATMOSFERA; NUNCA carrega o sync
(quem trava a batida sao os stems — ver director.py).

Gated + cache por hash (nao paga 2x). Best-effort no pipeline: falha -> skeleton so-stems.
"""
from __future__ import annotations

import hashlib
import io
import os

from pydub import AudioSegment

CACHE_DIR = "outputs/cache"
DEFAULT_PROVIDER = "stability"


def _prov(provider: str | None) -> str:
    """Provider explicito, senao env MUNTU_BED_PROVIDER, senao stability (lido em runtime)."""
    return provider or os.environ.get("MUNTU_BED_PROVIDER", DEFAULT_PROVIDER)

# --- Stable Audio 2.5 (Stability oficial) ---
STAB_URL = "https://api.stability.ai/v2beta/audio/stable-audio-2/text-to-audio"
STAB_MIN, STAB_MAX = 6, 190           # segundos
STAB_STEPS, STAB_CFG = 50, 6.0        # steps 30-100 (API Stability); 50 = qualidade/velocidade

# --- ElevenLabs Music V2 ---
EL_MODEL, EL_OUTPUT = "music_v2", "mp3_44100_128"
EL_MIN_MS, EL_MAX_MS = 3000, 600000


def _tem_lib(nome: str) -> bool:
    try:
        __import__(nome)
        return True
    except ImportError:
        return False


def musica_disponivel(provider: str | None = None) -> bool:
    """True se o provedor selecionado tem credencial + lib."""
    p = _prov(provider)
    if p == "stability":
        return bool(os.environ.get("STABILITY_API_KEY")) and _tem_lib("requests")
    if p == "elevenlabs":
        return bool(os.environ.get("ELEVENLABS_API_KEY")) and _tem_lib("elevenlabs")
    return False


def _cache_path(chave: str, cache_dir: str) -> str:
    h = hashlib.sha1(chave.encode()).hexdigest()[:16]
    return os.path.join(cache_dir, h)          # sem ext — pydub sniffa o formato


def _gera_stability(prompt: str, duracao: float) -> bytes:
    import requests

    dur = max(STAB_MIN, min(STAB_MAX, int(round(duracao))))
    r = requests.post(
        STAB_URL,
        headers={"Authorization": f"Bearer {os.environ['STABILITY_API_KEY']}",
                 "Accept": "audio/*"},
        files={"none": ""},                    # forca multipart/form-data (padrao v2beta)
        data={"prompt": prompt, "duration": dur, "output_format": "mp3",
              "steps": STAB_STEPS, "cfg_scale": STAB_CFG},
        timeout=180,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Stability {r.status_code}: {r.text[:200]}")
    return r.content


def _sugestao_de_plano(e) -> dict | None:
    """Extrai o composition_plan_suggestion de um erro 400 bad_composition_plan do
    ElevenLabs (filtro de ToS — ex. citar melodia por NOME de obra dispara; a API devolve
    o plano reescrito no fraseado aceito). None se o erro nao traz sugestao."""
    try:
        body = getattr(e, "body", None) or {}
        det = body.get("detail", {})
        if det.get("status") == "bad_composition_plan":
            return det.get("data", {}).get("composition_plan_suggestion")
    except Exception:  # noqa: BLE001
        pass
    return None


def _reconcilia_chunks(plan, cp: dict):
    """create() re-sintetiza os chunks e REDISTRIBUI estilos entre secoes por conta propria
    (visto 2026-07-07: o payoff — sax solo final, motivo do casamento, pico maximo — migrou
    pra secao Cauda, que e descartada no corte). Forca de volta: cada chunk recupera os
    estilos locais da SUA secao; a Cauda vira espelho da secao anterior (energia continua,
    sem payoff exclusivo que seria jogado fora). Best-effort: falha -> plano como veio."""
    try:
        chunks = list(getattr(plan, "chunks", None) or [])
        if not chunks or len(chunks) != len(cp.get("sections", [])):
            return plan

        def _com_estilos(ch, estilos):
            try:
                ch.positive_styles = estilos
                return ch
            except Exception:  # noqa: BLE001 — pydantic frozen
                return ch.model_copy(update={"positive_styles": estilos})

        for i, (ch, sec) in enumerate(zip(chunks, cp["sections"])):
            estilos = list(getattr(ch, "positive_styles", []) or [])
            for e in sec.get("positive_local_styles", []):
                if e not in estilos:
                    estilos.append(e)
            chunks[i] = _com_estilos(ch, estilos)
        for i, sec in enumerate(cp["sections"]):
            if sec.get("section_name") == "Cauda" and i > 0:
                chunks[i] = _com_estilos(chunks[i],
                                         list(getattr(chunks[i - 1], "positive_styles", [])))
        try:
            plan.chunks = chunks
        except Exception:  # noqa: BLE001
            plan = plan.model_copy(update={"chunks": chunks})
        return plan
    except Exception:  # noqa: BLE001 — reconciliacao e best-effort
        return plan


def _gera_elevenlabs(prompt: str, duracao: float, composition_plan: dict | None = None,
                     _retry: bool = True) -> bytes:
    from elevenlabs import ElevenLabs

    client = ElevenLabs()
    if composition_plan is not None:
        # musica COM arco: dict do director -> objeto tipado MusicPrompt (SDK exige)
        from elevenlabs.types.music_prompt import MusicPrompt
        from elevenlabs.types.song_section import SongSection

        cp = composition_plan
        secoes = [SongSection(
            section_name=s["section_name"],
            positive_local_styles=s.get("positive_local_styles", []),
            negative_local_styles=s.get("negative_local_styles", []),
            duration_ms=s["duration_ms"],
            lines=s.get("lines", []),
        ) for s in cp["sections"]]
        source = MusicPrompt(
            positive_global_styles=cp.get("positive_global_styles", []),
            negative_global_styles=cp.get("negative_global_styles", []),
            sections=secoes,
        )
        # music_v2 exige CompositionPlan (chunks); create() converte nossa MusicPrompt
        # (seed) -> chunks, preservando as durações das seções (alinhadas ao filme).
        ms = sum(s["duration_ms"] for s in cp["sections"])
        try:
            plan = client.music.composition_plan.create(
                prompt=", ".join(cp.get("positive_global_styles", [])),
                music_length_ms=ms, model_id=EL_MODEL, source_composition_plan=source)
            plan = _reconcilia_chunks(plan, cp)   # create redistribui estilos -> forca de volta
            # instrumental vem do plano (negative "vocals" + lines vazias)
            resp = client.music.compose(
                composition_plan=plan, model_id=EL_MODEL, output_format=EL_OUTPUT,
                respect_sections_durations=cp.get("respect_sections_durations", True))
        except Exception as e:                   # noqa: BLE001 — 400 de ToS traz plano corrigido
            sugestao = _sugestao_de_plano(e) if _retry else None
            if sugestao is None:
                raise
            import sys
            print("[muntu] plano rejeitado (ToS); retry com a sugestao da API", file=sys.stderr)
            sugestao.setdefault("respect_sections_durations",
                                cp.get("respect_sections_durations", True))
            return _gera_elevenlabs(prompt, duracao, composition_plan=sugestao, _retry=False)
    else:
        ms = max(EL_MIN_MS, min(EL_MAX_MS, int(duracao * 1000)))
        resp = client.music.compose(
            prompt=prompt, music_length_ms=ms, model_id=EL_MODEL,
            force_instrumental=True, output_format=EL_OUTPUT)
    return resp if isinstance(resp, (bytes, bytearray)) else b"".join(resp)


def gera_musica(prompt: str, duracao: float, provider: str | None = None,
               cache_dir: str = CACHE_DIR, composition_plan: dict | None = None) -> AudioSegment:
    """Gera (ou lê do cache) a musica. `composition_plan` (só ElevenLabs) = musica com arco.

    Raise RuntimeError se o provedor nao estiver disponivel e nao houver cache.
    """
    import json

    p = _prov(provider)
    os.makedirs(cache_dir, exist_ok=True)
    plan_tag = hashlib.sha1(json.dumps(composition_plan, sort_keys=True).encode()).hexdigest()[:8] \
        if composition_plan else prompt
    cache = _cache_path(f"{p}|{plan_tag}|{round(duracao, 1)}", cache_dir)
    if os.path.exists(cache):
        return AudioSegment.from_file(cache)

    if not musica_disponivel(p):
        raise RuntimeError(f"provedor '{p}' indisponivel (credencial/lib ausente).")

    if p == "stability":
        audio = _gera_stability(prompt, duracao)
    elif p == "elevenlabs":
        audio = _gera_elevenlabs(prompt, duracao, composition_plan)
    else:
        raise ValueError(f"provedor desconhecido: {p}")

    with open(cache, "wb") as f:
        f.write(audio)
    return AudioSegment.from_file(io.BytesIO(audio))
