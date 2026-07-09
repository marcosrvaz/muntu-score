---
tipo: pesquisa
data: 2026-07-07
status: deprecada
url: multi-fonte (ver secao Fontes)
---

# Biblioteca de moods → prompt de musica-gen (broadcast/advertising) — jul/2026

> ⚠️ **DEPRECADA (2026-07-07).** Feita no alvo errado (ferramentas de IA de musica), antes do
> redirect pra pesquisa organica de trilha real. Substituida por
> [[climas-trilha-filme-comercial-br-2026-07]] (a pesquisa de verdade) + o mapa aplicado
> [[mapa-vlm-mood-clima-muntu-2026-07]]. **Mantida so como referencia da camada downstream**
> (o COMO frasear prompt pro modelo de gen-IA) — nao e a taxonomia de clima. Ver
> [[pesquisa-clima-ancorar-musica-filme]] pro motivo do redirect.

Pesquisa pra resolver o gap "mood idiota" do [[caminhos/ia-aplicada|Muntu Score]]: o VLM
le o clima certo, mas o mapa clima→prompt de musica e cru. Objetivo = biblioteca
**mood→prompt** colavel em `packs/*.json`, focada em BED publicitario/broadcast.
Irma de [[sound-design-ia-2026-06]] e [[geradores-musica-ia-2026-06]].

**Metodo (4 canais paralelos):** `/deep-research` (103 agents, 21 fontes fetch, 25 claims
verificados adversarialmente, 20 confirmados / 5 mortos) + NotebookLM CLI (notebook
`cec5e6bf`, 46 fontes ready) + spec oficial ElevenLabs Music (WebFetch — context7/ref
sem creditos) + `/cs:pulse` (web; reddit bloqueado por user-agent).

## Veredito de uma linha

Libs comerciais tratam **mood como eixo de 1a classe** (paralelo a genero/tema), ancorado
no **modelo circumplexo de Russell (valence × arousal)**; a alavanca pra virar mood em
prompt e: **arousal → BPM/energia/densidade**, **valence → modo (maior/menor)/harmonia**.
Prompt de musica-gen bom e **hierarquico**: papel+genero+mood primeiro, depois
instrumentacao e specs tecnicas. BED de anuncio tem 3 invariantes proprias:
`instrumental only` + `sits under voiceover` + `clean ending`.

## 1. Como as libs comerciais taxonomizam mood

- **Eixo de 1a classe.** Epidemic Sound organiza em 3 eixos paralelos (Genres / Moods /
  Themes), ~33-34 moods nomeados, exposto por **Partner API** (`moods` endpoint:
  `happy`, `epic`, `relaxing`) com metadata `bpmMin/bpmMax`, `hasVocals`, `isExplicit`;
  busca combina mood+genre+BPM com **AND logic**. Artlist filtra por Genre / Mood / Video
  Theme / Instrument. [conf: high]
- **Vocabulario comercial** (3 grupos): estados emocionais (Happy, Sad, Angry, Hopeful,
  Romantic, Sentimental), tensao (Suspense, Fear, Scary, Dark, Mysterious), cinetica
  (Running, Chasing, Marching, Busy & Frantic). Artlist paralelo: Happy, Tense, Romantic,
  Uplifting, Playful, Dark, Sexy. [conf: high]
- **Ad e bucket proprio.** Epidemic tem tema dedicado "Ads, Promos & Trailers" (Elegant
  Ads, Badass Ads, Feelgood Trailers). Use-case e dimensao separada do mood. [conf: high]
- **Descritor refinado > cru.** Supervisores preferem Gleeful/Triumphant/Content vs
  Melancholy/Wistful/Resigned em vez de Happy/Sad blunt. [conf: medium — 1 fonte blog]

### Scaffold academico (informa design, NAO colar como palavra de anuncio)

- **Russell circumplex:** valence (desagradavel↔agradavel) × arousal (calmo↔agitado);
  estende p/ 3o eixo potency/dominance. 4 quadrantes:
  - **HV+HA** (alta energia positiva): Excitement, Joy, Triumphant, Euphoric
  - **HV+LA** (baixa energia positiva): Calm, Serene, Content, Tender
  - **LV+HA** (alta energia negativa): Anger, Fear, Tense, Menacing
  - **LV+LA** (baixa energia negativa): Sad, Melancholic, Wistful, Somber
- **Thayer variant:** eixos diagonais tension × energy.
- **MIREX 5 clusters / EMOPIA 4Q** = rotulos de pesquisa, nao vocab comercial.

## 2. Mapa mood → parametros musicais (a alavanca)

Features de audio mapeiam previsivelmente nos eixos — e ISSO vira BPM/key/instrumentacao:

