# Handoff — Muntu Score (2026-07-07, sessão trilha-por-parte)

Ler antes de continuar. Repo `~/Documentos/muntu-score`. **NADA COMMITADO** — commits são
mão do Marcos, sem trailer ([[muntu-score-commits-sem-trailer]]). Supersede a parte de
MÚSICA do `handoff-2026-07-07.md` (a parte de sound design/foley segue valendo).

## TL;DR

Reframe grande de conceito + arquitetura nova de trilha. **A trilha NÃO é mais 1 mood → 1
cama contínua.** É uma **sequência de músicas por PARTE narrativa** (festa = diegético →
ele sai = score), lida automaticamente do filme. Hits/stems nos cortes = **OFF** (estética
de trailer, descartada). Construído nesta sessão: **reader** (VLM segmenta o filme) +
**apply** (`trilha.py` monta a cama por parte). Wired no pipeline. **79 testes verdes.**
**Ainda NÃO rodou end-to-end com API real** (só reader validado 1x no filme). Ver memórias
[[muntu-trilha-psicologica-sem-hits]], [[muntu-trilha-por-parte]].

## Arquitetura (o que ficou)

```
analyze (cortes)
  → mood.analisa_clima   → cenas {clima, energia, climax}     (alimenta o FOLEY)
  → reader.le_timeline   → timeline {partes[], stop_t, climax_t}  (alimenta a TRILHA)
       cada parte = {start, end, tipo: diegetic|score, mood (free-text), papel}
  → SFX (sound design C): foley + ambiência NARRAM as cenas (sob a música)
  → trilha.monta_trilha(timeline): cama POR PARTE
       cada parte → prompt → base_bed.gerar_cama (1 geração/parte)
       diegetic → band-limit (soa saindo das caixas) ; score → limpo
       STOP: a música cala ~1.2s no beat do reveal (foley continua → a piada respira)
  → mix (música-forward: foley SOB a música) → mux
```

**Princípios cravados pelo usuário (30 anos de áudio):**

- Trilha = elemento **psicológico** que veste a narrativa, não sync mecânico ao corte.
- **Zero hit no corte** (isso é trailer; comercial moderno quase nunca faz).
- Trilha troca de roupa quando a **história** troca (diegético festa → score).
- **GENERALIDADE é constraint:** vale pra QUALQUER filme/clima, não só o Pringles cômico.

## Módulos novos/mudados (não commitado)

| Arquivo             | Estado                                                                                                                                                                                                             |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `muntu/reader.py`   | **NOVO.** VLM (Gemini) segmenta o filme → timeline de partes (diegetic/score + mood free-text + papel) + climax + STOP. `le_timeline` best-effort ({} on fail). Reusa infra de visão de `mood.py`.                 |
| `muntu/trilha.py`   | **NOVO.** `monta_trilha(timeline, duracao)` = cama por parte + STOP. `_prompt_da_parte` (pack lookup OU free-text), `_diegetico` (band-limit 320-3200Hz -3dB), `_aplica_stop` (silencia janela sem mudar duração). |
| `pipeline.py`       | reader ligado após mood; `timeline.partes` → `monta_trilha`, senão cama única (composition_plan). Gains revertidos (foley SOB música). Kill de hits/stems/warp/render_acentos.                                     |
| `muntu/director.py` | M1 (composition_plan sempre c/ elevenlabs), M3 (clima do VLM no bed_prompt), M4 (`_idx_climax` ancora no `cena.climax` do VLM), M6 (Outro em peça ≥12s).                                                           |
| `muntu/mood.py`     | guard `_parse_json` (content vazio → raise, não crash `.strip()`); `max_tokens` 8000→24000.                                                                                                                        |
| `packs/*.json`      | mapa de climas do usuário (12 packs, feito em paralelo — ver [[muntu-climas-pesquisa-fechada]]).                                                                                                                   |
| Testes              | `test_reader.py` (6), `test_trilha.py` (7). Total 79 verdes.                                                                                                                                                       |

