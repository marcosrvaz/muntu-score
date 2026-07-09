import os

from pydub import AudioSegment
from pydub.effects import normalize

from muntu import epidemic, musica, mood, reader, sfx_gen, sfx_map, trilha as trilha_mod
from muntu.analyzer import analyze
from muntu.director import (
    carrega_pack, plano_de_score, composition_plan, pack_por_clima, _clima_dominante,
)
from muntu.mixer import mux

BED_GAIN_DB = -3           # MUSICA (trilha) = camada psicologica dominante — veste o filme
# Foley/ambiencia NARRAM as cenas, sempre SOB a musica; foley sobe com a energia da cena
# (VLM 1-5) e fura so no climax narrativo. e1..e5 = -22,-17.5,-13,-8.5,-4 dB; climax = -2
# (acima do topo e5 pra picar). Sem hits de assinatura nos cortes (estetica de trailer, OFF).
AMB_GAIN_DB = -20          # ambiencia (room tone) — leito sob a musica
SFX_GAIN_BASE = -22        # foley energia 1
SFX_GAIN_STEP = 4.5        # e1=-22 .. e5=-4
SFX_CLIMAX_GAIN = -2       # foley no CLIMAX narrativo — fura a musica
MAX_DUR = 30.0             # corta video longo demais (peca de comercial curta)
FADE_IN_MS, FADE_OUT_MS = 150, 400
HEADROOM_DB = 1.0          # teto ~ -1 dBFS — hits nao estouram
PRE_MIX_DB = -6.0          # headroom durante a soma; normalize do _finaliza recupera o nivel


def _soma_camada(base, seg, gain_db, position=0):
    """Overlay com headroom: atenua a camada antes da soma pra nao saturar o clamp
    int do pydub; o normalize em _finaliza devolve o nivel."""
    return base.overlay(seg + gain_db + PRE_MIX_DB, position=position)


def _energia_em(cenas: list, t: float, default: int = 3) -> int:
    """Energia (1-5) da cena que contem t. Default 3 se sem VLM/cena."""
    for c in cenas:
        if c.get("start", 0) <= t < c.get("end", 0):
            e = c.get("energia", default)
            return int(e) if isinstance(e, (int, float)) else default
    return default


def _finaliza(mix):
    """Gain staging da saida: normaliza (sem clipar) + fade in/out."""
    if mix.max_dBFS != float("-inf"):       # silencio total (sem corte, sem musica) nao normaliza
        mix = normalize(mix, headroom=HEADROOM_DB)
    return mix.fade_in(FADE_IN_MS).fade_out(FADE_OUT_MS)