| Eixo                            | Correlato musical                                       | Uso no prompt                            |
| ------------------------------- | ------------------------------------------------------- | ---------------------------------------- |
| **Arousal** (energia)           | tempo, pitch, loudness, timbre, densidade               | escolhe **BPM** + densidade instrumental |
| **Valence** (positivo/negativo) | **modo** (maior=bright/happy, menor=dark/sad), harmonia | escolhe **key/mode**                     |

Escada de BPM (Suno glossary): Adagio 66-76 · Andante 76-108 · Moderato 108-120 ·
Allegro 120-168 · Presto 168-200. Numero literal (`108 BPM`) ancora melhor que "mid-tempo".

## 3. Estrutura de prompt validada (hierarquica, 7 componentes)

Ordem que converge em ElevenLabs + Suno + NotebookLM:

1. **Papel/use-case:** "music bed" / "underscore" / "background" — crava hierarquia
2. **Genero + era:** especifico ("2020s corporate pop" > "pop")
3. **Mood primario + valence:** "uplifting" / "melancholic" / "sophisticated"
4. **Tempo + arousal:** BPM numerico + descritor de pace ("108 BPM, steady drive")
5. **Instrumentacao com papel:** "warm piano lead", "sparse synth pads", densidade
6. **Constraints de producao:** "instrumental only, no vocals" (+ key/mode)
7. **Ending/movimento:** "clean ending" / "fade out" / (Udio: "a niente", "subito")

### Invariantes de BED publicitario/broadcast

- **Sob voiceover:** "minimalist", "sparse instrumentation", "no lead melody",
  "limit midrange clutter" — deixa faixa livre pro narrador.
- **Clean ending:** tags `[Outro]` `[Fine]` `[Sudden End]`; Udio "a niente".
- **Duracao:** ElevenLabs = exato via `music_length_ms` (30000 = 30s). Suno/Udio geram em
  segmentos (~32s/2m). Libs classificam: "Links" 15-20s, "Stings" <7s.
- **Negativa:** NAO confiavel inline ("no drums"). Usar **exclude field** (Suno) /
  `negative_global_styles` (ElevenLabs composition plan).

## 4. Biblioteca mood → prompt (colavel nos packs Muntu)

Template base:

```
"[papel] bed, [BPM] BPM, [mood+valence], [key/mode], [instrumentacao c/ papel],
 instrumental only, sits under voiceover, [ending]"
```

| Pack / mood                 | Quadrante V/A | BPM     | Modo  | Prompt (verbatim, colavel)                                                                                                                                                                                                                         |
| --------------------------- | ------------- | ------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Corporate/motivational**  | HV·mid-A      | 100-115 | maior | `Corporate underscore bed, 108 BPM, professional and optimistic, major key, clean acoustic guitar, warm piano, soft percussion, subtle synth pads, instrumental only, sits under voiceover, clean ending.`                                         |
| **Uplifting/inspirational** | HV·HA         | 110-125 | maior | `Inspirational corporate bed, 120 BPM, hopeful and building, major key, piano ostinato, soaring strings, light claps and drums, instrumental only, no lead melody, uplifting build to a clean end.`                                                |
| **Emotional/cinematic**     | LV·low→build  | 75-90   | menor | `Emotional cinematic bed, 85 BPM, bittersweet and introspective, minor key, delicate piano, warm string section, subtle brass swell, instrumental only, sparse under voiceover, builds from quiet contemplation to a gentle climax, clean ending.` |
| **Energetic/upbeat**        | HV·HA         | 120-135 | maior | `Upbeat commercial bed, 128 BPM, energetic and feel-good, major key, driving drums, punchy bass, bright electric guitar, hand claps, instrumental only, no vocals, sits under voiceover, clean end.`                                               |
| **Natal/seasonal**          | HV·warm       | 90-120  | maior | `Christmas holiday bed, festive and warm, major key, sleigh bells, orchestral strings, glockenspiel, warm piano, instrumental only, joyful and traditional, sits under voiceover, clean ending.`                                                   |
| **Dia das Maes/tender**     | HV·LA         | 75-90   | maior | `Tender emotional bed, 80 BPM, warm and heartfelt, major key, gentle piano, soft nylon guitar, warm strings, instrumental only, sparse under voiceover, clean ending.`                                                                             |
| **Tense/suspense**          | LV·HA         | 90-120  | menor | `Suspense underscore bed, 100 BPM, tense and ominous, minor key, pulsing low strings, sparse piano stabs, subtle percussion, instrumental only, limit midrange clutter, sudden end.`                                                               |

Exemplos oficiais verbatim (referencia de fraseado): ElevenLabs — `"Track for a high-end
mascara commercial. Upbeat and polished. Voiceover only."` / `"Corporate background,
108 BPM, professional and optimistic, clean acoustic guitar, light piano, gentle
percussion, no vocals, uplifting, presentation ready."`

