# Spec de Arquitetura + Handoff — Muntu Score, 2026-07-08

Doc-mestre da sessão de 2026-07-08. **Ler primeiro na próxima sessão.** Duas metades:
(1) estado tático (o que foi construído/auditado) + (2) a arquitetura completa que desenhamos
(sistema learn-from-ads, RAG semântico + aproximação, música + SFX + VO).

Contexto: repo `~/Documentos/muntu-score` (Claude pair, **nada commitado** — convenção
[[muntu-score-commits-sem-trailer]], mão do usuário, sem trailer). **157 testes verdes.**

---

## PARTE 1 — ESTADO TÁTICO (feito nesta sessão)

### 1.1 Auditoria da sessão GLM anterior (2026-07-07/08)

- **SFX map encolhido** (`sfx_map.py` MAX_TOKENS 64k→8k, prompt tags-curtas) — ✅ correto, testado.
- **Marcha nupcial (citação MIDI)** — código pronto (`tons.py` + `_overlay_citacoes`), mas
  **asset nunca nasceu** (fluidsynth/soundfont nunca instalados; sem `.mid`/`.sf2`/`marcha.mp3`).
  `_overlay_citacoes` é no-op hoje. **PARQUEADO** por decisão do usuário.

### 1.2 Integração Epidemic (provedor B) — CONSTRUÍDA + CALIBRADA + VALIDADA AO VIVO

- `muntu/epidemic.py` (novo): SELECIONA faixa real do catálogo → seta `parte["bed_file"]` →
  reusa o encanamento PIN camada 2. NÃO é geração. Gated em `EPIDEMIC_API_KEY`, best-effort.
- **Casamento com o mapa de composição (3 eixos por clima, ancorado NA PESQUISA):**
  - `CLIMA_EPIDEMIC` (mode→`mood=`, quadrantes V/A do [[mapa-vlm-mood-clima-muntu-2026-07]]);
    correção via pesquisa: **energetic→running** (cinético), não euphoric.
  - `CLIMA_BPM` (arousal→`bpmMin/Max`, tabela de convenção §2 de
    [[climas-trilha-filme-comercial-br-2026-07]]) — ativou o eixo de BPM que era inerte.
  - `CLIMA_GENERO` (instrumentação→`genre=`, default; register que nomeia gênero vence).
- **Endpoints VERIFICADOS AO VIVO (probe free tier 2026-07-08):** base
  `partner-content-api.epidemicsound.com`; auth bearer + `x-partner-user-id`; texto livre =
  `/v0/tracks/search?**term**=` (`query`/`q` ignorados); `mood=`/`genre=` exigem **id exato**
  (`/v0/moods` 20 ids, `/v0/genres` 20 top-level + subgêneros via `/v0/genres/{id}/children`);
  **mood+genre+BPM combinam com AND**; download `/v0/tracks/{id}/download?quality=` → `{url,expires}`.
- **Calibração (A/B de ouvido):** `GENERO_EPIDEMIC` ganhou subgêneros granulares (ballad,
  arena-rock, soft-rock, indie-pop, surf-rock…) + split de hífen; o A/B tinha errado "80s power
  ballad" caindo em `acoustic` — agora acha `genre=ballad`.
- `pipeline.run(..., banco=True)` + checkbox UI. Sem key → cai em A.

### 1.3 Regra universal de silêncio (fix "trilha entra depois da cena")

- `trilha._corta_silencio_inicial` no `monta_trilha` corta dead-air do início de QUALQUER bed
  (gerado/biblioteca/pinned). A balada pinned tinha 750ms de -inf → A e B entravam tarde. Cap 2s.
- Substituiu o `_intro_skip` do Epidemic (era agressivo — cortava intro musical, não só silêncio).

### 1.4 A/B de ouvido — VEREDITO

- **A (geração) > B (Epidemic) no mood.** Esperado: geração cria pro brief; catálogo aproxima.
  Confirma **A-agora / B-quando-cliente**.
- **B revelou o problema de fundo:** o filme é COMÉDIA, o reader emitiu clima `romantic` sincero
  → perdeu o humor (brega/kitsch sax). Fix de demo: override parte 2 = `comedic` → "Knife Skills"
  (quirky/smooth-jazz). **Fix durável (a fazer): `comico=true` → enviesar score cômico no reader.**