## ⚠️ Auditoria — achados (priorizados)

- **#1 [DEGRADA — TOP próxima sessão] `trilha.py:31` — pack lookup é código MORTO no per-part.**
  `pack_por_clima` casava **palavra exata** de clima, mas o reader emitia só mood free-text →
  nunca casava → mapa de climas inerte.
  **✅ RESOLVIDO (mesma sessão):** o reader agora emite `clima` (vocab `mood.MOODS`) por parte,
  além do `mood` free-text. `_prompt_da_parte`: **score** com `clima` que casa um pack → usa o
  `prompt_template` curado (comedic→playful, tense→tenso, verificado); **diegético** (source
  music, específico do filme) ou clima sem pack → direção livre (`mood`). Sem duplicata de
  invariantes. 80 testes verdes.

- **#2 [menor — desperdício] 3 calls VLM/latência.** `mood` + `reader` + `sfx_map` extraem
  frames e chamam o VLM separado (mood e reader montam montagem quase idêntica). FIX: extrair
  frames/montagem 1x; idealmente fundir mood+reader numa call.

- **#3 [menor] `plano_de_score` faz trabalho morto** — pós-reframe só o `bed_prompt` é usado
  (acentos/estima_bpm calculados à toa). FIX: helper só-bed_prompt.

- **#4 [menor] stale:** `run(stems_dir=...)` e a docstring de `com_cama=False` ("mix só com
  SFX + stems") mentem — não há mais camada de stems no runtime. FIX: remover.

**Confirmado correto:** assembly/cobertura (`_cobre` contígua, dura exato), parte <3s (gera
≥3s corta no span — payoff 1.9s ok), STOP (silêncio real, preserva duração, stop em cena 1/
além-do-fim tratados), diegético (band-limit sensato), generalidade (sem hardcode de filme/
gênero), degrade/gating (sem key → cama única → skeleton; `monta_trilha` dentro do try).

## Pendências ordenadas (próxima sessão)

1. ~~Fix #1 (bridge free-text→pack)~~ ✅ **FEITO** — reader emite `clima` por parte; score usa
   pack curado, diegético usa free-text.
2. ~~Regenerar a demo por parte~~ ✅ **FEITO** (`outputs/demo_partes.mp4`) — 3 partes (diegético
   festa → score → pizzicato), STOP cena 10. **Julgar de ouvido** ainda pendente.
3. ~~Gate de confiança de valence~~ ✅ **FEITO** — reader emite `confianca_valence` por parte;
   pack minor (tenso/melancolico) só dispara com `alta`, senão bed AMBIGUO (nem minor que
   inverte, nem major que adoça). Não afeta a demo cômica (major/alta). Ver docs de pesquisa ↓.
4. **Reverb de sala no diegético** (hoje só band-limit) — pra soar mais "no ambiente".
5. **Unificar mood+reader** numa call (custo/latência).
6. **Commit** (mão do Marcos, sem trailer) + **rotacionar TODAS as keys** (queimadas).
7. **A/B do mapa de climas** (packs) — craft do usuário, [[muntu-climas-pesquisa-fechada]].

**Pesquisa que fundamenta o mapa de climas + o gate (LER na próxima sessão):**
`~/Documentos/career/pesquisa/climas-trilha-filme-comercial-br-2026-07.md` (convenção real de
scoring por clima, lente BR, effect sizes β) + `~/Documentos/career/pesquisa/mapa-vlm-mood-clima-muntu-2026-07.md`
(VLM-mood → clima → pack auditado + a regra do gate de valence). Artefato ainda NÃO aplicado
desses docs: reader multi-frame emitir arousal(BPM) explícito; `confianca_valence` hint em
`mood.py` pro path single-bed (o gate hoje só cobre o path por-parte via reader).

## Como rodar / validar

