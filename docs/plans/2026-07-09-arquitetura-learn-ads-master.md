# Arquitetura learn-from-ads — Plano-Mestre (2026-07-09)

> **Para workers agênticos:** este é o doc de COORDENAÇÃO. Cada executor (Sonnet/GLM em
> terminal próprio) recebe UM plano de workstream (`ws-a`/`ws-b`/`ws-c`) e lê este mestre
> antes. Escopos de arquivo são DISJUNTOS — não toque em arquivo fora do seu workstream.

**Goal:** implementar o sistema learn-from-ads do spec `docs/spec-arquitetura-learn-ads-2026-07-08.md`: tag-schema compartilhado → reader rico (wow, camada 1) + spike do tagueador (crux, camada 2) + banco Supabase com RAG híbrido (premium, camada 3). Camada 4 (SFX bank + VO) fica planejada como interface, execução deferida.

**Architecture:** um tag-schema genérico (`muntu/tags.py`) vira o vocabulário único que alimenta A (geração — tags → prompt ElevenLabs) e B (seleção — tags → query do banco). O reader passa a emitir tags ricas por parte (ironia/cultura/instrumentação) além do clima. O banco é Supabase Postgres + pgvector com 2 vetores por asset (text-embed do descritor + CLAP do áudio) fundidos por RRF em SQL puro.

**Tech Stack:** Python 3 + pydub (existente); Gemini 2.5 Pro via OpenRouter (reader/tagueador); ElevenLabs (geração A); Supabase (Postgres + pgvector, via CLI/MCP p/ migrations + `supabase-py` runtime); text-embedding via OpenRouter `/api/v1/embeddings` (mesma key); venv dedicado torch-CPU só pro CLAP `laion/larger_clap_music` (áudio).

## Global Constraints

- **Commits: SÓ pela mão do usuário, sem trailer** (memória `muntu-score-commits-sem-trailer`). Executor NUNCA commita — checkpoint = testes verdes + PARAR e avisar.
- **Sem `git stash` entre agentes** (memória `muntu-fable-planeja-sonnet-executa`). Escopo de arquivo disjunto é a garantia.
- **Supabase: só via Supabase CLI ou MCP postgres, nunca conexão postgres direta** (regra global do usuário).
- **NUNCA hardcode API keys**; tudo via env (`SUPABASE_URL`, `SUPABASE_KEY`, `MUNTU_MOOD_API_KEY`...).
- **Best-effort em toda integração externa** (padrão do repo: falha → fallback, nunca crash do pipeline).
- **Reader (LLM) SEMPRE escolhe; apply só executa** (memória `muntu-trilha-regras-criativas`). Output errado = calibra prompt do reader, não hardcode no apply.
- Testes: `pytest tests/` — 157 verdes hoje; nenhum pode quebrar.
- Código/comentários em PT-BR no estilo do repo (docstrings explicando o PORQUÊ).
- **Pré-requisito de segurança (usuário, fora dos workstreams): rotacionar keys queimadas** — `EPIDEMIC_API_KEY`, `DATABASE_URL`, ElevenLabs/Stability/Replicate/Anthropic (spec Parte 3).

---

## Decisões travadas (pesquisa 2026-07-09, com fontes)

