"""Provedor B: biblioteca licenciada Epidemic Sound (Partner Content API).

NAO e geracao (musica.py = prompt->audio, estocastico). E SELECAO de faixa REAL do catalogo
licenciado, entregue como mp3 pro mecanismo `bed_file` (PIN camada 2, ver trilha.py). Fecha o
loop B-automatizado: reader da o mood da parte -> busca no catalogo -> download mp3 ->
parte["bed_file"] -> MESMO encanamento (corte/warp/diegetico/stop/overlays). Estocasticidade
ZERO (faixa real, nao gerada) + licenca explicita.

Decisao A-agora/B-quando-cliente ([[apis-musica-licenciada-2026-07]]): esta camada e OPT-IN.
Sem key, o pipeline segue em A (geracao). Free tier (prototype, self-serve) basta pra dev/demo;
licenca comercial/ads = partnership (entra com o cliente).

Gated em EPIDEMIC_API_KEY + httpx. Cache por trackId+qualidade (nao re-baixa). Best-effort:
key ausente, erro de rede/HTTP, ou zero match -> retorna None/[] e a parte cai em A.

Docs: https://developers.epidemicsite.com/docs/
Auth: API key bearer (`Authorization: Bearer epidemic_live_...`) + header `x-partner-user-id`.
VERIFICADO AO VIVO 2026-07-08 (probe free tier): auth bearer OK; texto livre = /v0/tracks/
search?term= (query/q/keyword sao IGNORADOS); `mood=` exige id exato lowercase do vocab
(/v0/moods, 20 ids em MOODS_VALIDOS); download devolve {url, expires}; response = {tracks:[...]}.
PENDENTE: Soundmatch by-video (deixado como stub; term search cobre o caso free-text por ora).
"""
from __future__ import annotations

import hashlib
import os

BASE_URL = "https://partner-content-api.epidemicsound.com"
CACHE_DIR = "outputs/cache/epidemic"
PARTNER_USER_ID = "muntu-score"     # id de analytics (nao e credencial)
QUALIDADE = "normal"                 # normal=128kbps (basta p/ bed sob mix) | high=320kbps
TIMEOUT = 60.0


def _tem_lib(nome: str) -> bool:
    try:
        __import__(nome)
        return True
    except ImportError:
        return False


def epidemic_disponivel() -> bool:
    """True se ha key + httpx. Gate identico ao dos demais provedores pagos."""
    return bool(os.environ.get("EPIDEMIC_API_KEY")) and _tem_lib("httpx")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ['EPIDEMIC_API_KEY']}",
        "x-partner-user-id": PARTNER_USER_ID,
    }


