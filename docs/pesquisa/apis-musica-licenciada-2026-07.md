---
tipo: pesquisa
data: 2026-07-08
url: multi-fonte (ver tabelas) — 2 agentes WebSearch + docs oficiais Epidemic (2026-07-08)
---

# APIs de música licenciada + busca por referência — Muntu Score, jul/2026

Pesquisa pra decidir **arquitetura A (geração IA + camadas) vs B (biblioteca licenciada)**
na trilha do [[caminhos/ia-aplicada|Muntu Score]]. Contexto: o gargalo de qualidade da
trilha é o **modelo de geração** (ElevenLabs redistribui estilos entre seções, ignora
eventos pontuais, estocástico) — ver handoff `muntu-score/docs/handoff-2026-07-07-refs-camadas-pin.md`.
2 agentes WebSearch (APIs de biblioteca + busca por referência). Irmã de
[[climas-trilha-filme-comercial-br-2026-07]], [[geradores-musica-ia-2026-06]].

## Veredito de uma linha

**Existe API self-serve de biblioteca licenciada com busca-por-vídeo: Epidemic Sound
Partner API** (Soundmatch = vídeo→faixa, licença de ads, PT-BR). B automatizado é
alcançável JÁ — não é fluxo manual. Mas broadcast TV e ads B2B (agência p/ cliente)
precisam de tier/contrato maior. Busca por referência via API só de prateleira no
Epidemic; fora dele = Cyanite/AIMS (catálogo próprio) ou DIY (CLAP embeddings).

## 1. APIs de production music library (uso comercial/ads)

| Biblioteca                                        | API?                                                | Busca via API (mood/BPM)                                                                                                     | Licença ads?                                                                                  | Preço                                                          | Fit                      |
| ------------------------------------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | ------------------------ |
| **Epidemic Sound**                                | **SIM** — Partner API (ES Connect), a mais madura   | SIM: semantic search, mood/genre/tempo/energy, **Soundmatch (vídeo→música)**, similar-track, search-by-reference, stems beta | SIM (tier pago via ES Connect = commercial license, cobre ads); free tier = pessoal (sem ads) | **Free tier self-serve** (API key na hora) + pago via contrato | ★ melhor                 |
| **Soundstripe**                                   | SIM — docs públicas                                 | SIM: BPM+mood no song object, stems via CDN; modelo = reindex noturno                                                        | SIM (Enterprise cobre broadcast + indenização US$1M)                                          | Enterprise/custom; creator US$10-34/mês                        | bom                      |
| **Artlist**                                       | SIM — Enterprise API (mira "generative media apps") | parcial (docs fechadas sob contrato)                                                                                         | SIM (Pro cobre client work + paid ads worldwide; Social não)                                  | Enterprise/custom, sem preço público                           | bom (contrato)           |
| **Pond5**                                         | SIM — reseller/partner                              | SIM declarado (2,6M faixas); doc sob aplicação                                                                               | SIM (royalty-free worldwide forever)                                                          | per-track + acordo reseller                                    | ok                       |
| **Envato/AudioJungle**                            | SIM — Market API                                    | search/item; sem mood/BPM estruturado garantido                                                                              | PARCIAL (Standard não cobre broadcast; ads TV = Broadcast License avulsa)                     | per-track + afiliados                                          | fraco                    |
| **Musicbed / APM / Universal PM / Audio Network** | NÃO público                                         | —                                                                                                                            | SIM no produto (manual/quote)                                                                 | quote/contrato                                                 | descartável p/ automação |
| **Uppbeat**                                       | NÃO                                                 | —                                                                                                                            | PARCIAL (Pro cobre ads digital; **exclui broadcast**)                                         | assinatura                                                     | fraco                    |

**Divisor de licença:** "ads" nas subscription libs = quase sempre **digital/social paid
media**. **Broadcast (TV/rádio)** exige enterprise (Soundstripe, Artlist Business) ou
licença avulsa (AudioJungle Broadcast, APM, UPM). Epidemic Pro exclui grandes anunciantes.

**Brasil:** Epidemic tem site+planos PT-BR (presença BR mais clara). Demais: licença
worldwide cobre BR, sem operação local dedicada.

## 2. Busca por REFERÊNCIA de áudio (similarity search) via API