| #   | Decisão                                                                                                                                                                                                                         | Base                                                                                                                                                                                                                                                                                                                                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | **Fusão dos 2 vetores = RRF em SQL puro**, k=60, variante ponderada `Σ w_i/(k+rank_i)`                                                                                                                                          | Rank-fusion evita normalizar distribuições incompatíveis (cosine de espaços distintos). Padrão: CTE por scorer com `ROW_NUMBER()`, `FULL OUTER JOIN`, `COALESCE(1/(60+rank),0)`. Fontes: tigerdata.com/blog (BM25+vector RRF), dev.to/lpossamai                                                                                                                                                       |
| D2  | **Sem índice ANN** (<10k rows: seq scan exato, recall 100%). Se crescer >10k: HNSW, nunca IVFFlat                                                                                                                               | rivestack.io/blog/pgvector-hnsw-vs-ivfflat; supabase.com/blog/increase-performance-pgvector-hnsw                                                                                                                                                                                                                                                                                                      |
| D3  | **CLAP = `laion/larger_clap_music`**, 512-dim, 48kHz, janelas ~10s + mean-pool L2-normalizado                                                                                                                                   | Model card HF (checkpoint music-only); dim confirmado no ClapConfig. Caveat: sem benchmark head-to-head vs `music_audioset` — se load-bearing, A/B no banco próprio                                                                                                                                                                                                                                   |
| D4  | **Text-embedding = OpenRouter `/api/v1/embeddings`** com `openai/text-embedding-3-small` (1536-dim) — mesma key `MUNTU_MOOD_API_KEY`, zero key nova, zero modelo local pro texto (ATUALIZADO 2026-07-09, resposta 1 do usuário) | milvus.io/blog/choose-embedding-model-rag-2026; OpenRouter serve embeddings desde 2026 (endpoint OpenAI-compat: openrouter.ai/docs/api/reference/embeddings). Em tags curtas o ganho de SOTA é marginal — qualidade do DESCRITOR pesa mais que o modelo. Fallback local se API incomodar: bge-m3 (1024-dim — exigiria migration com outra dimensão)                                                   |
| D5  | **Tabela `assets` única** com `asset_type`, filtros SQL (era, license_ok, bpm) e 2 colunas vetoriais (`text_emb vector(1536)`, `audio_emb vector(512)`)                                                                         | Pré-filtro SQL barato antes do blend; padrão multi-tipo                                                                                                                                                                                                                                                                                                                                               |
| D6  | **Tag-schema ancorado em Artlist dictionaries + AudioSet Music-mood**; eixos autorais (ironia, função narrativa, cultura) por cima — nenhuma taxonomia pública os cobre (é o moat)                                              | developer.artlist.io/dictionaries; research.google.com/audioset/ontology                                                                                                                                                                                                                                                                                                                              |
| D7  | **VO = 6 eixos primários do ElevenLabs Voice Design** (gênero, idade, sotaque, timbre, pace, pitch) + tom/energia como registro                                                                                                 | elevenlabs.io/docs voice-design                                                                                                                                                                                                                                                                                                                                                                       |
| D8  | **Epidemic = ponteiro, só text_emb** (`audio_emb` null); own+Artlist têm os 2 vetores                                                                                                                                           | Spec §2.5                                                                                                                                                                                                                                                                                                                                                                                             |
| D9  | **Bridge A→B:** draft gerado (A) vira query de áudio do CLAP → acha faixa real no banco                                                                                                                                         | Spec §2.6                                                                                                                                                                                                                                                                                                                                                                                             |
| D10 | **Mass-embed do banco SÓ depois do veredito do spike** (WS-B). Infra do WS-C pode nascer antes; ingestão em massa não                                                                                                           | Spec §2.7 (crux: qualidade do sistema = qualidade do tagueamento)                                                                                                                                                                                                                                                                                                                                     |
| D11 | **GraphRAG avaliado e DESCARTADO** (pergunta do usuário 2026-07-09). Fica pgvector híbrido                                                                                                                                      | GraphRAG serve corpus grande + query multi-hop/global; aqui é banco pequeno de schema fixo com query single-hop (vizinho + filtro SQL — relações era/cultura já são colunas). Eixo mais valioso é o SOM (CLAP), que grafo não representa. E o crux não muda: grafo sobre tag errada = mesmo lixo, com arestas. Convenções aprendidas ("comédia 80s BR→brega→sax") vivem no reader/packs, não em grafo |

---

## Tag-schema v1 CANÔNICO (conteúdo integral de `muntu/tags.py`)

O WS-A Task 1 cria este arquivo VERBATIM. WS-B e WS-C importam dele (nunca redefinem).

```python
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
```

---

## Workstreams — escopo de arquivos (DISJUNTO, é a lei)

| WS                                                       | Executor sugerido | Cria                                                                                                                                                                 | Modifica                                                                                                                 | Testes                                                                   |
| -------------------------------------------------------- | ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| **A — reader rico + tag-schema** (camada 1, wow)         | Sonnet terminal 1 | `muntu/tags.py`, `tests/test_tags.py`                                                                                                                                | `muntu/reader.py` (PROMPT + `_normaliza`), `muntu/trilha.py` (`_prompt_da_parte`), `muntu/epidemic.py` (ironia na busca) | `tests/test_reader.py`, `tests/test_trilha.py`, `tests/test_epidemic.py` |
| **B — spike do tagueador** (camada 2, crux)              | GLM terminal 2    | `muntu/tagueador.py`, `tests/test_tagueador.py`, `scripts/spike_tagueador.py`                                                                                        | —                                                                                                                        | novos apenas                                                             |
| **C — banco Supabase + RAG híbrido** (camada 3, premium) | Sonnet terminal 3 | `muntu/banco.py`, `tests/test_banco.py`, `supabase/migrations/*_assets.sql`, `scripts/embeddings/{embed_texto.py,embed_audio.py,README}`, `scripts/ingere_assets.py` | `requirements.txt` (+`supabase`)                                                                                         | novos apenas                                                             |

