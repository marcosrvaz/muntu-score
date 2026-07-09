# Composition Plan — design (cama com arco)

> Evolução da cama: de **textura plana** (Stable Audio, 1 prompt) pra **música com
> estrutura** (intro → build → clímax → outro) que **segue o arco do filme** e
> **respeita os cortes**. Motor = ElevenLabs Music V2 `composition_plan` (seções com
> duração + estilo). O director monta o plano a partir da análise do vídeo.

## Os 3 pedidos que isto resolve

1. **Intro / final** — música tem começo e fim, não loop cru.
2. **Respeitar o mood** — cada seção herda o clima da cena (via VLM) + gênero do pack.
3. **Respeitar os cortes** — as fronteiras de seção caem em cortes reais; os acentos
   (stems) continuam travando na grade por cima.

## Por que ElevenLabs e não Stable Audio

- **Stable Audio 2.5** = 1 prompt → 1 textura. Sem controle de seção/timing. Dá pra pedir
  "with intro and outro" no texto, mas não crava duração nem sequência.
- **ElevenLabs Music V2 `composition_plan`** = até 30 seções, cada uma com nome, estilos
  próprios, `duration_ms` (3–120s) e lyrics. Flag `respect_sections_durations=true` obriga
  o modelo a bater a duração de cada seção → **alinhamento ao filme**. Total 3s–10min.

Decisão de custo muda: a assinatura ElevenLabs agora **compra uma feature** (estrutura),
não só qualidade de som. Stable Audio segue como fallback pra cama sem arco.

## Schema do composition_plan (o que geramos)

```json
{
  "positive_global_styles": ["<gênero>", "<instrumento>", "<mood>", "instrumental"],
  "negative_global_styles": ["vocals", "<o que evitar>"],
  "sections": [
    {
      "section_name": "Intro",
      "positive_local_styles": ["sparse", "gentle", "establishing"],
      "negative_local_styles": ["full drums"],
      "duration_ms": 5920,
      "lyrics": ""
    }
    // ... build, climax, outro
  ],
  "respect_sections_durations": true
}
```

- **global** = a identidade da faixa inteira (vem do pack + clima dominante).
- **local** (por seção) = como aquela seção difere (energia, densidade).
- `lyrics: ""` sempre — instrumental (brand-safe pra ad).

## Mapeamento filme → plano (o algoritmo do director)

Entrada: `cortes` (analyzer), `cenas` com `clima`+`energia` (VLM/mood), `duracao`, `pack`.
Saída: `composition_plan` + os `acentos` de sempre (que continuam por cima).

### [1] Estilos globais

`positive_global_styles` = `pack.bed_estilo` quebrado em lista + `clima_dominante` (VLM) +
`"instrumental"`. `negative_global_styles` = `["vocals"]` + `pack.negativos` (ex: "distortion").

### [2] Segmentar o filme em seções (não 1 por corte)

Corte ≠ seção. Seção mínima = 3s (limite ElevenLabs). Agrupa cortes em **3–5 seções** por
regime de energia:

- Fronteiras de seção = os cortes onde a **energia muda mais** (via VLM). Sem VLM: cortes
  que dividem a duração em blocos ~iguais, respeitando 3s mín.
- Merge de seções < 3s; split de seções > 120s.
- **Sempre:** 1ª seção = Intro, última = Outro.

### [3] Localizar o clímax

Seção de clímax = a que contém o **pico de energia** (VLM) — ou, sem VLM, a de maior
**magnitude de corte** (curva de novidade — o corte mais forte, mesmo critério que o
director já usa pra acento forte). É onde a arquitetura já pensa. Ex: no ad completo, o
**casamento** = pico → seção Climax ali.

### [4] Estilos locais por papel de seção

| Seção  | positive_local_styles                               | papel  |
| ------ | --------------------------------------------------- | ------ |
| Intro  | sparse, gentle, establishing, soft entrance         | abre   |
| Build  | developing, adding layers, warming, rising energy   | cresce |
| Climax | full arrangement, emotional peak, soaring, powerful | pico   |
| Outro  | resolving, winding down, gentle ending, fade        | fecha  |

Templates de arco vivem no **pack** (campo novo `arco`) — refináveis no teu ouvido.

### [5] Durações = timestamps reais do filme

`duration_ms` de cada seção = span real entre as fronteiras escolhidas (em ms).
`respect_sections_durations=true` força o alinhamento. Soma = duração do vídeo.

### [6] Acentos por cima (coexistência)

O composition_plan dá o **arco** (bed). Os **acentos** (stems quantizados) continuam
disparando nos cortes por cima — frame-precisos. Bed = estrutura+mood; stems = hits no
corte. Os dois juntos = arco + cortes + mood.

## Exemplo trabalhado — Pringles 16s

Cortes reais: `[1.63, 2.67, 5.92, 6.8, 9.22, 10.18, 11.97, 14.14, 15.85]`, dur 16.0s.
Mood (assistido): história de amor nostálgica (ref. Lionel Richie "Stuck On You").

Plano de 3 seções (cada ≥3s, fronteiras em cortes reais):