- Arquivos: `outputs/ab/A_pinned.mp4` + `B_epidemic.mp4` (+ .mp3).

### 1.5 Epidemic Soundmatch (video→track) — TESTADO PELO USUÁRIO = RUIM

- O modelo learned deles é genérico/fraco pra ad. **Descartado.** O pipeline muntu (reader
  narrativo + geração) já bate. Confirma que o **moat é a camada que raciocina o filme.**

---

## PARTE 2 — A ARQUITETURA (a visão fechada, a construir)

### 2.1 O problema de fundo (por que "mood não dá conta")

A pesquisa `climas-trilha` §1 já cravou: **"o adjetivo subdetermina"**. Um rótulo de mood (12
climas OU 20 do Epidemic) não fecha a partitura. Todo o pipeline passa por esse gargalo lossy:
vídeo → VLM cospe um RÓTULO → mapa heurístico → faixa. Cada seta perde info. Por isso a comédia
se perdeu. **Mais pesquisa de mood não resolve — é teto do método (label), não falta de cobertura.**

### 2.2 A solução: sistema learn-from-ads (3 modalidades) → schema genérico → alimenta A e B

Aprende de **comerciais reais** os descritores que o mood não segura. NÃO é treinar modelo — é
**LLM/VLM etiquetando** item a item (o "aprendizado" é a extração). Extrai de cada ad real:

- **cena → tags de música** (VLM lê vídeo): era, registro/ironia, cultura (brega/Balkan/bossa),
  função narrativa, instrumentação assinatura, + os 2 knobs da pesquisa (mode/valence, BPM/arousal).
- **áudio → tipos de SFX** (o foley/ambiência que o ad usa).
- **fala → tipos de VO** (análise de ÁUDIO, não vídeo): gênero/idade, tom (autoritário/caloroso/
  hype/luxo-sussurro/deadpan-cômico), pace, registro, sotaque, energia.

O **tag-schema é o vocabulário compartilhado** e serve DUAS pontas:

- **A (geração):** tags → prompt do ElevenLabs (register rico, não os 12 climas rasos).
- **B (seleção):** tags → query do banco.
  Um passo de tagueamento alimenta tudo.

### 2.3 As 4 camadas + sequência (wow-first, pra NÃO virar elefante)

1. **WOW-AGORA (crítico):** A-música acerta o mood via **tag-schema + reader rico**
   (comédia/registro/cultura-aware). **ZERO banco.** É o que abre agência. Ataca a raiz (o reader).
2. **Premium seleção:** banco Supabase (música) + RAG semântico/aproximação. Entra com curadoria/cliente.
3. **SFX curado:** `monta_sfx` (irmão do `monta_trilha`) puxa do banco de SFX do usuário. **CLAP
   brilha aqui** (SFX = eventos sonoros curtos = home turf do CLAP/AudioSet). Aditiva.
4. **VO:** ElevenLabs TTS + ducking ("sits under voiceover" já é invariante da pesquisa
   `moods-broadcast` §4). Camada final. Precisa do roteiro (usuário).

Cada camada é **aditiva, não bloqueio**. Mesmo schema + Supabase servem música e SFX.

### 2.4 O banco: Supabase (Postgres) + pgvector, 2 vetores

**Supabase desde o início** (o usuário já tem no stack; pgvector nativo; sem migração; sync
iMac↔MBP; query híbrida = SQL nativo). NÃO usar vector DB dedicado (overkill p/ banco curado).

- **Tabela genérica** `assets(id, asset_type music|sfx|vo, source own|artlist|epidemic, pointer,
facets [era,mood,genre,instrumentos,license_ok], descritor text, embedding vector, clap_vec vector)`.
- **2 vetores complementares:**
  - **RAG semântico** = text-embedding do descritor. Casa por INTENÇÃO. **Cobre tudo, incl.
    Epidemic-ponteiro** (que só tem texto/metadata, sem áudio).
  - **RAG por aproximação** = CLAP (audio-embedding). Casa por SOM. **Só own+Artlist** (precisa do
    áudio). De-risca o tagueador (se a tag erra, o som ainda acha).
