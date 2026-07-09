"""Tag-schema — vocabulário compartilhado do sistema learn-from-ads.

Um tagueamento alimenta DUAS pontas: A (geração — tags viram prompt ElevenLabs) e
B (seleção — tags viram query do banco). O rótulo de mood subdetermina a partitura
(pesquisa climas-trilha §1); estas dimensões carregam o que o mood não segura:
registro/ironia, cultura, função narrativa, instrumentação-assinatura.

Ancoragem: Artlist dictionaries (mood/genre/instruments/themes) + AudioSet Music-mood.
Os eixos ironia/funcao/cultura são autorais — nenhuma taxonomia pública os cobre.
Ver docs/spec-arquitetura-learn-ads-2026-07-08.md §2.2 e o plano-mestre 2026-07-09.
"""
from __future__ import annotations

# Como o registro musical se relaciona com a cena (o eixo que o clima "romantic"
# sincero da comédia Pringles NÃO tinha — e por isso o humor se perdeu):
#   sincero  = a música leva a emoção a sério (drama, luxo, romance real)
#   kitsch   = deliberadamente cafona/brega (a comédia romântica que se leva a sério DEMAIS)
#   deadpan  = música straight CONTRA o absurdo (a comédia do contraste)
#   parodia  = imita/zomba um gênero reconhecível
IRONIA = ("sincero", "kitsch", "deadpan", "parodia")

# Papel narrativo da música na parte (não da cena): o que ela FAZ na história.
FUNCAO = ("setup", "build", "payoff", "reveal", "transicao", "assinatura")

MODE = ("major", "minor", "ambiguous")

# ---- dimensões por tipo de asset (defaults = valor neutro) ----

TAGS_MUSICA = {
    "era": "",              # período SONORO: "1980s", "1960s", "modern" (livre)
    "registro": "",         # free-text rico: "cheesy 80s power ballad, tongue-in-cheek"
    "ironia": "sincero",
    "cultura": "",          # referência cultural/regional: "brega", "bossa nova",
    #                         "sertanejo", "balkan brass", "surf rock"; "" = neutra
    "funcao": "",
    "instrumentacao": [],   # assinaturas: ["saxophone", "pizzicato strings"] (máx 3)
    "mode": "ambiguous",    # valence — knob 1 da pesquisa climas-trilha
    "bpm": None,            # arousal — knob 2; int ou None
}

TAGS_SFX = {
    "ambiencia": "",        # "indoor party crowd", "beach waves distant"
    "eventos": [],          # foley/eventos curtos: ["glass clink", "needle scratch"]
    "assinatura": "",       # o som que CRAVA o clímax ("champagne cork pop")
}

TAGS_VO = {                 # 6 eixos ElevenLabs Voice Design + registro
    "genero": "",           # male | female | neutral
    "idade": "",            # young adult | middle-aged | elderly ...
    "tom": "",              # autoritario | caloroso | hype | luxo-sussurro | deadpan-comico
    "timbre": "",           # deep | warm | gravelly | smooth | raspy | breathy
    "pace": "",             # fast | measured | slow
    "sotaque": "",          # "neutro BR", "carioca", "US southern"
    "energia": 3,           # 1-5
}

_SCHEMAS = {"music": TAGS_MUSICA, "sfx": TAGS_SFX, "vo": TAGS_VO}


def normaliza_ironia(valor) -> str:
    """Clampa ao vocabulário; desconhecido/vazio -> "sincero" (o default seguro:
    kitsch aplicado por engano é pior erro que sinceridade a mais)."""
    v = (valor or "").strip().lower() if isinstance(valor, str) else ""
    return v if v in IRONIA else "sincero"


def valida_tags(tags: dict, tipo: str = "music") -> dict:
    """Saída de LLM -> tags válidas no schema do tipo. Campo desconhecido cai fora;
    campo ausente ganha default; enum fora do vocabulário -> default. Nunca levanta:
    entrada lixo -> schema default (best-effort, padrão do repo)."""
    schema = _SCHEMAS.get(tipo, TAGS_MUSICA)
    out = {}
    src = tags if isinstance(tags, dict) else {}
    for campo, default in schema.items():
        v = src.get(campo, default)
        if isinstance(default, list):
            out[campo] = [str(i).strip() for i in v if str(i).strip()][:3] if isinstance(v, (list, tuple)) else []
        elif isinstance(default, str):
            out[campo] = str(v).strip() if isinstance(v, str) else default
        elif campo == "bpm":
            out[campo] = int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else None
        elif isinstance(default, int):
            try:
                out[campo] = max(1, min(5, int(v)))
            except (TypeError, ValueError):
                out[campo] = default
        else:
            out[campo] = v
    if "ironia" in schema:
        out["ironia"] = normaliza_ironia(src.get("ironia"))
    if "mode" in schema:
        m = (src.get("mode") or "").strip().lower() if isinstance(src.get("mode"), str) else ""
        out["mode"] = m if m in MODE else "ambiguous"
    if "funcao" in schema:
        f = (src.get("funcao") or "").strip().lower() if isinstance(src.get("funcao"), str) else ""
        out["funcao"] = f if f in FUNCAO else ""
    return out


def descritor(tags: dict, tipo: str = "music") -> str:
    """Tags -> descritor textual único: input do text-embedding E base do prompt A.
    Ordem FIXA de campos (estabilidade do embedding entre re-ingestões); vazio omitido."""
    t = valida_tags(tags, tipo)
    if tipo == "sfx":
        partes = [t["ambiencia"], ", ".join(t["eventos"]), t["assinatura"]]
    elif tipo == "vo":
        partes = [t["genero"], t["idade"], t["tom"], t["timbre"], t["pace"], t["sotaque"],
                  f"energy {t['energia']}/5"]
    else:
        partes = [t["era"], t["registro"],
                  t["ironia"] if t["ironia"] != "sincero" else "",
                  t["cultura"], t["funcao"],
                  ", ".join(t["instrumentacao"]),
                  t["mode"] if t["mode"] != "ambiguous" else "",
                  f"{t['bpm']} BPM" if t["bpm"] else ""]
    return ", ".join(p for p in partes if p)
