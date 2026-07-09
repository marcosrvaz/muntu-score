---
tipo: pesquisa
data: 2026-07-07
url: derivada — cruza [[climas-trilha-filme-comercial-br-2026-07]] x repo muntu-score
---

# Mapa VLM-mood → clima → pack (auditado) — Muntu Score, jul/2026

Fecha o elo que faltava em [[climas-trilha-filme-comercial-br-2026-07]]: traduz o **mood
que o VLM cospe** na **convencao musical real** (trilha/cinema/ad) e no **pack** que a tool
toca. Ancorado no ground truth do repo `~/Documentos/muntu-score` (`muntu/mood.py` +
`packs/*.json` + `director.pack_por_clima`), nao em achismo. Resolve o "mood idiota"
([[muntu-biblioteca-de-climas]]).

## Ground truth (repo, 2026-07-07)

- **Vocabulario do VLM** (`mood.py:33`, 12 moods): `romantic, tender, nostalgic,
melancholic, joyful, playful, comedic, energetic, tense, calm, epic, neutral`.
- **Auto-selecao** (`director.pack_por_clima`): pega o pack cujo campo `climas` cobre o mood
  dominante; **sem match ou clima None → `default`**. Packs sem `climas` (natal/surf) nunca
  auto-selecionam (override manual).
- **Packs com `climas`:** so **playful** (joyful/energetic/playful/comedic) e **romantico**
  (romantic/tender/nostalgic/melancholic). `default`/`natal`/`surf` sem `climas`.
- **Modo:** os 5 packs sao `mode: major`. **Nenhum pack minor existe.**

## Tabela de traducao (VLM-mood → convencao real → pack)

Convencao vem da secao 2 de [[climas-trilha-filme-comercial-br-2026-07]] (craft de scoring).

| #   | VLM mood        | Convencao musical real (modo/andamento/instrumentacao)                          | Pack hoje             | Veredito                                                                                    |
| --- | --------------- | ------------------------------------------------------------------------------- | --------------------- | ------------------------------------------------------------------------------------------- |
| 1   | **romantic**    | maior, medio-lento, guitarra mellow/Rhodes/cordas quentes                       | romantico             | ✅ ok                                                                                       |
| 2   | **tender**      | maior, lento, acustico intimo                                                   | romantico             | ✅ ok                                                                                       |
| 3   | **nostalgic**   | maior, retro, Rhodes/soul pop                                                   | romantico             | ✅ ok                                                                                       |
| 4   | **melancholic** | **MENOR**, 60-80 BPM, **piano+violoncelo** ("magra e esguia")                   | romantico (**major**) | ⚠️ modo errado — romantico e major; melancholic pede minor                                  |
| 5   | **joyful**      | maior, medio-rapido, acustico brilhante                                         | playful               | ✅ ok                                                                                       |
| 6   | **playful**     | maior, rapido, plucky/bouncy/quirky                                             | playful               | ✅ ok                                                                                       |
| 7   | **comedic**     | maior, rapido, bouncy, leve                                                     | playful               | ✅ ok                                                                                       |
| 8   | **energetic**   | maior, rapido, driving                                                          | playful               | 🟡 serve, mas playful e "quirky/bouncy" — energetic puro (ex. esporte/acao) fica subservido |
| 9   | **tense**       | **ATONAL/menor**, dissonante (2a menor, 5a dim), graves, cordas staccato        | **default**           | ❌ GAP CRITICO — cai em bed corporate warm **major** = oposto                               |
| 10  | **calm**        | maior/ambiguo, lento, texturas suaves, sus chords                               | **default**           | ❌ mismatch — corporate motion nao e calmo                                                  |
| 11  | **epic**        | maior/hibrido, **metais** (trompete/trompa), percussao orquestral, grande naipe | **default**           | ❌ GAP CRITICO — corporate warm nao e epico                                                 |
| 12  | **neutral**     | ambiguo, medio (76-120), drones/pedais, texturas de apoio                       | **default**           | ✅ aceitavel (neutral→corporate neutro)                                                     |

## Auditoria — o que a tabela revela

- **Cobertura: 8/12 com pack dedicado.** 4 moods (`tense, calm, epic, neutral`) caem no
  `default`.