# Vocabulario REAL de moods do Epidemic (GET /v0/moods, probe ao vivo 2026-07-08). 20 ids.
# NAO usado como filtro direto: a busca vai por /v0/tracks/search?term=<free-text>, que aceita
# QUALQUER texto (o `mood=` de /v0/tracks exige id EXATO lowercase — "dreamy" filtra, "uplifting"
# e "Dreamy" retornam 0). Fica de referencia/documentacao + p/ eventual filtro mood= preciso.
MOODS_VALIDOS = (
    "happy", "dreamy", "epic", "laid-back", "euphoric", "quirky", "suspense", "running",
    "relaxing", "mysterious", "sentimental", "sad", "peaceful", "countryside", "romantic",
    "hopeful", "chasing", "dark", "sneaking", "sunny-holiday",
)
# Generos top-level do Epidemic (GET /v0/genres, probe 2026-07-08). 20 ids. Subgeneros
# (surf-rock, bossa-nova, 1980s…) existem via /v0/genres/{id}/children e filtram por slug, mas
# aqui usamos top-level (o `term=` pega o granular). Referencia + validacao dos mapas de genero.
GENEROS_VALIDOS = (
    "pop", "jazz", "electronic", "hip-hop", "funk", "country", "rock", "classical", "rb",
    "soul", "disco", "acoustic", "drama", "solo-piano", "easy-listening", "small-ensemble",
    "waltz", "ambient", "drone", "african-continent",
)
# CASAMENTO DE NOMENCLATURA: biblioteca de climas do muntu (mood.MOODS, 12, que o reader usa)
# -> mood id do Epidemic (MOODS_VALIDOS). Ancorado NA PESQUISA (nao achismo): os quadrantes V/A
# de [[mapa-vlm-mood-clima-muntu-2026-07]] + o vocab comercial de [[moods-broadcast-prompt-2026-07]]
# §1 (estados emocionais / tensao / CINETICA = Running/Chasing). `clima` = vocab controlado ->
# filtro `mood=` PRECISO (casamento firme); registro free-text -> `term=` de refino.
#   energetic -> running: pesquisa poe energetic no bucket CINETICO (HA, valence-neutro), nao no
#   emocional (euphoric = HV·HA). tender/nostalgic -> sentimental (HV·LA bittersweet); tense ->
#   suspense (bucket tensao); melancholic -> sad (LV·LA); calm -> peaceful (HV·LA serene).
CLIMA_EPIDEMIC = {
    "romantic": "romantic", "tender": "sentimental", "nostalgic": "sentimental",
    "melancholic": "sad", "joyful": "happy", "playful": "quirky", "comedic": "quirky",
    "energetic": "running", "tense": "suspense", "calm": "peaceful", "epic": "epic",
    "neutral": "laid-back",
}
# CASAMENTO DE GENERO: o reader nao emite genero estruturado (o estilo vem no `mood`/registro
# free-text: "surf rock", "80s sax", "orchestral"). Extraimos a keyword de genero do registro
# -> genre id do Epidemic (GET /v0/genres, 20 ids; probe 2026-07-08: `genre=` filtra e COMBINA
# com `mood=`). Palavra -> id; 1a palavra que casa vence. So generos/instrumentos (nao moods).
#   O valor pode ser SUBGENERO granular (slug) — o filtro `genre=` os aceita (probe 2026-07-08:
#   ballad, arena-rock, soft-rock, pop-rock, surf-rock, smooth-jazz filtram). Granular > top-level
#   quando o register nomeia o estilo (ex. "power ballad" -> ballad, "80s arena" -> arena-rock;
#   calibrado contra o A/B que errou "80s power ballad" caindo em acoustic).
GENERO_EPIDEMIC = {
    "rock": "rock", "surf": "surf-rock", "punk": "punk-rock", "grunge": "grunge",
    "arena": "arena-rock", "hard-rock": "hard-rock",
    "ballad": "ballad", "powerballad": "ballad",       # "power ballad" -> match em "ballad"
    "soft": "soft-rock", "poprock": "pop-rock",
    "jazz": "jazz", "jazzy": "jazz", "sax": "smooth-jazz", "saxophone": "smooth-jazz",
    "swing": "swing", "bebop": "jazz",
    "electronic": "electronic", "synth": "electronic", "synthwave": "synthwave",
    "electro": "electronic", "edm": "electronic", "techno": "techno", "house": "electronic",
    "hip-hop": "hip-hop", "hiphop": "hip-hop", "rap": "hip-hop", "trap": "trap",
    "funk": "funk", "funky": "funk",
    "country": "country", "bluegrass": "country", "western": "country",
    "classical": "classical", "orchestral": "orchestral", "orchestra": "orchestral",
    "strings": "classical", "symphony": "classical", "symphonic": "classical",
    "soul": "soul", "motown": "motown", "gospel": "gospel",
    "disco": "disco", "boogie": "disco",
    "acoustic": "acoustic", "guitar": "acoustic", "folk": "folk",
    "piano": "solo-piano",
    "ambient": "ambient", "atmospheric": "ambient", "drone": "drone", "pad": "ambient",
    "waltz": "waltz",
    "lounge": "lounge", "easy-listening": "easy-listening",
    "chamber": "small-ensemble", "ensemble": "small-ensemble", "quartet": "small-ensemble",
    "african": "african-continent", "afrobeat": "african-continent",
    "bossa": "bossa-nova", "samba": "samba", "forro": "forro", "reggae": "reggae",
    "blues": "blues", "metal": "metal",
    "pop": "pop", "synthpop": "synth-pop", "indie-pop": "indie-pop", "indie-rock": "indie-rock",
    "rnb": "rb", "r&b": "rb",
    "cinematic": "drama", "dramatic": "drama", "trailer": "drama",
}
# CASAMENTO COM O MAPA DE COMPOSICAO: a pesquisa define POR CLIMA os 3 eixos que a composicao
# usa (mode->mood ja em CLIMA_EPIDEMIC; arousal->BPM; instrumentacao->genre). Aqui os outros 2,
# ancorados na tabela de convencao (secao 2 de [[climas-trilha-filme-comercial-br-2026-07]]) +
# [[mapa-vlm-mood-clima-muntu-2026-07]]. Assim a selecao de faixa B casa com o mesmo mapa que
# rege a geracao A (packs). Best-effort: clima sem entrada -> eixo omitido (a escada degrada).
#
# BPM band (arousal) por clima — da tabela de convencao + BPMs dos packs (mapa-vlm):
CLIMA_BPM = {
    "romantic": (75, 100), "tender": (70, 90), "nostalgic": (80, 110),
    "melancholic": (60, 80), "joyful": (100, 125), "playful": (110, 140),
    "comedic": (110, 140), "energetic": (120, 140), "tense": (80, 120),
    "calm": (60, 90), "epic": (110, 140), "neutral": (76, 120),
}
# genre DEFAULT (instrumentacao) por clima — da coluna Instrumentacao da tabela de convencao.
# So default: se o `register` do reader nomeia um genero, ELE vence (mais especifico).
CLIMA_GENERO = {
    "romantic": "acoustic", "tender": "acoustic", "nostalgic": "soul",
    "melancholic": "solo-piano", "joyful": "acoustic", "energetic": "rock",
    "tense": "drama", "calm": "ambient", "epic": "classical", "neutral": "ambient",
    # playful/comedic sem default (quirky nao e genero; register/term carrega o sabor)
}
# reader emite mood em PT-BR/EN livre; o catalogo e tagueado em EN -> traduz palavras comuns
# pra elevar o hit-rate do term search. Best-effort: sem match, manda a palavra original.
_PT_EN = {
    "comico": "quirky", "comedia": "quirky", "romantico": "romantic", "triste": "sad",
    "melancolico": "sad", "sombrio": "dark", "tenso": "suspense", "epico": "epic",
    "alegre": "happy", "feliz": "happy", "esperancoso": "hopeful", "relaxante": "relaxing",
    "misterioso": "mysterious", "festa": "party", "corporativo": "corporate",
    "sonhador": "dreamy", "calmo": "peaceful", "dancante": "dance", "energetico": "energetic",
}