def run(video_path: str, out_path: str = "outputs/scored.mp4", pack: str = "auto",
        com_musica: bool = True, timeline_path: str | None = None,
        banco: bool = False) -> str:
    """`com_musica=False` = mix so com SFX (ambiencia+foley), sem a musica — QA da camada de
    sound design isolada.
    `timeline_path` = PIN: carrega uma timeline travada (JSON) em vez de re-ler o filme —
    regenera so o audio, deterministico contra a estocasticidade do VLM. Loop: roda sem pin
    (auto-grava outputs/timeline_<stem>.json), ouve, e quando boa preserva o JSON e re-roda
    com timeline_path=<esse JSON>.
    `banco=True` = provedor B (Epidemic): seta bed_file das partes score com faixa REAL do
    catalogo licenciado (via mood do reader) — estocasticidade zero. Opt-in; sem key cai em A
    (geracao). Ver muntu/epidemic.py + [[apis-musica-licenciada-2026-07]]."""
    os.makedirs("outputs", exist_ok=True)

    try:
        brief = analyze(video_path)
    except Exception as e:
        raise ValueError(f"nao consegui ler o video (formato invalido?): {e}") from e

    duracao = brief.get("duracao", 0.0)
    if duracao <= 0:
        raise ValueError("video sem duracao valida.")
    duracao = min(duracao, MAX_DUR)                       # corta em 30s
    cortes = [c for c in brief.get("cortes", []) if c < duracao]
    brief["duracao"], brief["cortes"] = duracao, cortes   # a jusante ve so o trecho valido

    # clima por cena (opcional, best-effort) — falha (sem token/credito) cai na heuristica
    if mood.clima_disponivel():
        try:
            brief["cenas"] = mood.analisa_clima(video_path, cortes, duracao)
        except Exception as e:                 # noqa: BLE001 — VLM e best-effort
            print(f"[muntu] VLM indisponivel ({e}); sem clima, seguindo com heuristica")

    # reader narrativo: o VLM segmenta o filme em PARTES da trilha (festa diegetica -> score
    # que desenha a historia), cada uma com registro proprio + o beat de STOP. Guia a trilha
    # por parte (muntu-trilha-por-parte). Best-effort: {} -> cai na musica unica do arco.
    timeline, fonte = {}, "reader"
    if timeline_path:                          # PIN: le a timeline travada, NAO re-le o filme
        timeline = reader.carrega_timeline(timeline_path)
        if timeline.get("partes"):
            fonte = f"PIN {timeline_path}"
        else:
            print(f"[muntu] timeline_path {timeline_path} vazia/invalida; caindo na leitura do filme")
    if not timeline.get("partes") and reader.timeline_disponivel():
        timeline = reader.le_timeline(video_path, cortes, duracao)
    if timeline.get("partes"):
        print(f"[muntu] {fonte}: {len(timeline['partes'])} partes | "
              f"stop=cena {timeline.get('stop_cena')} | climax=cena {timeline.get('climax_cena')}")

    # provedor B (opt-in): faixa REAL do catalogo licenciado (Epidemic) no lugar da geracao.
    # Seta bed_file por parte via o mood do reader -> monta_trilha usa esse mp3 (PIN camada 2).
    # Sem key/match -> parte fica sem bed_file -> cai em A. Nao mexe no diegetico (som do mundo).
    if banco and timeline.get("partes"):
        if epidemic.epidemic_disponivel():
            timeline = epidemic.popula_beds(timeline)
            n = sum(1 for p in timeline["partes"] if p.get("bed_file"))
            print(f"[muntu] banco (Epidemic): {n}/{len(timeline['partes'])} partes com faixa real")
        else:
            print("[muntu] banco pedido mas EPIDEMIC_API_KEY ausente; seguindo em A (geracao)")

    # auto-selecao de mood: o VLM detecta o clima dominante -> a tool escolhe o pack
    # sozinha (o "elo acionado"). Sem VLM (sem cenas) cai no default. Packs contextuais
    # (natal/surf) so via override manual.
    if pack == "auto":
        clima_dom = _clima_dominante(brief.get("cenas") or [])
        pack = pack_por_clima(clima_dom)
        print(f"[muntu] auto-mood: clima='{clima_dom or 'n/d'}' -> pack '{pack}'")

    pack_cfg = carrega_pack(pack)

    # camada de SOUND DESIGN: foley + ambiencia NARRAM as cenas. O VLM le o filme (QUE som
    # cada cena pede); ElevenLabs text->SFX faz o one-shot; colamos no tempo da cena (sync
    # NOSSO, frame-tight). Ambiencia cobre o span da cena; foley na acao. NAO ha hits de
    # assinatura nos cortes — isso e estetica de trailer, descartada (regra do usuario): a
    # trilha veste o filme, o foley narra. Best-effort. Ver muntu-foley-decidido-text-sfx.
    base = AudioSegment.silent(duration=int(duracao * 1000)) + PRE_MIX_DB
    if sfx_map.mapa_disponivel() and sfx_gen.sfx_disponivel():
        cenas = brief.get("cenas") or []
        climax_t = next((c["start"] for c in cenas if c.get("climax")), None)
        for ev in sfx_map.gera_mapa(video_path, cortes, duracao):
            pos = int(ev["t"] * 1000)
            # AMBIENCIA: room tone do LOCAL, cobre a cena (dur), fades curtos, sob a musica
            if ev["ambiencia"]:
                amb = sfx_gen.gera_sfx(ev["ambiencia"], duracao_s=max(1.0, min(ev["dur"], 12.0)))
                if amb is not None:
                    base = _soma_camada(base, amb.fade_in(120).fade_out(200), AMB_GAIN_DB, position=pos)
            # FOLEY de ACAO: one-shot no tempo da cena; sobe com a energia; CLIMAX fura a musica
            if ev["foley"]:
                fol = sfx_gen.gera_sfx(ev["foley"], duracao_s=1.2)
                if fol is not None:
                    if climax_t is not None and abs(ev["t"] - climax_t) < 0.1:
                        gain = SFX_CLIMAX_GAIN
                    else:
                        gain = SFX_GAIN_BASE + (_energia_em(cenas, ev["t"]) - 1) * SFX_GAIN_STEP
                    base = _soma_camada(base, fol, gain, position=pos)

    # trilha (musica) = elemento psicologico: veste a NARRATIVA (mood + energia + climax do
    # VLM via composition_plan), nao os cortes. ElevenLabs gera honrando as duracoes das
    # secoes (arco emocional intro->build->climax->outro). Sem warp/lock mecanico ao corte.
    # Falha (free tier 402, timeout) degrada pro sound design so — nunca derruba o binario.
    mix = base
    prov = musica._prov(None)
    if com_musica and musica.musica_disponivel():
        try:
            if timeline.get("partes"):
                # trilha POR PARTE: cada parte narrativa = sua musica (diegetico|score) + STOP
                # no reveal. Veste a historia trecho a trecho, nao 1 mood chapado.
                bed = trilha_mod.monta_trilha(timeline, duracao, cortes=cortes)
            else:
                # fallback sem reader: musica unica no arco emocional (composition_plan).
                # plano_de_score so aqui (era computado sempre = trabalho morto no path por-parte)
                plan = composition_plan(brief, pack_cfg) if prov == "elevenlabs" else None
                bed_prompt = plano_de_score(brief, pack_cfg)["bed_prompt"]
                bed = musica.gera_musica(bed_prompt, duracao, composition_plan=plan)
            mix = _soma_camada(base, bed, BED_GAIN_DB)  # base (dura=duracao) e o leito; bed entra nela
        except Exception as e:                     # noqa: BLE001 — musica e best-effort
            print(f"[muntu] musica IA indisponivel ({e}); seguindo so com sound design")

    # PONTUACOES: acentos SFX nos beats narrativos que o reader marcou (agulha de vinil no
    # stop, uivo comico no gag) — linguagem classica de filme; 1 one-shot por beat, furando
    # a musica (mesmo gain do climax). O reader ESCOLHE (ou o PIN editado); aqui so executa.
    if sfx_gen.sfx_disponivel():
        for p in timeline.get("pontuacoes") or []:
            try:
                s = sfx_gen.gera_sfx(p["sfx"], duracao_s=1.5)
            except Exception as e:                 # noqa: BLE001 — pontuacao e best-effort
                print(f"[muntu] pontuacao '{p.get('sfx')}' falhou ({e})")
                continue
            if s is not None:
                gain = p.get("gain_db", SFX_CLIMAX_GAIN)   # PIN calibra por pontuacao (ouvido)
                mix = _soma_camada(mix, s, gain, position=int(p["t"] * 1000))

    mix = _finaliza(mix)
    mix.export("outputs/_audio.wav", format="wav")
    return mux(video_path, "outputs/_audio.wav", out_path)