- **2 GAPS CRITICOS** (mood mal-servido, nao so ausente):
  - **`tense` → corporate warm major.** Suspense/tensao pede dissonancia/menor/graves. A tool
    hoje toca o OPOSTO do clima que o VLM leu. Pior erro do conjunto.
  - **`epic` → corporate warm.** Epico pede metais + percussao orquestral. Corporate bed nao
    entrega escala heroica.
- **1 mismatch de MODO:** `melancholic` esta no `romantico`, que e **major**. A convencao
  real (Central do Brasil, "magra e esguia") e **minor + piano/cello**. Major "adocica" a
  tristeza — perde o registro.
- **Buraco estrutural: nenhum pack `minor`.** As convencoes de `tense` e `melancholic`
  dependem de menor/atonal — **inexpressaveis** com o parque atual (5 packs major). Sem um
  pack minor, o "adjetivo subdetermina" (achado central) nao tem como virar som certo.
- **`neutral` ok mas silencioso:** funciona por fallthrough, nao por intencao. Melhor cravar
  explicitamente pra nao mascarar futuros gaps.
- **`energetic` observar:** playful cobre, mas mistura energia com humor/quirkiness. Ad de
  esporte/automotivo energetico-serio fica com timbre errado (bouncy).

## Recomendacoes (packs a criar/ajustar)

Prioridade por dano: **tense > epic > melancholic-modo > calm > neutral-explicito > energetic**.

1. **Novo pack `tenso`** (`mode: minor`, claims `["tense"]`) — resolve o pior gap + estreia
   modo menor no parque:

```json
{
  "nome": "tenso",
  "climas": ["tense"],
  "bpm_range": [80, 120],
  "mode": "minor",
  "bed_estilo": "tense suspense underscore, low sustained strings, sparse dissonant piano, subtle synth drones, unsettling, no drums",
  "prompt_template": "Tense suspense underscore bed, {bpm} BPM, ominous and unsettling, {mode} key, low sustained strings, sparse dissonant piano stabs, subtle synth drones, instrumental only, limit midrange clutter, sudden end."
}
```

2. **Novo pack `epico`** (`mode: major`, claims `["epic"]`):

```json
{
  "nome": "epico",
  "climas": ["epic"],
  "bpm_range": [110, 140],
  "mode": "major",
  "bed_estilo": "epic cinematic bed, brass fanfare, soaring strings, orchestral percussion, heroic, building, no vocals",
  "prompt_template": "Epic cinematic bed, {bpm} BPM, triumphant and building, {mode} key, brass fanfare, soaring strings, orchestral percussion, instrumental only, sits under voiceover, uplifting build to a clean end."
}
```

3. **`melancholic` → mover pra pack minor.** Tirar de `romantico` (que fica com
   romantic/tender/nostalgic, todos major-ok) e criar `melancolico` minor (piano+cello,
   60-80 BPM) OU absorver em variacao minor. Preserva o registro "magra e esguia" BR.
4. **`calm` → pack `calmo`** (major/ambiguo, lento, piano/pad minimal) OU aceitar default com
   ressalva documentada. Recomendo pack proprio — corporate motion contradiz calmo.
5. **`neutral` → cravar `climas: ["neutral"]` no default** pra ser intencional, nao
   fallthrough silencioso.
6. **`energetic` (watch):** se surgir demanda de ad energetico-serio, split pra pack proprio
   (driving drums/bass, sem quirkiness). Por ora playful serve.

**Efeito:** cobertura 8/12 → **12/12 intencional**, com modo menor representado (tense +
melancholic corretos) e os 2 gaps criticos fechados.

## Pesos β aplicados — confianca por eixo (2026-07-07)

Camada nova sobre o mapa, ancorada na secao 6 de [[climas-trilha-filme-comercial-br-2026-07]]
(effect sizes de McMaster/McGill/Berkeley/Max Planck). Nao muda o QUAL pack — muda **quanto
confiar de cada eixo** e **o que fazer no baixo-confianca**.

**Achado que valida o design atual:** os 2 unicos knobs dos packs — `bpm_range` e `mode` —
sao **exatamente os 2 eixos que a ciencia isola**. Nao ha 3o knob a inventar; instrumentacao
e sabor downstream.

- **`bpm_range` ← arousal.** Attack/densidade ritmica domina o arousal — **63,2% da variancia,
  1 cue** (Schutz/McMaster); Tempo→arousal **β=.55** (Gu 2026). Um cue manda → robusto a QUAL
  cue voce consegue ler → **eixo confiavel PRA ESTE pipeline** (VLM le motion/cut-rate facil).