**Ordem de disparo:**

1. Usuário confirma plano → executor A roda **Task 1 do WS-A** (cria `muntu/tags.py` verbatim) → testes verdes → **usuário commita**.
2. Com `tags.py` no `main`: **A (resto), B e C partem em PARALELO** (3 terminais). B e C importam `muntu.tags`; nenhum toca arquivo do outro.
3. Review forte no fim de cada WS (Fable ou `code-reviewer` agent) antes do commit do usuário.
4. **Gate do crux:** ingestão em massa do WS-C (ingere_assets em cima do acervo real) SÓ roda depois do veredito do usuário no spike do WS-B (D10).

**Interfaces entre workstreams (contratos):**

- `tags.valida_tags(dict, tipo) -> dict` e `tags.descritor(dict, tipo) -> str` — usados por A (prompt), B (normalizar saída do VLM) e C (descritor pro embedding).
- Partes da timeline ganham campos novos opcionais: `ironia: str`, `cultura: str`, `instrumentacao: list[str]` (WS-A). Ausência = comportamento atual (retrocompat: timelines PINadas antigas seguem válidas).
- WS-C entrega `banco.popula_beds(timeline, cache_dir) -> None` com o MESMO contrato de `epidemic.popula_beds` (muta partes setando `bed_file`) — plugin futuro no pipeline sem mexer em `trilha.py`.
- WS-B entrega `tagueador.tagueia_ad(video_path) -> dict` com chaves `musica` (lista por parte), `sfx`, `vo` — todas já passadas por `valida_tags`.

---

## Camada 4 (SFX bank + VO) — só interface, execução deferida

- `monta_sfx(timeline, ...)` irmão do `monta_trilha`: consome `banco.busca_hibrida(tipo="sfx")` (CLAP brilha em evento curto — home turf AudioSet). Aditiva sobre o `sfx_map` atual.
- VO: ElevenLabs TTS com voz escolhida via `TAGS_VO` + ducking da trilha ("sits under voiceover" é invariante da pesquisa moods-broadcast §4). **Bloqueada em input do usuário (roteiro).**
- Nada disso entra agora; o schema (`TAGS_SFX`, `TAGS_VO`) já nasce no WS-A pra o spike do WS-B testar a leitura de VO (o traço mais difícil — validar cedo).

## Respostas do usuário (2026-07-09) — plano DESTRAVADO

1. **Text-embedding:** via OpenRouter `/api/v1/embeddings` (`openai/text-embedding-3-small`, 1536-dim) com a key `MUNTU_MOOD_API_KEY` já existente — OpenRouter serve embeddings em 2026 (verificado: openrouter.ai/docs/api/reference/embeddings). D4/D5 atualizadas; bge-m3 vira fallback.
2. **Supabase:** projeto NOVO dedicado; usuário apaga o projeto existente (de quebra, mata o `DATABASE_URL` vazado na sessão GLM).
3. **Corpus do spike:** canal YouTube do usuário — `https://www.youtube.com/@muntu_co` — via yt-dlp; MUITO mais que 3-4 ads. Spike julga amostra de 6-10; aprovado → tagueia o resto do corpus (insumo da ingestão WS-C).
4. **GLM no WS-B:** confirmado ("seguro assim?" → sim: só arquivos novos, schema travado verbatim no mestre, review forte antes do commit, agente nunca commita; pior caso = descartar arquivos novos).
5. **Rotação de keys:** ADIADA pelo usuário (decisão consciente, fora dos planos). Risco registrado: ElevenLabs/Epidemic/Replicate/Anthropic queimadas seguem válidas até rotacionar. A troca do projeto Supabase (item 2) já cobre o `DATABASE_URL`.