| Serviço                              | O que faz                                                                                                                                                         | Via API?                                                                       | Catálogo                                                                 | Preço               |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------- |
| **Cyanite.ai**                       | análise (mood/BPM/key) + similarity search (sobe ref na Library → similares); `searchMode` por trecho `{start,end}`                                               | SIM (GraphQL)                                                                  | **próprio** (≥1000 faixas); integra Source Audio/Harvest/DISCO/Synchtank | ~€290/mês + análise |
| **AIMS API**                         | similarity **feita p/ production music**: ref por **link (YT/Spotify) OU arquivo** → similares                                                                    | SIM (dedicada, integra "em dias")                                              | próprio do cliente (Universal PM, Warner Chappell PM usam)               | quote               |
| **Epidemic (UI+API)**                | search-by-reference (link Spotify) + Soundmatch (vídeo)                                                                                                           | Partner API tem `get-similar-section-tracks` (por trackID, não upload externo) | catálogo Epidemic                                                        | ES Connect          |
| **APM / Artlist / Soundstripe (UI)** | busca por ref (cola link; APM aceita arrastar MP3)                                                                                                                | **só UI web, sem API self-serve**                                              | próprio                                                                  | assinatura          |
| **Musiio (SoundCloud)**              | tinha Search API                                                                                                                                                  | **morto** (redireciona p/ soundcloud.com)                                      | —                                                                        | —                   |
| **Musimap**                          | emotional metadata + similarity                                                                                                                                   | **morto** (Utopia faliu)                                                       | —                                                                        | —                   |
| **DIY — CLAP embeddings**            | embedding áudio↔texto → nearest-neighbor (FAISS/numpy); **bônus: busca por TEXTO no mesmo índice** ("80s romantic ballad, saxophone") = casa c/ pipeline VLM→mood | self-host                                                                      | qualquer (gargalo = LICENÇA de baixar catálogo, não técnica)             | GPU modesta/CPU     |

**Padrão:** bibliotecas grandes têm busca-por-ref **só na UI**; nenhuma expõe self-serve
via API (muitas usam AIMS/Cyanite white-label por baixo). Pra ter isso via API sobre
catálogo licenciado = contratar Cyanite/AIMS sobre catálogo que se pode ingerir, ou DIY.

## 3. Implicação pro Muntu (A vs B)

- **A arquitetura já corta música pronta** (`bed_file` + `bed_offset` no PIN aceita mp3;
  passa por corte/warp/diegético/stop/overlays). B **manual** funciona HOJE; B
  **automatizado** = Epidemic Soundmatch (self-serve) plugado no `bed_file`.
- **A** (gen IA + camadas): maximiza o produto-espetáculo (tool-isca 100% IA = wow que abre
  agência), qualidade "boa o bastante", eventos (marcha/sax) só garantidos com overlays.
- **B** (Epidemic): qualidade de faixa real, estocasticidade zero, licença explícita —
  ao custo de assinatura recorrente, pitch menor ("escolhe" < "cria"), dependência de
  catálogo, broadcast/B2B precisa contrato.
- **Recomendação: A agora** (demo/sonda/wow), **B via Epidemic quando houver cliente**
  (licença entra no job). Experimento barato que decide: API key free do Epidemic →
  Soundmatch no `real.mp4` → `bed_file` → A/B de ouvido.

## 4. Tiers Epidemic + integração CONSTRUÍDA (2026-07-08)

Docs oficiais fecharam a dúvida de acesso. **3 tiers** — o gargalo é a LICENÇA, não a key:

| Tier                 | Acesso                                       | Licença                                        | Cap                 | Testável hoje? |
| -------------------- | -------------------------------------------- | ---------------------------------------------- | ------------------- | -------------- |
| **Free / prototype** | key self-serve na hora (sem contrato/cartão) | ❌ prototyping-only (não pode vender o output) | ~50 downloads       | **SIM**        |
| **Startup**          | partnership (contato sales)                  | ✅ comercial (cobre ads)                       | maior               | contrato       |
| **Established**      | partnership                                  | ✅ comercial                                   | >1000 downloads/mês | contrato       |