### Aplicacao no Muntu (director.pack_por_clima)

Cada pack ganha campo `climas` (ja existe) + campo novo `prompt_template` por papel de
stem. O VLM devolve label de clima → `director` faz lookup → preenche `[BPM]`/`[key]` a
partir do quadrante V/A → monta o prompt do `base_bed.py`. Ex. pack JSON:

```json
{
  "id": "corporate",
  "climas": ["corporate", "optimistic", "professional"],
  "bpm": 108,
  "mode": "major",
  "prompt_template": "Corporate underscore bed, {bpm} BPM, professional and optimistic, {mode} key, clean acoustic guitar, warm piano, soft percussion, subtle synth pads, instrumental only, sits under voiceover, clean ending."
}
```

## Caveats (do deep-research — nao virar dogma)

- **"measurably changes output" = fraseado de vendor** (ElevenLabs/Suno/fal.ai), NAO
  estudo controlado independente. key/BPM ajudam consistencia, mas magnitude nao medida.
- **5 claims MORTOS na verificacao:** (a) "prompt use-case+mood-adjective supera lista de
  atributos" — refutado; (b) schema fixo primary/secondary tag NAO e padrao de industria
  (vem de 1 blog); (c) schema Suno de 6 componentes fixo — refutado. Trate a tabela acima
  como **ponto de partida testavel, nao receita provada**.
- Contagens de mood (~33-34 Epidemic) sao de paginas de vendor que driftam — re-scrapear
  antes de hardcodar.
- MIREX/EMOPIA = labels academicos, nao colar como palavra de anuncio.

## Open questions

- Vocab especifico de **APM, Musicbed, Universal Production Music** — nenhum claim
  sobreviveu; mapa generaliza de Epidemic + Artlist so.
- **Lookup VLM-mood → palavra-de-lib → fraseado de prompt** na granularidade certa (o
  gap central do Muntu — [[sound-design-ia-2026-06]] memoria "mood precisa assistir").
  GLM-4.6V da "comedic"/"romantic"; falta a tabela de traducao pro descritor de prompt.
- Benchmark independente (nao-vendor) de quanto key/BPM/mode muda saida de ElevenLabs
  Music V2 / Suno / Udio.
- Presets canonicos de genero+mood+BPM+instrumentacao por tipo de campanha — a tabela
  acima e hipotese, precisa A/B na tool.

## Fontes (2026-07-07)

- Epidemic Sound moods — https://www.epidemicsound.com/music/moods/
- Epidemic Partner API — https://developers.epidemicsite.com/docs/music/
- Epidemic Ads/Promos/Trailers — https://www.epidemicsound.com/music/themes/ads-promos-trailers/
- Artlist catalog browse — https://help.artlist.io/hc/en-us/articles/29596157272221-Browsing-Artlist-s-Music-catalog
- Artlist corporate — https://artlist.io/royalty-free-music/categories/corporate
- ThatPitch mood/emotion library selection — https://thatpitch.com/blog/how-mood-and-emotion-drive-library-selection/
- ElevenLabs Music best-practices — https://elevenlabs.io/docs/overview/capabilities/music/best-practices
- ElevenLabs Music v2 — https://elevenlabs.io/blog/introducing-music-v2
- fal.ai Eleven Music prompt guide — https://fal.ai/learn/biz/eleven-music-prompt-guide
- Suno glossary/tempo — https://help.suno.com/en/articles/9010177
- Suno prompt formula/tags — https://hookgenius.app/learn/suno-prompt-guide-2026/ · https://hookgenius.app/learn/suno-style-tags-guide/
- Soundverse prompt structure — https://www.soundverse.ai/blog/article/how-to-structure-prompts-for-suno-ai-music-generation-0402
- musicsmith ad-bed best-practices — https://musicsmith.ai/blog/ai-music-generation-prompts-best-practices
- imagine.art 52 prompts por mood/use-case — https://www.imagine.art/blogs/ai-music-prompts
- Google music-gen prompt guide — https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/music/music-gen-prompt-guide
- Yang & Chen Music Emotion Review — https://people.ict.usc.edu/~gratch/CSCI534/Readings/Yang-Music-Emotion-Review.pdf
- EMOPIA (4Q V-A) — https://arxiv.org/pdf/2108.01374
- NotebookLM notebook `cec5e6bf` (46 fontes ready) — Circumplex/Thayer + prompt structure + ad conventions

## Log

- 2026-07-07 — Criada. Pesquisa paralela 4-canais (deep-research + NotebookLM + ElevenLabs
  spec + pulse). Deliverable = tabela mood→prompt + caveats de verificacao. Proximo:
  transformar em campo `prompt_template` nos `packs/*.json` do repo muntu-score e A/B testar.