- **`mode` ← valence.** Modo e o maior cue de valence (**38,9%**), mas a variancia de valence
  se divide entre modo+pitch+attack+harmonia; dissonancia→valence **β=−.43**. **⚠️ Nao e que
  valence seja imprevisivel** (Schutz modela valence a 81% vs arousal 50%) — e que o cue-chave
  (MODO) e o mais dificil de inferir de pixel de video E cultura-dependente (McGill: cultura>
  treino). → **eixo arriscado NESTE pipeline**, nao no ouvido humano. Ver ressalva 6.2 de
  [[climas-trilha-filme-comercial-br-2026-07]].

### Tabela β: knob + confianca por mood

Quadrante V/A = **derivacao propria** (circumplex de Russell + convencao da secao 2), nao
extraido de fonte. `confianca_valence` = julgamento de quao facil o VLM crava o sinal daquele
mood de video. Ponto de partida testavel, nao medido.

| VLM mood        | Quadrante V/A        | arousal→`bpm` | valence→`mode`   | Confianca valence                           | Risco se errar                              |
| --------------- | -------------------- | ------------- | ---------------- | ------------------------------------------- | ------------------------------------------- |
| **romantic**    | HV·LA                | baixo-medio   | major            | alta                                        | baixo                                       |
| **tender**      | HV·LA                | lento         | major            | alta                                        | baixo                                       |
| **nostalgic**   | HV/LV·LA             | medio         | major            | **media** (bittersweet — borda de valence)  | adoca demais se era saudade triste          |
| **melancholic** | LV·LA                | 60-80         | **minor**        | **baixa**                                   | ❌ major "adoca a tragedia" (bug antigo)    |
| **joyful**      | HV·HA                | medio-rapido  | major            | alta                                        | baixo                                       |
| **playful**     | HV·HA                | rapido        | major            | alta                                        | baixo                                       |
| **comedic**     | HV·HA                | rapido        | major            | alta (valence) / **arousal so multi-frame** | ❌ erro Pringles = perde o pace, nao o modo |
| **energetic**   | ~neutro·HA           | rapido        | major            | media (valence secundario a energia)        | baixo                                       |
| **tense**       | LV·HA                | 80-120        | **minor/atonal** | **baixa**                                   | ❌ major = OPOSTO do clima (pior erro)      |
| **calm**        | HV·LA                | lento         | major/ambiguo    | media                                       | motion-bed contradiz calmo                  |
| **epic**        | HV·HA (alta potency) | rapido        | major            | alta                                        | baixo                                       |
| **neutral**     | mid·mid              | 76-120        | ambiguo          | —                                           | —                                           |

### 3 regras que caem dos β

1. **Arousal so existe multi-frame — e a raiz do erro Pringles.** Um still nao tem tempo/
   densidade → o eixo confiavel (β=.63) fica cego. Com multi-frame (motion, cut-rate, acao)
   o arousal destrava e vira a leitura mais robusta. **Fix do Pringles = multi-frame, nao
   trocar modo** ([[muntu-mood-precisa-assistir]]): a comedia lida como romance perdeu o
   PACE (arousal), o modo (major) estava certo nos dois.
2. **Valence e o eixo ruidoso mesmo com contexto; `mode` e a aposta arriscada.** Baixa
   confianca de valence → **modo ambiguo/sus, NUNCA major commitado**. Major default sobre
   cena negativa = adocicar tragedia (o bug `melancholic→major`). O custo de errar valence e
   assimetrico: pack minor numa cena feliz soa "off"; pack major numa cena triste **mente**.
3. **Ordem de selecao robusta: casar arousal-tier primeiro, refinar valence depois.** BPM
   band (do motion multi-frame) e o key robusto; `mode` entra como refino gated. **Pack minor
   (`tenso`, `melancolico`) so deve disparar com confianca de valence alta** (multi-frame
   confirma cena negativa) — senao cai no neutral/ambiguo, nao num major que inverte o clima.

### Artefato concreto pro repo (proximo passo, nao aplicado)