def _term(mood: str | None) -> str | None:
    """Free-text do reader -> termo de busca EN (traduz palavras PT comuns). None se vazio.
    O term search e substring sobre metadata; texto livre funciona (nao precisa id exato)."""
    if not mood:
        return None
    m = mood.strip().lower()
    if not m:
        return None
    palavras = [_PT_EN.get(w, w) for w in m.replace(",", " ").split()]
    return " ".join(p for p in palavras if p) or None


def _genero(register: str | None) -> str | None:
    """Extrai a keyword de genero do registro free-text -> genre id (top-level OU subgenero slug)
    do Epidemic. 1a palavra que casa vence. Testa o token inteiro (casa 'hip-hop','indie-pop')
    e depois as partes do hifen ('indie-pop'->'pop'). None se nenhuma. Best-effort."""
    if not register:
        return None
    for w in register.strip().lower().replace(",", " ").replace("/", " ").split():
        if w in GENERO_EPIDEMIC:
            return GENERO_EPIDEMIC[w]
        for parte in w.split("-"):                       # 'indie-pop' -> 'pop'; 'hip-hop' ja casou acima
            if parte in GENERO_EPIDEMIC:
                return GENERO_EPIDEMIC[parte]
    return None


def _get_tracks(path: str, params: dict) -> list[dict]:
    """1 GET a `path` (/v0/tracks browse ou /v0/tracks/search). Levanta em erro HTTP (o caller
    trata a escada). Response = {tracks: [...], pagination, links, aggregations}."""
    import httpx

    r = httpx.get(f"{BASE_URL}{path}", headers=_headers(), params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json().get("tracks", []) or []


def busca(clima: str | None = None, register: str | None = None, bpm_min: int | None = None,
          bpm_max: int | None = None, limit: int = 5) -> list[dict]:
    """Faixas do catalogo casadas com o MAPA DE COMPOSICAO (os 3 eixos por clima):
      - `clima` (vocab controlado do reader) -> mood id (CLIMA_EPIDEMIC, valence/mode) +
        banda de BPM (CLIMA_BPM, arousal) + genero default (CLIMA_GENERO, instrumentacao);
      - `register` (free-text) -> genero especifico se nomear um (vence o default) + `term=`.
    A busca do Epidemic combina mood+genre+BPM com AND (confirmado na pesquisa moods-broadcast).
    Retorna [{id, bpm, moods, ...}]. [] so em ultimo caso.

    ESCADA (mais preciso -> degrada; probe ao vivo 2026-07-08 fixou os endpoints):
      1. mood + genre + BPM  (casamento full dos 3 eixos);
      2. mood + BPM          (larga o genero);
      3. mood                (larga o BPM);
      4. term=<register>     (fuzzy, /v0/tracks/search — param e `term`);
      5. browse / sem filtro (qualquer faixa > cair em A).
    Best-effort: erro de rede -> []; erro HTTP -> proxima tentativa (degrada, nao quebra)."""
    if not epidemic_disponivel():
        return []
    import httpx
    import sys

    c = (clima or "").strip().lower()
    mood_id = CLIMA_EPIDEMIC.get(c)
    genre_id = _genero(register) or CLIMA_GENERO.get(c)      # register nomeia -> vence o default
    if bpm_min is None and bpm_max is None and c in CLIMA_BPM:
        bpm_min, bpm_max = CLIMA_BPM[c]                      # banda de BPM do clima (pesquisa)
    bpm: dict = {}
    if bpm_min is not None:
        bpm["bpmMin"] = bpm_min
    if bpm_max is not None:
        bpm["bpmMax"] = bpm_max

    tentativas: list[tuple[str, dict]] = []
    if mood_id:
        base = {"mood": mood_id, "limit": limit}
        if genre_id:
            tentativas.append(("/v0/tracks", {**base, **bpm, "genre": genre_id}))  # 1. 3 eixos
        tentativas.append(("/v0/tracks", {**base, **bpm}))                         # 2. mood+BPM
        tentativas.append(("/v0/tracks", base))                                    # 3. so mood
    term = _term(register)
    if term:
        tentativas.append(("/v0/tracks/search", {"term": term, "limit": limit}))   # 4. fuzzy
    tentativas.append(("/v0/tracks", {**bpm, "limit": limit}))                      # 5. browse/BPM
    if bpm:
        tentativas.append(("/v0/tracks", {"limit": limit}))                        # 5b. sem filtro

    for i, (path, params) in enumerate(tentativas):
        try:
            tracks = _get_tracks(path, params)
            if tracks:
                if i > 0:
                    print(f"[muntu] epidemic: fallback nivel {i} (clima '{clima}'/'{register}')",
                          file=sys.stderr)
                return tracks
        except httpx.HTTPStatusError as e:
            print(f"[muntu] epidemic busca HTTP {e.response.status_code} em {path}; "
                  f"tentando proximo", file=sys.stderr)
            continue                                  # 4xx/5xx numa tentativa -> degrada p/ proxima
        except Exception as e:                        # noqa: BLE001 — rede/parse
            print(f"[muntu] epidemic busca indisponivel ({type(e).__name__}: {e})", file=sys.stderr)
            return []
    return []


def _url_download(track_id: str, qualidade: str = QUALIDADE) -> str | None:
    """Resolve a URL de download (temporaria) da faixa (GET /v0/tracks/{id}/download).
    A API devolve uma URL de CDN com expiracao (24h normal / 1h high). None se falhar."""
    import httpx

    r = httpx.get(f"{BASE_URL}/v0/tracks/{track_id}/download",
                  headers=_headers(), params={"quality": qualidade}, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    # response = {url, expires} (probe 2026-07-08). Fallbacks p/ robustez se a doc mudar.
    return data.get("url") or data.get("downloadUrl") or data.get("location")


def baixa_faixa(track_id: str, cache_dir: str = CACHE_DIR,
                qualidade: str = QUALIDADE) -> str | None:
    """Baixa a faixa -> arquivo mp3 local (cache por track+qualidade). Retorna o path, ou
    None se indisponivel/erro. O caller usa esse path como parte["bed_file"]."""
    if not epidemic_disponivel():
        return None
    import httpx

    os.makedirs(cache_dir, exist_ok=True)
    h = hashlib.sha1(f"{track_id}|{qualidade}".encode()).hexdigest()[:16]
    destino = os.path.join(cache_dir, f"{h}.mp3")
    if os.path.exists(destino):
        return destino
    try:
        url = _url_download(track_id, qualidade)
        if not url:
            return None
        with httpx.stream("GET", url, timeout=TIMEOUT) as resp:
            resp.raise_for_status()
            with open(destino, "wb") as f:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
        return destino
    except Exception as e:                          # noqa: BLE001 — best-effort
        import sys
        if os.path.exists(destino):
            os.remove(destino)                      # nao deixa mp3 truncado no cache
        print(f"[muntu] epidemic download falhou ({type(e).__name__}: {e})", file=sys.stderr)
        return None


def bed_para_clima(clima: str | None, register: str | None = None, bpm: int | None = None,
                   cache_dir: str = CACHE_DIR) -> str | None:
    """Conveniencia: clima (vocab) + register (free-text) + BPM -> path mp3 da MELHOR faixa.
    None se sem match. BPM vira janela +-8 (folga; a faixa e atmosfera, sem lock ao corte)."""
    faixas = busca(clima, register, bpm_min=(bpm - 8) if bpm else None,
                   bpm_max=(bpm + 8) if bpm else None, limit=1)
    if not faixas:
        return None
    tid = faixas[0].get("id")
    return baixa_faixa(tid, cache_dir) if tid else None


def popula_beds(timeline: dict, cache_dir: str = CACHE_DIR,
                so_score: bool = True) -> dict:
    """Seta `bed_file` nas partes da timeline usando o mood que o reader ja emitiu — a fonte
    do bed passa de A (geracao) pra B (faixa licenciada). MUTA a timeline in-place e a retorna
    (o pipeline com PIN pode salvar esse JSON = B travado, reproduzivel).

    Best-effort POR PARTE: sem match/erro -> parte fica sem bed_file -> cai em A. `so_score`
    pula partes diegeticas (som do mundo; faixa de catalogo nao e ambiencia). Nao sobrescreve
    bed_file ja setado (respeita PIN manual)."""
    if not epidemic_disponivel():
        return timeline
    for parte in timeline.get("partes", []):
        if parte.get("bed_file"):
            continue
        if so_score and parte.get("tipo") == "diegetic":
            continue
        # clima = casamento preciso (mood= id); mood = registro free-text (term= refino)
        path = bed_para_clima(parte.get("clima"), parte.get("mood"),
                              parte.get("bpm"), cache_dir)
        if path:
            parte["bed_file"] = path
            # silencio inicial: cortado como REGRA universal no monta_trilha (trilha._corta_
            # silencio_inicial), pra qualquer bed. `bed_offset` fica so manual (pular pro refrao).
    return timeline
