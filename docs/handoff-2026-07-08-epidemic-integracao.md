# Handoff 2026-07-08 — Integração Epidemic (provedor B) + auditoria GLM

Sessão dirigida pelo usuário: auditar a sessão GLM de 2026-07-07/08, depois construir a
integração da API de banco de trilha (Epidemic). Contexto no repo `~/Documentos/muntu-score`
(Claude pair, **nada commitado** — convenção: mão do usuário, sem trailer).

## 1. Auditoria da sessão GLM (2026-07-07 noite → 2026-07-08)

Duas coisas foram feitas pelo GLM antes da sessão morrer envenenada (troca de backend
GLM↔Anthropic → 400 eterno):

**SFX map encolhido — ✅ correto.** `muntu/sfx_map.py`: `MAX_TOKENS` 64000→8000, prompt de
parágrafos verbosos → tags curtas ("MAX ~10 WORDS", "not an essay"). Reverte o fix errado
anterior (subir teto). Backup `sfx_map.py.bak-verbose-2026-07-07`. Testado.

**Marcha nupcial (citação MIDI) — ⚠️ código pronto, asset nunca nasceu.**

- Escrito+testado: `muntu/tons.py` (detecta tom via librosa Krumhansl-Schmuckler + transpõe
  via ffmpeg `rubberband=pitch=`, fator `2**(semitons/12)` — bug pego por probe: pitch é
  FATOR, não semitom). `trilha.py`: removeu o weave da citação do prompt (aposta ToS morta),
  add `_overlay_citacoes` (cola áudio PD no beat, alinhado ao tom da cama).
- **NUNCA rodou:** `sudo apt install fluidsynth fluid-soundfont-gm` (o "banco de midi" =
  soundfont GM) foi sugerido, usuário não rodou. `fluidsynth`/`timidity` ausentes. Sem
  `.mid`/`.sf2`, sem `assets/citacoes/`, sem `marcha_nupcial.mp3`. → `_overlay_citacoes` é
  **no-op** hoje (asset ausente → skip). Gated, binário intacto.
- **DECISÃO DO USUÁRIO: MIDI/marcha parqueada.** Retomar = install + gerar asset + validar
  timbre de ouvido (órgão MIDI-renderizado é escolha de gosto não-validada).

## 2. Integração Epidemic (provedor B) — CONSTRUÍDA nesta sessão

Decisão do funil (ver `docs/pesquisa/apis-musica-licenciada-2026-07.md` §4): das libs de
trilha, **Epidemic é a única self-serve testável** (Artlist/Soundstripe/AIMS = contrato).
Free tier = key na hora, prototyping-only (~50 downloads, sem licença comercial); licença
ads = partnership (quando houver cliente). Bate com A-agora/B-quando-cliente.

**Arquitetura:** Epidemic NÃO é geração — é **seleção** de faixa real → entregue como mp3 pro
mecanismo `bed_file` (PIN camada 2, já existente). Reusa todo o encanamento; só troca a fonte
do bed de "gen IA" pra "faixa licenciada". Estocasticidade zero.

**Arquivos (gated, opt-in, 152 testes verdes):**

- `muntu/epidemic.py` (novo):
  - `epidemic_disponivel()` — gate em `EPIDEMIC_API_KEY` + httpx (padrão dos outros provedores).
  - `busca(mood, bpm_min, bpm_max)` — `GET /v0/tracks`. **Robusta:** `_mood_canonico` mapeia
    free-text do reader → keyword de Epidemic (sinônimo pt/en → substring de 32 moods padrão →
    texto limpo). Escada de fallback: mood+BPM → (400 ou vazio) só-BPM → sem filtro. Faixa no
    BPM certo > silêncio.
  - `baixa_faixa(id)` — `GET /v0/tracks/{id}/download?quality=normal` → URL de CDN temporária
    → stream pro disco (cache por track+qualidade). Best-effort: remove mp3 truncado no erro.
  - `bed_para_mood(mood, bpm)` e `popula_beds(timeline)` — seta `bed_file` nas partes **score**
    via mood; pula diegético; respeita `bed_file` já setado (PIN manual). Muta in-place.
- `pipeline.py`: param `banco: bool = False`. Popula beds via Epidemic entre o load da
  timeline e `monta_trilha`. Sem key → loga e cai em A. Import `epidemic` add.
- `app.py`: checkbox "Banco licenciado (Epidemic)".
- `tests/test_epidemic.py` (novo, 10 testes): gate, cache-hit, sem-URL, popula_beds
  (por-mood / pula-diegético / respeita-PIN / no-op sem key), mood_canonico, fallback 400,
  fallback vazio.

## 2b. VERIFICAÇÃO AO VIVO (2026-07-08 tarde — key obtida)

Usuário criou a conta free (App "muntu", plano Free, sem cartão) e gerou a key (colada em
chat → **QUEIMADA, rotacionar**). Probe ao vivo fechou a incerteza da taxonomia e **refatorou
`busca`**:

- Texto livre = `GET /v0/tracks/search?**term**=` (`query`/`q`/`keyword` são ignorados). `mood=`
  em `/v0/tracks` exige **id exato lowercase** do vocab `/v0/moods` (20 ids); "uplifting"/"Dreamy"
  = 0. → `busca` trocada pra `term=` + tradução PT→EN; `_MOODS_EPIDEMIC` inventado virou
  `MOODS_VALIDOS` (os 20 reais, de referência).
- Download = `{url, expires}` (campo `url` confirmado). Track = `{id, bpm, moods:[{id,name}]…}`.
- **End-to-end validado:** `busca("romantico piano")` → Prelude in C / Swedish Piano Song (mood
  `romantic`); `bed_para_mood` baixou mp3 197s 48kHz estéreo; `popula_beds` setou score, pulou
  diegético.

## 2c. CASAMENTO com o mapa de composição (as pesquisas — 2026-07-08)

O usuário exigiu que a seleção B casasse com as pesquisas de clima + o mapa de composição, não
com achismo. `busca(clima, register)` agora usa os **3 eixos por clima** que a composição define,
derivados da pesquisa (Epidemic combina mood+genre+BPM com AND — [[moods-broadcast-prompt-2026-07]] §1):

- **mode → `mood=`** (`CLIMA_EPIDEMIC`, quadrantes V/A do [[mapa-vlm-mood-clima-muntu-2026-07]]);
  correção: energetic→**running** (bucket cinético), não euphoric.
- **arousal → `bpmMin/Max`** (`CLIMA_BPM`, tabela de convenção §2 de
  [[climas-trilha-filme-comercial-br-2026-07]]) — ativa o eixo de BPM que era inerte (clima dá a
  banda; reader não precisa emitir bpm).
- **instrumentação → `genre=`** (`CLIMA_GENERO`; `register` que nomeia gênero vence). Vocab real
  `/v0/genres` (20, `GENEROS_VALIDOS`); granular via `term=`.
  Escada: mood+genre+bpm → mood+bpm → mood → term → browse. **Prova ao vivo (7 climas):** todos
  casam nos 3 eixos, n>0. **156 testes verdes** (14 no epidemic).

## 3. Achados de auditoria da própria integração (honesto)

Sólido:

- Gating idêntico aos demais provedores; sem key nunca quebra o binário.
- `busca` robusta contra a incerteza mood-enum-vs-free-text (fallback absorve sem a key).
- Encaixa no `bed_file` existente sem tocar no pipeline de mix.

Fraco / a refinar (nenhum quebra o binário):

- **`bed_file` NÃO passa por warp** — só o branch de geração warpa. Faixa Epidemic =
  atmosfera, sem beat-lock ao corte. Consistente com "música nunca carrega sync", mas o BPM
  de busca é o único alinhamento. (Corrigi a nota: eu tinha escrito "corte/warp" errado.)
- **Reader não emite `bpm` por parte** → filtro de BPM da busca inerte hoje (sempre None).
  Pra ativar: derivar BPM da cadência dos cortes e passar pra `popula_beds`.
- **`bed_offset` não setado** → faixa toca do 0 (intro fraca), não pula pro refrão.
- Taxonomia mood + shape de download: **RESOLVIDO ao vivo (§2b)** — `term=` search + vocab
  real. Falta só o Soundmatch by-video (stub; `term` cobre free-text por ora).

## 4. Pendências / como retomar

1. **Key: obtida, mas QUEIMADA** (colada em chat 2026-07-08). Rotacionar: revogar no dashboard
   Epidemic → gerar nova → `EPIDEMIC_API_KEY` no `.env` **sem colar em chat**.
2. **A/B de ouvido** — `run(real.mp4, banco=True)` (B-Epidemic) vs A-IA, com PIN. É o próximo
   teste de valor (a integração já baixa faixa relevante; falta ouvir no filme).
3. Refino opcional: `bed_offset` default (pular intro da faixa) + Soundmatch by-video.
4. **COMMIT** (mão do usuário, sem trailer) — nada commitado: `epidemic.py`, `tons.py`,
   `sfx_map.py` encolhido, `trilha.py` (marcha overlay), `pipeline.py`, `app.py`, testes.
5. **ROTACIONAR keys** — coladas em chat em sessões passadas + `env` dump 2026-07-08.
6. Marcha/MIDI parqueada (§1) — retomar só se quiser a citação nupcial.

## Contexto de vaults (reorg do usuário)

Em outra sessão o usuário **separou o vault career do vault muntu**: as notas de pesquisa de
música (`apis-musica-licenciada`, `climas-trilha`, `sound-design-ia`, etc.) migraram de
`career/pesquisa/` → `muntu-score/docs/pesquisa/`. O working tree do vault career tem essas
deleções + o handoff enxugado NÃO-commitadas (trabalho da outra sessão). Não commitar pelo
usuário. Esta nota e a de pesquisa vivem agora em `muntu-score/docs/`.