```json
{
  "positive_global_styles": [
    "warm nostalgic soft rock",
    "soul pop",
    "romantic",
    "mellow electric guitar",
    "warm Rhodes piano",
    "retro 1980s",
    "instrumental"
  ],
  "negative_global_styles": ["vocals", "aggressive", "distortion"],
  "sections": [
    {
      "section_name": "Intro",
      "positive_local_styles": ["sparse", "gentle", "soft guitar", "establishing"],
      "negative_local_styles": ["full drums"],
      "duration_ms": 5920,
      "lyrics": ""
    },
    {
      "section_name": "Build",
      "positive_local_styles": ["developing", "warm Rhodes enters", "rising", "tender"],
      "negative_local_styles": [],
      "duration_ms": 6050,
      "lyrics": ""
    },
    {
      "section_name": "Climax",
      "positive_local_styles": ["full warm arrangement", "emotional peak", "heartfelt", "soaring"],
      "negative_local_styles": [],
      "duration_ms": 4030,
      "lyrics": ""
    }
  ],
  "respect_sections_durations": true
}
```

- Intro 0–5.92s (fronteira no corte 5.92) · Build 5.92–11.97s (corte 11.97) · Climax
  11.97–16.0s.
- Acentos suaves continuam em 1.63/2.67/6.8/9.22/10.18/14.14/15.85 quantizados na grade.

**No ad completo de 30s** o arco fica óbvio: Intro (festa) → Build (escola/encontro) →
**Climax (casamento)** → Outro (resolução). 4 seções, clímax no pico emocional real.

## Como o pack alimenta (campos novos)

```json
{
  "nome": "romantico",
  "bpm_range": [90, 120],
  "generos": ["warm nostalgic soft rock", "soul pop", "retro 1980s"],
  "negativos": ["aggressive", "distortion"],
  "arco": {
    "Intro": ["sparse", "gentle", "establishing"],
    "Build": ["developing", "warming", "rising"],
    "Climax": ["full arrangement", "emotional peak", "soaring"],
    "Outro": ["resolving", "gentle ending"]
  }
}
```

`bed_estilo` (string) segue servindo o Stable Audio (sem arco); `generos`/`arco` (novos)
servem o composition_plan do ElevenLabs.

## O que muda no código

- `director.py`: nova função `composition_plan(brief, pack)` → devolve o dict acima
  (segmenta seções, acha clímax, monta estilos). Puro Python, testável.
- `base_bed.py`: `_gera_elevenlabs` passa a aceitar `composition_plan=` (em vez de só
  `prompt`). Provider `elevenlabs` vira o caminho "com arco".
- `pipeline.py`: se provider=elevenlabs e pack tem `arco` → usa composition_plan; senão
  cai no prompt simples (Stable Audio).
- packs ganham `generos`/`negativos`/`arco`.

## Alinhamento de BPM — warp pós-geração (ajuste fino tipo Ableton)

O BPM da grade (dos cortes) entra nos `positive_global_styles` como hint (`"127 BPM",
"steady tempo"`) — mas **o modelo só aproxima, não crava**. Pra "melhor aproximação
possível", uma etapa de **warp pós-geração** trava o tempo real do bed na grade — igual
o warp do Ableton Live. É o caminho barato não-explorado da pesquisa (librosa beat-track +
elastic warp).

### Camadas (do barato ao caro)

1. **Hint de prompt** (feito) — BPM nos estilos globais. Grátis, aproxima.
2. **Warp global** (próximo chunk) — detecta o tempo real do bed (`librosa.beat.beat_track`)
   e time-stretch o bed inteiro pra `tempo == bpm_grade`. Um fator só. ffmpeg
   `rubberband` (build já tem `librubberband`). **Cap de stretch ≤ ~6%** (pesquisa) — se o
   desvio for maior, provável erro de oitava (ex: 64 vs 128) → corrige a oitava, não
   estica demais. Preserva pitch.
3. **Warp elástico / beat-level** (pro, deferido) — alinha cada batida do bed a cada linha
   de grade (hit-points tipo Ableton/Cubase). Complexo. Só se o warp global não bastar.

### Princípio (não muda)

O warp é **best-effort no bed** (atmosfera). Quem carrega o **sync exato** continua sendo
os **stems/acentos** quantizados na grade (frame-precisos). O warp só melhora a coerência
groove-do-bed ↔ acentos; nunca é a fonte do sync. Frame-lock full-track automático segue
FORA (fronteira R&D — o elefante).

### Onde entra no pipeline

`analyzer → mood → director(plano + composition_plan) → base_bed(gera) → **warp p/ grade** →
stems → mix → mux`. O warp roda entre a geração do bed e o overlay dos acentos.

## Decisões abertas (pra ti)

1. **Nº de seções alvo** — 3–5. Pro 16s, 3. Pro ad de 30s, 4 (com Outro).
2. **Clímax automático precisa de VLM** (pico de energia). Sem VLM, uso magnitude de corte
   (aproximação). Ligar VLM (`REPLICATE_API_TOKEN`)?
3. **`respect_sections_durations=true`** alinha ao filme, mas a doc do ElevenLabs avisa que
   pode custar qualidade vs `false` (que preserva só a duração total). Alinhamento vs som —
   qual priorizar? (Recomendo true; é o ponto do produto.)
4. **Confirma o provider pago** — composition_plan é ElevenLabs. Precisa plano com Music API.

```

```