- Adicionar hint `confianca_valence: alta|media|baixa` por mood no `mood.py` (coluna acima).
- `director.pack_por_clima`: se mood tem `mode: minor` **e** `confianca_valence != alta` →
  fallback pra `neutral` (ambiguo), nao pro pack minor. Impede o pior erro (tense/melancholic
  commitado com leitura fraca).
- Leitura do VLM: exigir janela **multi-frame** antes de emitir arousal (BPM band); single-frame
  so pode emitir valence-tentativa (baixa confianca). Fecha a raiz do Pringles no nivel do reader.

## Caveats

- Convencoes de `tense/melancholic/epic` (secao 2) sao **solidas-mas-nao-trianguladas** — a
  verificacao adversarial do deep-research foi cortada no limite de gasto; vem do NotebookLM
  (fontes de craft) sem voto. Ver caveats de [[climas-trilha-filme-comercial-br-2026-07]].
- BPM/mode dos packs propostos = ponto de partida testavel (A/B na tool), nao lei.
- **APLICADO no repo 2026-07-07** (packs criados/editados, teste atualizado, 36 verdes).
  **Commit e so seu** — [[muntu-score-commits-sem-trailer]] (nada commitado por mim).

## Open questions

- `calm` merece pack proprio ou default basta? (decisao de produto)
- `energetic` fica em playful ou vira pack? (depende do mix de ad-alvo)
- Convencao de **luxo** (claim morto no deep-research) — nao ha mood VLM "luxo"; entra como
  variacao de qual? (provavel `tender`/`neutral` com timbre "caro")
- Aplicar `confianca_valence` + gate de pack minor no `director` (secao Pesos β) — decidir se
  vira campo em `mood.py` ou regra hardcoded no `pack_por_clima`.
- Reader multi-frame emite arousal; single-frame so valence-tentativa — mudanca no reader
  (Gemini 2.5 Pro), maior que edicao de pack. Escopo pra sessao propria.

## Log

- 2026-07-07 — Criada. Tabela VLM-mood→convencao→pack + auditoria contra repo real.
  Achado: 4 moods caem no default; tense/epic sao gaps criticos; nenhum pack minor; modo de
  melancholic errado. Recomendados packs `tenso` (minor) e `epico`.
- 2026-07-07 — APLICADO. Criados `tenso`(minor), `epico`, `melancolico`(minor), `calmo`;
  `melancholic` removido de romantico; `neutral` cravado no default. `test_director` atualizado
  (cobertura 12/12). Verificado: `pack_por_clima` mapeia os 12 moods intencional, 0 overlap,
  36 testes verdes. Falta: commit (usuario) + A/B dos BPM/timbres na tool.
- 2026-07-07 — **Pesos β aplicados** (secao nova). Effect sizes da secao 6 de
  [[climas-trilha-filme-comercial-br-2026-07]] mapeados nos 2 knobs dos packs: `bpm_range`←
  arousal (confiavel, β=.55/63%), `mode`←valence (ruidoso, 38,9% espalhado). 3 regras: (1)
  arousal so multi-frame = raiz do erro Pringles; (2) baixa confianca de valence → modo
  ambiguo, nunca major commitado (custo assimetrico); (3) selecao arousal-first, pack minor
  gated. Artefato pro repo (`confianca_valence` + gate no director) especificado, NAO aplicado.
- 2026-07-07 — **Auto-auditoria.** Corrigido o racional do knob `mode`: nao "valence
  imprevisivel" (Schutz modela a 81%), e sim "modo dificil de ler de video + cultura-dependente"
  — frágil NESTE pipeline, nao no ouvido. Coluna Quadrante V/A marcada como derivacao propria
  (nao-fonte). Regras 1-3 e a logica de gate seguem validas (independem da tese contestada).
- 2026-07-08 — **este mapa vira o casamento do provedor B (Epidemic).** `muntu/epidemic.py`
  deriva DESTA tabela + da convenção §2 de [[climas-trilha-filme-comercial-br-2026-07]] a seleção
  de faixa real: mode→`mood=` (CLIMA_EPIDEMIC), arousal→`bpmMin/Max` (CLIMA_BPM, as bandas por
  clima) e instrumentação→`genre=` (CLIMA_GENERO). O mesmo mapa que rege a geração A (packs) rege
  a busca B — validado ao vivo (7 climas, casam nos 3 eixos). Ver [[apis-musica-licenciada-2026-07]] §4.