Reconciliação: o **free tier self-serve é real** (a tabela §1 estava certa). O que a doc de
getting-started chama de "partnership agreement" é a **licença comercial** (startup+), não o
acesso à API. Free = build + teste hoje; vender pra agência (ads license) = partnership →
bate exato com A-agora/B-quando-cliente.

**Auth/endpoints — VERIFICADO AO VIVO (probe free tier, 2026-07-08):** base
`https://partner-content-api.epidemicsound.com`. API key bearer (`Authorization: Bearer
epidemic_live_...`) + header `x-partner-user-id`.

- **Busca por texto livre = `GET /v0/tracks/search?term=<texto>`** — o param é **`term`**
  (`query`/`q`/`keyword` são IGNORADOS, retornam default). Aceita frase livre e filtra.
- Filtro estruturado `GET /v0/tracks?mood=<id>&bpmMin=&bpmMax=` — `mood=` exige **id exato
  lowercase** do vocab `/v0/moods` (20 ids: happy, dreamy, epic, laid-back, romantic, sad,
  dark, relaxing…). "uplifting" e "Dreamy" retornam 0. Por isso a busca usa `term`, não `mood=`.
- Download `GET /v0/tracks/{id}/download?quality=normal` → `{url, expires}` (CDN temporária,
  24h/1h) → MP3 48kHz. Track = `{id, bpm, moods:[{id,name}], genres, length, title, …}`.
- Soundmatch by-video ainda não resolvido (stub; `term` cobre o caso free-text por ora).

**Integração no repo — VALIDADA END-TO-END ao vivo (gated, opt-in, 156 testes verdes):**

- `muntu/epidemic.py` — `busca(clima, register)` + `baixa_faixa(id)` (cache) + `popula_beds`.
  NÃO é geração: SELECIONA faixa real → seta `parte["bed_file"]` → reusa o encanamento PIN
  camada 2 (corte/diegético/stop/overlays). Estocasticidade zero.
- **CASAMENTO com o mapa de composição (os 3 eixos por clima, ancorado NA PESQUISA — não
  achismo):** a busca do Epidemic combina mood+genre+BPM com AND (confirmado em §1 da
  [[moods-broadcast-prompt-2026-07]]), então cada `clima` (mood.MOODS, 12) casa nos 3 eixos que
  a composição usa:
  - **mode → `mood=`** (`CLIMA_EPIDEMIC`): via quadrantes V/A de [[mapa-vlm-mood-clima-muntu-2026-07]].
    Ex.: melancholic→sad, tense→suspense, **energetic→running** (bucket cinético da pesquisa,
    corrigido de euphoric).
  - **arousal → `bpmMin/Max`** (`CLIMA_BPM`): bandas da tabela de convenção §2 de
    [[climas-trilha-filme-comercial-br-2026-07]] (melancholic 60-80, epic 110-140, tense 80-120…).
    Isto **ativa o eixo de BPM** que antes era inerte (o clima dá a banda; o reader não precisa emitir bpm).
  - **instrumentação → `genre=`** (`CLIMA_GENERO`, default por clima; `register` que nomeia
    gênero vence): epic→classical (brass/orquestral), melancholic→solo-piano (piano+cello),
    calm→ambient, energetic→rock. Vocab real: `/v0/genres` (20 top-level, `GENEROS_VALIDOS`).
    Escada degrada: mood+genre+bpm → mood+bpm → mood → term(register) → browse.
- **Prova ao vivo (7 climas):** melancholic→"A Long Night" (sad, solo-piano, bpm80); epic→
  "Mission to Eternity" (epic, classical, bpm130); romantic+"80s sax"→"Tokyo for an Evening"
  (romantic, **jazz** — register venceu); energetic+"surf rock"→(running, rock). Todos casam
  nos 3 eixos, n>0 (sem super-filtrar). `popula_beds` setou score, pulou diegético.
- `pipeline.run(..., banco=True)` + checkbox na UI Gradio. Sem `EPIDEMIC_API_KEY` → cai em A.
  Só popula partes **score**; respeita `bed_file` já setado (PIN manual).