```bash
cd ~/Documentos/muntu-score && source venv/bin/activate
python -m pytest tests/ -q                       # 79 verdes

# demo com trilha POR PARTE (custa ~3 gerações ElevenLabs; keys vivas no .env):
python -c "from dotenv import load_dotenv; load_dotenv(); from pipeline import run; print(run('outputs/real.mp4', out_path='outputs/demo_partes.mp4', com_cama=True))"

# ver a timeline que o reader extrai de um filme (1 call Gemini):
python -c "from dotenv import load_dotenv; load_dotenv(); from muntu.analyzer import analyze; from muntu import reader; b=analyze('outputs/real.mp4'); print(reader.le_timeline('outputs/real.mp4', b['cortes'], b['duracao']))"
```

Reader validado no `real.mp4` (Pringles): `S1-S4 diegetic "muffled indie-rock from party
speakers" → S5-S8 score "uplifting indie-pop" → S9-S10 score "quirky pizzicato"`,
STOP=cena 9, climax=cena 10. **Bateu exato com a leitura humana do usuário.**

## Config (.env — gitignored, TODAS queimadas → ROTACIONAR)

```
MUNTU_MOOD_API_KEY=<OpenRouter>   MUNTU_MOOD_MODEL=google/gemini-2.5-pro   # reader + mood + sfx_map
ELEVENLABS_API_KEY=<scope sound_generation + music>   # SFX + cama (por parte)
MUNTU_BED_PROVIDER=elevenlabs     # cama via ElevenLabs (composition_plan só funciona aqui)
STABILITY_API_KEY / REPLICATE_API_TOKEN   # fallback/sem uso na trilha
```

Nota: `DEFAULT_PROVIDER=stability` IGNORA composition_plan (só prompt+duração) — a curva
estruturada só existe no `elevenlabs`. Manter `MUNTU_BED_PROVIDER=elevenlabs`.

---

## Atualização fim-de-sessão — trilha por parte REFINADA (2026-07-07, dirigido por ouvido)

Iteração longa com o usuário ouvindo `demo_partes.mp4`. **90 testes verdes.** Nada commitado.
**Regras criativas na memória [[muntu-trilha-regras-criativas]] — LER.** Princípio-mãe: **o
reader (LLM) SEMPRE escolhe** (diegético/score, mood, era, registro cômico); o apply só
executa; **output errado = calibra o READER (prompt), não o apply**.

### Fixes aplicados (todos em `muntu/trilha.py` + `muntu/reader.py`, sem regen de áudio ainda)

1. **Gate de valence** — pack minor (tenso/melancolico) só dispara com `confianca_valence: alta`
   (reader emite por parte); senão `AMBIGUO` (nem minor que inverte, nem major que adoça).
2. **Fix #1 concluído** — reader emite `clima` (vocab) → score usa pack curado; diegético/sem-match → free-text.
3. **Diegético = som do ambiente:** band-limit + **reverb** (ffmpeg aecho) + **já-tocando** (sem
   intro/build) + nível `DIEGETICO_GAIN_DB=-10` (festa alta; total ~−13 após BED_GAIN −3).
4. **STOP roteado:** score→corte limpo; diegético + **filme cômico** (film-level, `filme_comico`)
   → gag **vinil desligando** (`_wind_down`, pitch cai), SÓ dentro da parte diegética
   (`_stop_diegetico(…, ate_ms)` — não apaga o score seguinte, era bug); diegético não-cômico→não para.
5. **Era** (`reader.era`, lida do visual pelo LLM): RETRÔ → força a época (diegético E score);
   MODERNO → não força (trilha retrô = escolha do mood, reader decide). `_e_retro()`.
6. **Comédia = muitos registros** (pizzicato/surf/80s-sax/soft-contra-absurdo) — hint no reader, não default 80s.
7. **Merge de partes curtas** (`reader._merge_curtas`, <1.5s) — sliver de 0.2s virava silêncio (era o "sem música no fim").
8. **Pack `romantico` = "romântico anos 80"** — ganhou saxofone + Rhodes + synth strings + gated reverb (cafona/kitsch).