- **Retrieval híbrido:** `where era=… and license_ok order by (blend dos 2 vetores)`. Fusão de 2
  vetores precisa de normalização/peso (RRF) — detalhe de impl, não bloqueio.

### 2.5 Como o Epidemic se encaixa (a pergunta recorrente)

- Epidemic = **ponteiro** (nome + estilo + metadata deles), **NÃO baixa** (free tier = 50 downloads;
  catálogo 55k inviável de embedar local). Licença entra na ENTREGA (partnership tier c/ cliente).
- Vai **só no RAG semântico** (text-embed do metadata + tag de curadoria). **Sem CLAP** (sem áudio).
- **Caveat:** ponteiro Epidemic depende 100% da qualidade da tag (sem rede de segurança do som).
  Own+Artlist têm as 2 redes.

### 2.6 O bridge A→B (o pulo do gato do "por aproximação")

Problema: pra um ad novo, de onde vem o som de referência da busca-por-aproximação? **Resposta:
a geração A cria um draft → esse draft É a query de áudio → CLAP acha a faixa REAL mais parecida
no banco.** A (que acerta o brief) GUIA o retrieval de B. Usa a força de cada um.

### 2.7 O CRUX (repetido porque é O risco)

A arquitetura (Supabase+pgvector) é a parte fácil e resolvida. **O gargalo é o TAGUEADOR** — o
VLM/áudio-model que lê registro/ironia/tom-de-voz. Se ele erra (como o reader errou a comédia), o
banco fica mal-etiquetado e o RAG retorna lixo bem-organizado. **Qualidade do sistema = qualidade
do tagueamento.** VO é o mais difícil (traço de voz é sutil). → **validar o tagueador ANTES de
construir banco.**

---

## PARTE 3 — SEGURANÇA + CONSTRAINTS

- **ROTACIONAR (urgente):** `EPIDEMIC_API_KEY` (colada em chat 2026-07-08) + `DATABASE_URL`
  (vazou no env dump da sessão GLM) + as keys ElevenLabs/Stability/Replicate/Anthropic (sessões
  passadas). Tudo queimado.
- Epidemic free tier: 50 downloads, prototyping-only (sem licença comercial). Comercial = partnership.
- Supabase: tocar via **Supabase CLI ou postgres MCP**, nunca postgres direto (regra do usuário).

---

## PARTE 4 — PRÓXIMA SESSÃO (ordem de execução)

1. **[wow-crítico] Reader rico + tag-schema.** Escrever o tag-schema genérico (dimensões da §2.2)
   - calibrar o reader pra ler registro/ironia/comédia (`comico=true` → enviesar cômico). Feed nas
     tags do prompt de geração A. **Zero banco.** É o que destrava o mood que "não dá conta".
2. **[validar o crux] Spike do tagueador.** VLM etiqueta 3-4 ads reais no schema → usuário julga de
   ouvido/olho se leu o registro fino. Se não ler, o resto não adianta.
3. **[premium, com o schema pronto] Banco Supabase.** `create extension vector` + tabela genérica
   (via CLI/MCP) + embedar o set inicial (own+Artlist) com text-embed E CLAP; Epidemic como ponteiro
   semântico. Rodar RAG semântico + aproximação no set pequeno.
4. SFX bank (`monta_sfx`) + VO (ElevenLabs TTS + ducking) — camadas 3 e 4, aditivas.
5. **[sempre] Commit** (mão do usuário, sem trailer). Nada commitado desde o skeleton.

### CLAP spike — status

- venv isolado criado + **torch 2.13 CPU + transformers 5.13 instalados LISO** (minutos, sem
  drama) → provou que CLAP **não é dispendioso** ($0, ~2-4GB disco, roda no CPU). Falta só puxar
  o modelo (`laion/larger_clap_music` ~2GB) + embedar/testar. venv em scratchpad (deletável).

### Arquivos-chave desta sessão (uncommitted)

`muntu/epidemic.py` (novo, 14 testes), `muntu/trilha.py` (+regra de silêncio), `pipeline.py`
(+`banco`), `app.py` (+checkbox), `docs/pesquisa/apis-musica-licenciada-2026-07.md` (§4 +endpoints
+calibração), `docs/handoff-2026-07-08-epidemic-integracao.md`, este spec.