- **A/B de ouvido (2026-07-08) + CALIBRAÇÃO:** veredito do usuário = A (gerada) > B no mood
  (esperado: geração cria pro brief; catálogo aproxima) → confirma A-agora/B-quando-cliente.
  Dois fixes aplicados: (a) **calibração de gênero** — `GENERO_EPIDEMIC` ganhou subgêneros
  granulares (ballad, arena-rock, soft-rock, indie-pop, surf-rock…) + split de hífen no `_genero`;
  o A/B tinha errado "80s power ballad" caindo em `acoustic` (top-level grosso) — agora alcança
  `genre=ballad` (verificado: "Feel like Family", romantic/ballad). (b) **`bed_offset` auto**
  (`_intro_skip`) — pula intro de baixa energia pra faixa entrar logo (fix "entra depois da cena");
  cap relativo à parte. `bed_file` segue sem warp (atmosfera). **156 testes verdes.**
- **REGRA universal de silêncio inicial (2026-07-08):** `trilha._corta_silencio_inicial` corta
  dead-air do início de QUALQUER bed (gerado/biblioteca/pinned) no `monta_trilha` — gen-IA e
  faixa de catálogo às vezes começam com silêncio/count-in (a balada pinned tinha 750ms de -inf →
  A e B entravam depois da cena). Cap 2s (preserva fade-in musical). Substituiu o `_intro_skip`
  do Epidemic (agressivo). Verificado: parte 2 entra no corte (6.8s) em A e B. **157 testes.**
- **Comédia perdida no reader:** filme cômico → reader emitiu clima `romantic` sincero → B saiu
  genérica. Fix de demo: override parte 2 = `comedic` (mood quirky + "cheesy sax") → "Knife Skills"
  (quirky/smooth-jazz/strange-weird). **Durável (a fazer):** `comico=true` → enviesar score cômico.
- **Falta:** re-ouvir B (brega-sax) vs A + **rotacionar a key** (colada em chat 2026-07-08 = queimada).

## Fontes (2026-07-07; §4 = 2026-07-08)

- Epidemic Partner API — https://developers.epidemicsite.com/docs/ · https://www.epidemicsound.com/business/developers/
- Soundstripe API — https://www.soundstripe.com/api · https://docs.soundstripe.com/
- Artlist Enterprise API — https://developer.artlist.io/welcome
- Pond5 API — https://www.pond5.com/api
- Envato API — https://api.envato.com · https://audiojungle.net/licenses/music
- Uppbeat licenças — https://uppbeat.io/commercial-licenses
- Cyanite similarity — https://api-docs.cyanite.ai/docs/similarity-search/ · https://cyanite.ai/faq/
- AIMS API — https://www.aimsapi.com/blog/ai-music-similarity-search-guide
- CLAP (DIY) — https://github.com/LAION-AI/CLAP (`laion/larger_clap_music`)
- Musiio morto (redirect) — https://musiio.com/ ; Musimap/Utopia falência — https://www.musicbusinessworldwide.com/swiss-court-launches-bankruptcy-proceedings-against-proper-group-formerly-utopia-music/

## Caveats

- Preços de AIMS, Bridge, Soundstripe Enterprise: não públicos (só contato).
- Filtros da Artlist API e doc da Pond5: fechados/parciais (403 no fetch).
- Enquadramento de ads B2B no Epidemic (agência trilha ad do cliente) precisa negociação
  contratual — Pro de varejo cobre ad online mas exclui grande anunciante.
- Ranking DIY (CLAP) vs Cyanite/AIMS não é benchmarkado publicamente.

## Log

- 2026-07-07 — Criada. 2 agentes WebSearch (APIs de biblioteca + similarity search).
  Achado-chave: Epidemic Partner API self-serve + Soundmatch (vídeo→faixa) = B automatizado
  alcançável. Busca-por-ref via API só Cyanite/AIMS (catálogo próprio) ou DIY CLAP. Decisão
  A-agora/B-quando-cliente registrada.
- 2026-07-08 — §4 add. Docs oficiais Epidemic confirmam 3 tiers (free self-serve prototype /
  startup / established); "partnership agreement" = licença comercial, não acesso à API.
  **Integração B construída no repo:** `muntu/epidemic.py` (busca/download/popula_beds via
  `bed_file`) + `pipeline.run(banco=True)` + checkbox UI, gated em `EPIDEMIC_API_KEY`, 149
  testes verdes. Falta: key free (mão do usuário) + verificar taxonomia mood/by-video ao vivo.