### Feedback do usuário sobre a última demo (14:14) — o que ainda falta VERIFICAR por áudio

- ✅ STOP na hora certa; ✅ ambiente certo.
- ❌ Diegético entrava tarde → fix #3 (already-playing). ❌ Diegético baixo → fix #3 (−10). ❌ Sem
  música no fim → fix #7 (merge). **Nenhum verificado por regen ainda** — o próximo passo é gerar
  e ouvir se os fixes resolveram.

### Próximo passo #1: REGENERAR e ouvir

```bash
python -c "from dotenv import load_dotenv; load_dotenv(); from pipeline import run; print(run('outputs/real.mp4', out_path='outputs/demo_partes.mp4', com_cama=True))"
```

Julgar: diegético entra do início + alto + ambiente; vinil-power-down no fim da festa (se cômico);
score veste a narrativa; sem buraco de silêncio no fim.

### Pendências abertas

- **Verificar os 8 fixes por áudio** (regen acima) — a maioria não foi ouvida.
- **Registro cômico do score**: o reader escolhe (pizzicato/surf/80s/soft) — se sair errado, calibrar o prompt do reader.
- Reverb de sala é `aecho` (slap), não convolução — pode melhorar. Merge perde o "punchline" pizzicato (podia virar foley/SFX).
- Custo: 3 calls VLM (mood+reader+sfx_map) + N gerações ElevenLabs por run. Unificar mood+reader.
- Commit (mão do Marcos) + rotacionar keys.

**Contagem de testes: 90 verdes** (era 79 no topo deste doc).

---

## Atualização 2 — reader token-fix + calibração diegética + O PROBLEMA CENTRAL (2026-07-07)

Continuou a iteração por áudio. **2 fixes técnicos + 1 problema de fundo identificado.**

### Fixes

- **`reader.MAX_TOKENS` 24000 → 48000.** Com o prompt do reader crescido (era + menu cômico +
  confianca_valence) o Gemini estourava (finish=length → content vazio → timeline `{}` →
  **fallback de cama única**). Foi a causa do "desandou": uma demo saiu single-bed, outra
  all-score. Com 48000 o reader volta a devolver as partes.
- **Critério de diegético REFORÇADO** (`reader.PROMPT`, bullet `tipo`): "cena de festa/club/bar
  → a música quase SEMPRE é diegética; não cair em score". Antes o reader lia a festa como
  score (sem diegético). Probe pós-fix: `S1-S3 DIEGETIC "Loud upbeat 1990s house party pop"`.

### ⚠️ PROBLEMA CENTRAL — estocasticidade do reader (TOP próxima sessão)

O reader (Gemini) **varia muito run-a-run**: às vezes marca festa diegética, às vezes tudo
score; às vezes score 80s cafona, às vezes indie-folk. **A MELHOR demo até agora** (relato do
usuário) foi **diegético + "cama de bolo" 80s cafona** — e NÃO é reproduzível de forma
confiável. Toda calibração de prompt melhora a tendência mas não fixa a saída.

**Direção pra resolver (decidir com o usuário):**

1. **Calibrar mais o prompt** (empurrar diegético-festa + retrô-cômico em montagem-de-vida) —
   melhora odds, não garante.
2. **Mecanismo de PIN/override** — quando uma leitura fica boa, salvar a timeline (JSON) e
   permitir regenerar só o áudio a partir dela (sem re-ler o filme). Dá reprodutibilidade +
   controle ao usuário. **Provavelmente o caminho certo** — separa "ler o filme" de "gerar",
   e o usuário trava a leitura boa.
3. Baixar `temperature` do reader (se o backend expõe) pra reduzir variância.

Divisão de trabalho cravada pelo usuário: **usuário = ouvido/direção; Claude = técnico/
calibração** ([[muntu-trilha-regras-criativas]]).

**Estado:** 90 testes verdes. Reader calibrado (diegético volta). Nada commitado. A demo
"diegético + 80s cafona" (a melhor) precisa ser recuperada — via calibração ou pin.
