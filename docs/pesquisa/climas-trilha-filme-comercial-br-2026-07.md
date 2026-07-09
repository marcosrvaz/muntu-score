---
tipo: pesquisa
data: 2026-07-07
url: multi-fonte (ver secao Fontes)
---

# Climas na trilha de cinema e comercial (foco Brasil) — jul/2026

Pesquisa **organica** de clima/emocao como a **musica para filmes e a publicidade de
verdade** trata — NAO ferramentas de IA de musica (isso e camada downstream, ver
[[moods-broadcast-prompt-2026-07]]). Objetivo: dar ao [[caminhos/ia-aplicada|Muntu Score]]
uma taxonomia de clima ancorada no craft real de trilha, com lente brasileira.
Irma de [[sound-design-ia-2026-06]] e [[geradores-musica-ia-2026-06]]. Feedback que
originou o alvo: [[pesquisa-clima-ancorar-musica-filme]].

**Metodo (4 canais, expandido):** `/deep-research` v2 (18 claims verificados 3-0;
synthesize morreu 2x no limite de gasto → **sintese feita a mao** aqui) + NotebookLM CLI
(notebook `ffada1b0` "Climas trilha filme+comercial BR", 35 fontes web + 6 videos de craft
ingeridos, 3 asks) + `/yt-search` (curadoria de video de craft) + exa (ativado, so carrega
proxima sessao). Fonte BR veio via NotebookLM (Google-backed alcanca PT); WebSearch do
deep-research e US-only, serviu de backbone internacional.

## Veredito de uma linha

Clima na trilha real **nao e uma tag** — e um **processo**: o adjetivo ("tenso", "epico")
**subdetermina** a musica; o craft carrega **modo + andamento + harmonia + instrumentacao

- arco**. No Brasil ha duas escolas proprias: **estetica "magra e esguia"** no cinema
  (piano+cello, minimalismo — Central do Brasil) e **jingle "chiclete"** na publicidade
  (memoria afetiva por rima/metrica — Pipoca e Guarana, Bamerindus). Licao pro Muntu: o pack
  tem que carregar a **convencao musical inteira** por clima, nao so a palavra.

## 1. Como o clima nasce (processo, nao lista)

- **Spotting session:** reuniao diretor↔compositor onde se alinha a **intencao emocional**
  cena a cena — onde entra musica, e que funcao narrativa/emocional ela cumpre — ANTES de
  compor. [deep-research, adrianwalther]
- **Vocabulario compartilhado:** diretor comunica com **adjetivo simples** ("danceable",
  "frenetic", "peaceful", "sadder", "faster"), nao jargao tecnico. Cria-se uma lingua
  comum. [filmindependent]
- **⚠️ O adjetivo SUBDETERMINA (achado central):** "tensao" vira dissonancia OU
  instabilidade ritmica OU silencio OU harmonia nao-resolvida OU cordas agudas suaves — a
  palavra sozinha nao fecha a partitura. Adjetivo puro ("dark", "epic", "intimate") e o
  **nivel MENOS util** de brief; ref track com timecode + arco emocional + instrumentacao +
  hit points e o que funciona. [toolsforfilm]
- **Prova concreta do mapeamento:** a MESMA melodia lida como "derrotado" vira
  "determinado" so trocando **menor→maior** e **lento→um pouco mais rapido**. [toolsforfilm]

> **Implicacao Muntu:** o VLM devolve um adjetivo de clima. Isso e o brief mais fraco.
> O pack precisa traduzir o adjetivo em modo+BPM+instrumentacao (secao 2) senao repete o
> problema "mood idiota" ([[muntu-biblioteca-de-climas]]).

## 2. Taxonomia de clima → convencao musical (o mapa)

Sintese deep-research (claims 9,11,15,16,17) + NotebookLM ask 1. Cada clima = pacote de
convencoes reais de scoring:

| Clima                              | Andamento                              | Modo                                | Harmonia                                                               | Instrumentacao                                                             |
| ---------------------------------- | -------------------------------------- | ----------------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **Alegria / calor / conforto**     | medio-rapido                           | **maior**                           | consonante, diatonica                                                  | acustico — violao, piano solo, cordas quentes                              |
| **Tristeza / melancolia**          | lento (60-80 BPM)                      | **menor**                           | simples, resolucoes suaves                                             | **piano + violoncelo** ("magra e esguia"), madeiras                        |
| **Tensao / suspense / perigo**     | percepcao alterada por ostinato/graves | **atonal** ou instavel (Locrio)     | **dissonante** (2a menor, 5a diminuta, Shepard tone, "raise the root") | graves, sintetizadores, metais pesados, cordas staccato                    |
| **Misterio / imaginacao / wonder** | medio-lento (flutua)                   | **Lidio** ("magico"), tons inteiros | tríades aumentadas, "leading shape" nao-resolvida                      | harpa (arpejo p/ flashback), madeiras, texturas leves de cordas            |
| **Heroico / epico / acao**         | rapido, ritmico                        | maior/hibrido                       | 4a aberta, "flat-6 sobre 1" (super-heroi)                              | **metais** (trompete/trompa), percussao orquestral, grande naipe de cordas |
| **Neutro / limbo / transicao**     | medio (76-120 BPM)                     | ambiguo (sus chords)                | 4as, drones/pedais                                                     | texturas sutis, synth de fundo, "apoio"                                    |

Modos extras (deep-research 17): **Dorico** = antigo/melancolico; **Frigio** = pavor.
Andamento lento 60-80 BPM = gravidade emocional (le como tensao/solenidade/poder conforme
o contexto). **Arousal** (intensidade) sobe com **tempo rapido + volume alto**; **valence**
(positivo/negativo) vem do **modo**.

## 3. Convencao por tipo de comercial

NotebookLM ask 2 + deep-research (5 funcoes, NeedScope). As **5 funcoes** que a musica
cumpre num ad (compositor publicitario trabalha a partir delas): branding/mnemonico ·
storytelling · resposta emocional direta · identificacao demografica · fonte/diegetico.
[newmusicusa]

| Tipo                              | Clima-alvo                         | Convencao musical                                                                                 | Caso BR real                                                                    |
| --------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **Corporativo/institucional**     | confianca, perenidade, otimismo    | orquestral/acustico, andamento constante                                                          | Banco Nacional (Natal com maestro/orquestra)                                    |
| **Alimento/CPG (jingle)**         | alegria, valence positiva, fixacao | rima + metrica simples + silaba forte que "pipoca"                                                | Guarana Antarctica "Pipoca e Guarana", Big Mac, Parmalat                        |
| **Banco/financeiro**              | seguranca, continuidade            | refrao de fixacao, andamento equilibrado                                                          | Poupanca **Bamerindus** ("o tempo passa, o tempo voa")                          |
| **Tecnologia**                    | futurista, atmosferico             | **sintetizadores**, texturas digitais                                                             | (ref intl Hans Zimmer; contextualizar BR)                                       |
| **Automotivo**                    | acao, aventura, dinamismo          | segue o tom narrativo/cinematografico                                                             | Chevrolet (branded entertainment c/ Netflix); Carbel/Cetibras (jingle regional) |
| **Luxo**                          | sofisticacao, elegancia            | _(claim nao sobreviveu — verificacao cortada no limite; hipotese: lento, minimal, timbre "caro")_ | —                                                                               |
| **Natal**                         | reuniao familiar, nostalgia        | orquestral, sinos, coral                                                                          | Banco Nacional, Coca-Cola (uniao familiar)                                      |
| **Dia das Maes / drama familiar** | tristeza doce, saudade             | **lento (60-76 BPM), piano+violoncelo**, minimalismo                                              | estetica de _Central do Brasil_                                                 |

## 4. Lente Brasil (o diferencial)

NotebookLM ask 3 + deep-research (claims 5,6,7,8). Duas escolas proprias de construir emocao:

1. **Cinema — realismo "magro e esguio":** orquestracao reduzida (parte por orcamento)
   virou **estetica de minimalismo**; **piano e violoncelo** no centro pra clima
   melancolico/intimo. Espelha dureza social, foge do sentimentalismo Hollywood.
2. **Publicidade — jingle "chiclete" / memoria afetiva:** fixacao por melodia cativante +
   rima + encaixe de vogais. Transicao de "anuncio cantado" → trilha que "precisa parecer
   musica" (emocao menos explicita). No BR a **intencao musical e decidida no brief pela
   agencia**, antes da producao — nao e etapa tardia. [meioemensagem]

**Instrumentacao tipica BR:** violao (raiz — Noel Rosa improvisando ao vivo), saxofone,
rabeca (regional/nordestino), + orquestra em campanha institucional. **Cinema Novo** usou
idioma regional como estrategia: repente/cordel nordestino, samba suburbano carioca.

**Compositores/maestros citados:**

- Cinema: **Antonio Pinto & Jaques Morelenbaum** (Central do Brasil), **John Neschling**
  (Pixote, O Beijo da Mulher Aranha), **Villa-Lobos**, **Radames Gnattali** (une classico +
  popular), **Francisco Mignone**, **Guerra Peixe**, Lyrio Panicali, Erlon Chaves.
- MPB no cinema: Edu Lobo, Egberto Gismonti, Caetano Veloso, Francis Hime, Lo Borges.
- Jingle/publicidade: **Sergio Campanelli** (MCR), **Miguel Gustavo**, Wilson Simoninha.
- Generos-base: bossa nova, samba, choro, MPB, regional/nordestino.

## 5. Frameworks de sonic branding (como marca escolhe clima)

- **Kantar NeedScope:** posicionamento de marca por **emocao universal** — 6 espacos
  emotivos (color-coded) como territorios; casa a musica ao espaco da marca. **NeedScope
  Music** posiciona uma faixa analisando ritmo+tempo+pitch+timbre+arranjo+melodia juntos.
- **Audio mood board:** escolher trilha = evocar a MESMA emocao do posicionamento, capturada
  em termos **musicais E emocionais** (nao so adjetivo). [kantar]
- **Assinatura sonica:** funciona como logo — assina toda comunicacao da marca (vinheta,
  arranjos variados, som de produto), nao so o comercial. [meioemensagem]

## 6. Camada academica (exa) — a ciencia por tras do mapa

Busca exa em 4 vetores (film-scoring · valence/arousal em music cognition · musica em
publicidade · trilha cinema BR), filtro `research paper`, peer-reviewed priorizado. Isto
**ancora a tabela da secao 2 em evidencia empirica com effect sizes** e mostra onde o achado
"adjetivo subdetermina" tem base cientifica: emocao musical e um espaco continuo, nao uma tag.

**Labs de topo que apareceram** (o pedido: melhores universidades): **UC Berkeley** (Cowen/
Keltner, emotion lab) editado por **Duke/Durham** (Purves) na PNAS; **McGill — Schulich School
of Music** (McAdams, timbre/percepcao); **McMaster — MAPLE Lab** (Schutz, cue-weighting);
**Max Planck** (Empirical Aesthetics + Human Development); **Macquarie** (W.F. Thompson); **UCL**
(musica em ad). _Berklee **nao apareceu nestas buscas** (4 queries exa `research paper`) — a
ciencia empirica de mood→feature saiu de labs de psicologia/percepcao (acima), nao do
conservatorio; nao e prova de que Berklee nao pesquise, so que nao rankeou aqui. Juslin,
Gabrielsson, Eerola, Vieillard aparecem so como referencia citada dentro dos papers._

### 6.1 A base: modelo valence × arousal com pesos de regressao (a espinha da secao 2)

Music cognition organiza emocao musical em **2 dimensoes** que capturam a maior parte da
variancia: **valence** (positivo↔negativo) e **arousal** (intensidade/ativacao). O mapeamento
canonico — **modo → valence; andamento/densidade ritmica → arousal** — nao e folclore, tem
peso medido:

- **Schutz/MAPLE Lab (McMaster) 2021** — 48 trechos do Bach WTC, regressao de 3 cues:
  **modo explica 38,9% da variancia de valence** (o maior), attack rate 14,8%, pitch 3,1%
  (modelo = **81,2%** da valence). Pra **arousal, attack rate explica 63,2%**, modo so 3,5%.
  Pesos: valence **cai −0,933 ao trocar maior→menor**, sobe +0,248 por ataque/seg, +0,102 por
  semitom; **arousal = 0,474 × attack rate**. → o eixo maior/menor é a alavanca #1 de valence;
  densidade ritmica é a #1 de arousal. Cravanca a secao 2.
- **Gu et al. 2026 (Scientific Reports)** — deep learning interpretavel, dataset DEAM (1.802
  trechos), coeficientes β padronizados: **Tempo → arousal β=.55***; **Harmonic Complexity →
  valence β=−.43*** (dissonancia derruba valence); Spectral Flux → arousal .48; Brightness →
  valence .31. Sintese: **"fast tempi and bright timbres... high arousal and positive valence,
  while slow tempi and minor modes... low arousal and negative valence."**
- **Hofbauer & Rodriguez 2023 (Intl. J. of Psychology)** — 102 pessoas, 20 rapidas (>110 BPM)
  vs 20 lentas (<90 BPM): tempo → arousal β=.20; relacao valence↔arousal **quadratica**
  (valence extremo, + OU −, puxa arousal alto). Achado-chave pro **leigo do ad**: **"tempo
  cues appear powerful enough to outweigh mode... in non-musicians"** — pro publico leigo, BPM
  pesa MAIS que modo na leitura de valence.
- **Cohrdes et al. 2018 (Max Planck)** — "high tempo + major → positive valence; lower tempo +
  minor → negative valence"; **loudness + timbre = preditores confiaveis de arousal alto**;
  loudness/timbre **variaveis** → percebido como negativo E excitado. Confirma valence menos
  confiavel que arousal.
- **McAdams/McGill (Schulich) 2021, cross-cultural timbre** — valence positivo ↔ energia
  espectral grave + alta variacao espectral + notas curtas de ataque agudo (staccato/pizz) +
  dynamic range; **energy arousal ↔ brilho + spectral flux (a feature #1)**; tension arousal ↔
  agudo/ruidoso. **"Cultural background influences affect perception more than musicianship"**
  → base cientifica pra **lente BR (secao 4)**: instrumentacao regional muda o afeto, e cultura
  supera treino.
- **Caveat forte — Cowen/Keltner (UC Berkeley) PNAS 2020, ed. Duke/Durham** — **13 dimensoes**
  organizam a experiencia musical (triumphant, awe...), e valence/arousal sao **"higher-order
  inferences", nao building blocks**; 18 categorias discretas preservam-se melhor entre
  culturas (r=.75) que valence. → o pack Muntu **nao deve colapsar clima em "positivo/intenso"**;
  manter os climas discretos da secao 2, que carregam textura que o 2D perde.

### 6.2 Especifico de trilha de filme

- **Arousal e perceptualmente mais consistente que valence** (com ressalva, ver abaixo).
  Crocker & Fazekas 2025 (FME-24, **300 trilhas profissionais 2002-2024**): "chord types
  influenced arousal more strongly than pitch"; **"arousal was generally perceived more
  consistently than valence."** Cohrdes/Max Planck cita Eerola no mesmo sentido; Berkeley da
  arousal r=.81 vs valence r=.75 cross-cultural (lean fraco). → a INTENSIDADE do clima e mais
  robusta; o SINAL (alegre↔triste) e o que mais escapa — o erro Pringles
  ([[muntu-mood-precisa-assistir]]). **⚠️ Ressalva honesta:** NAO e que valence seja
  intrinsecamente imprevisivel — o modelo de 3 cues do Schutz explica **valence a 81,2%** vs
  **arousal a 49,8%** (cues predizem valence MELHOR). O ponto real: a variancia de valence
  **concentra no cue MODO** (38,9%), e modo e (a) o cue mais dificil de inferir de pixel de
  video e (b) cultura-dependente (McGill: cultura>treino). Logo valence e fragil **neste
  pipeline especifico** (VLM le video), nao no ouvido humano em geral. Priorizar leitura de
  valence pela CENA, nao pelo frame.
- **Uma feature acustica carrega clima E cena ao mesmo tempo.** Nature Sci. Reports 2025
  (N=121): **tempo e loudness** alimentam tanto emocao (happiness/sadness) quanto **propriedades
  narrativas** (scene brightness, character role), contribuicoes distintas e nao-sobrepostas.
  → base empirica pro [[muntu-sfx-cena-nao-mood]]: o mesmo material sonoro fala de mood e de
  cena; separar os dois sinais e correto.
- **Reacoes a pitch/ritmo/orquestracao em parte inatas** (Lascurain 2016, UC eScholarship);
  **timbre como ferramenta central** (Bagnall 2014, Huddersfield — analise de Zimmer).

### 6.3 Especifico de publicidade (reforca a secao 3)

- **Modo maior + andamento rapido ampliam intencao de compra.** Liu, Abolhasani & Hang 2022
  (European J. of Marketing): "Major mode music strengthens the effect of positive brand
  attitudes on purchase intention... major mode music with a fast tempo can further
  strengthen" isso. → modo+tempo **moderam conjuntamente** a conversao.
- **Valence divide o RESULTADO: recall vs conversao.** Dogaru, Furnham & McClelland 2024
  (Acta Psychologica, UCL): "music with a quicker tempo and smooth rhythm as happy... low
  pitch and slower tempo as sad"; **musica triste ↑ reconhecimento de marca e recall**;
  **musica alegre ↑ intencao de compra**. → escolher o clima do ad e escolher o objetivo
  (lembrar vs comprar), nao so o humor.
- **Componentes isolados mudam percepcao de marca** mesmo em background/incongruentes
  (Zoghaib 2019, RAM): tempo, modo, timbre. **Atencao modula** (Tran & Getz 2023, Music
  Perception, Univ. San Diego): tempo rapido → "corre mais rapido"; trombone vs flauta →
  "mais duravel" — mas so quando a atencao vai pra musica.
- Modelo integrativo de resposta a musica publicitaria (Lantos & Craton 2012): congruencia
  musica↔mensagem e moderador critico. Musica = **cue periferico**, efeito depende do **fit**
  com a narrativa (Morris & Boone, Univ. Florida).

### 6.4 Academia BR de trilha (teses/dissertacoes)

- **Vasconcelos 2008 (UNICAMP)** — trilha como peca indissociavel que dialoga com o visual;
  analisa _Central do Brasil_, _Pra Frente Brasil_, _Bye Bye Brasil_.
- **Oliveira 2017 (USP)** — significacao semiotica na musica de cinema (como constroi sentido
  narrativo).
- **Alvarenga 2020 (UFPE)** — Kleber Mendonca Filho: **"o proprio ato de escuta da musica e
  essencial na narrativa"** — trilha como agente ativo, nao acompanhamento.
- **Porto 2023 (UFRGS)** — som direto como marca estetica definidora de identidade filmica.
- **Souza 2018 (USP)** — Andre Abujamra: processo criativo ancorado em referencias culturais.

Padrao BR academico: trilha constroi emocao por **articulacao narrativa integrada** (nao
subordinacao) + **marca estetica contextualizada** (som direto, minimalismo, regionalismo) —
converge com a secao 4.

### 6.5 O que muda pro Muntu

- **Confirma o modelo mental:** o pack deve carregar valence (modo) + arousal (BPM/volume) +
  timbre — os 3 eixos que a literatura isola. A tabela da secao 2 esta cientificamente correta.
- **Arousal e barato, valence e caro:** o VLM/pack acerta intensidade facil; errar alegre↔triste
  e o risco real (film-scoring 6.2 + Pringles). Priorizar o sinal de valence na leitura de cena.
- **Timbre e cultura > treino:** a lente BR (instrumentacao regional) tem base — nao e sabor,
  muda o afeto. Reforca embutir instrumentacao BR nos packs quando a peca for brasileira.
- **Clima tem textura (13-dim):** nao colapsar tudo em 2D; manter os climas discretos da secao 2.

## Ponte pro Muntu (sem virar AI-prompt research)

- O achado "adjetivo subdetermina" **valida** carregar convencao inteira no pack: cada
  `clima` do VLM → linha da tabela da secao 2 (modo+BPM+instrumentacao), + funcao de ad
  (secao 3), + lente BR quando a peca for brasileira.
- A traducao dessa convencao pra prompt de gen-IA e o passo seguinte —
  [[moods-broadcast-prompt-2026-07]] ja tem o esqueleto tecnico. Esta nota da o **conteudo
  organico** (o QUE cada clima e musicalmente); a outra da o COMO frasear pro modelo.

## Caveats

- **Sintese do deep-research falhou 2x** (limite de gasto mensal); os 18 claims sao
  verificados 3-0 individualmente, mas o merge/dedupe final foi feito a mao aqui.
- Claims **nao verificados** (verificacao cortada no limite): luxo commercial, detalhe de
  mode→emotion, Lydian, tempo→arousal, instrumentacao-por-emocao. **Porem** o NotebookLM
  cobre todos esses independentemente (secao 2) — convergem, mas nao passaram pelo voto
  adversarial do deep-research. Tratar como solidos-mas-nao-triangulados.
- Muito exemplo BR (Bamerindus, Pipoca e Guarana, Central do Brasil) vem das fontes do
  notebook NotebookLM `ffada1b0`, nao de URL isolada citavel — verificavel abrindo o notebook.
- 3 videos YouTube falharam ingestao (sem transcript); 6 entraram.
- **Secao 6 (exa) e de confianca MAIOR que 1-5:** papers peer-reviewed com effect sizes,
  nao claims de notebook sem voto. Porem os β's vem de **1 extracao por subagent** (nao reli
  cada PDF na integra) — numeros conferidos contra o texto da busca, mas nao contra o paper
  fonte. Tratar β's como fieis-a-fonte-secundaria.
- **A tese "arousal>valence em confiabilidade" e um LEAN, nao lei** (ver ressalva em 6.2):
  Schutz modela valence melhor (81% vs 50%); Cohrdes da R² quase igual (.18 vs .19). O que
  sustenta o pipeline e o argumento especifico "modo e dificil de ler de video + cultura-
  dependente", nao uma superioridade universal do arousal.

## Open questions

- Convencao de **luxo** em comercial BR (claim morto) — re-pesquisar.
- **Tabela de traducao VLM-mood → clima da secao 2** na granularidade certa (o elo que
  fecha o "mood idiota"). GLM da "comedic"/"romantic"; falta mapear pro pacote musical.
- ~~Camada **exa** (tese academica BR de trilha)~~ — **FEITO** (secao 6, 2026-07-07): 4
  vetores exa, effect sizes de McMaster/McGill/Berkeley/Max Planck + teses BR.
- Como a estetica "magra e esguia" BR convive com pedido de ad "polido/otimista" — tensao
  entre autenticidade BR e commodity publicitaria.
- **Elo que falta pro Muntu:** transformar os pesos β (modo=38,9% valence, attack=63,2%
  arousal) numa regra concreta de leitura VLM→pack — quanto de valence vs arousal confiar do
  frame vs da cena. Passo de implementacao, nao de pesquisa.

## Fontes (2026-07-07)

- Kantar sonic branding / NeedScope — https://www.kantar.com/inspiration/brands/how-sonic-branding-builds-a-deeper-connection-with-your-audience
- Meio & Mensagem, trilha de campanha (BR) — https://www.meioemensagem.com.br/home/comunicacao/2017/05/17/como-e-pensada-a-trilha-sonora-para-uma-campanha.html
- SESC SP, musica de cinema brasileiro — https://www.sescsp.org.br/editorial/musica-de-cinema-playlist-revisita-o-brasil-atraves-dos-filmes/
- Film Independent, diretor↔compositor — https://www.filmindependent.org/blog/know-score-directors-can-effectively-communicate-composer/
- Tools for Film, work with a composer — https://www.toolsforfilm.com/blog/how-to-work-with-a-composer
- Adrian Walther, spotting sessions — https://www.adrianwalther.com/post/spotting-sessions-demystified-collaborating-with-directors-to-find-the-perfect-musical-moments
- New Music USA, composer publicitario (5 funcoes) — https://newmusicusa.org/nmbx/problem-solver-not-widget-maker/
- Songer, cinematic scoring (BPM/emocao) — https://songer.co/blog/posts/how-to-create-cinematic-music-scoring-without-a-studio
- NotebookLM notebook `ffada1b0` (35 fontes web BR/intl + 6 videos craft: Gaveta/Hans Zimmer, Cinematic Composing, whittymusic tensão×2, trilha importância, Itaú "Mostra Tua Força")

**Papers academicos (exa, secao 6):**

- Schutz/MAPLE (McMaster), "Emotion and expertise", Psychological Research 2021 — https://link.springer.com/article/10.1007/s00426-020-01467-1
- Gu et al., "Interpretable deep learning... musical emotion", Scientific Reports 2026 — https://doi.org/10.1038/s41598-025-34238-2
- Hofbauer & Rodriguez, valence/arousal stimuli validation, Intl. J. Psychology 2023 — https://doi.org/10.1002/ijop.12922
- Cohrdes et al. (Max Planck), "The sound of affect", Musicae Scientiae 2018 — https://www.fsv.uni-jena.de/fsvmedia/159390/cohrdes-etal-2018-thesoundofaffect.pdf
- Wang/McAdams (McGill Schulich), timbre cross-cultural, Frontiers Psychology 2021 — https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.732865/full
- Korsmit/McAdams (McGill), dimensional vs discrete affect, Frontiers Psychology 2023 — https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2023.1287334/full
- Cowen/Keltner (UC Berkeley, ed. Duke/Durham), "13 dimensions", PNAS 2020 — https://pmc.ncbi.nlm.nih.gov/articles/PMC6995018/
- Li/Thompson (Macquarie), cross-cultural emotion bias, Brain Sciences 2025 — https://www.mdpi.com/2076-3425/15/5/477
- Sayal et al. (Coimbra/Iscte/Panda), fMRI valence/arousal, IEEE TAC 2024 — https://doi.org/10.1109/taffc.2024.3507192
- Crocker & Fazekas, "Feature-based modelling of perceived emotion in film music" (FME-24), 2025 — https://doi.org/10.5281/zenodo.17488747
- "Acoustic features of instrumental movie soundtracks...", Scientific Reports 2025 — https://www.nature.com/articles/s41598-025-86089-6
- Lascurain, "The persuasive power of film music", UC eScholarship 2016 — https://escholarship.org/uc/item/4n1745zx
- Liu/Abolhasani/Hang, ad music subjective/objective, European J. Marketing 2022 — https://doi.org/10.1108/ejm-01-2021-0017
- Dogaru/Furnham/McClelland (UCL), music in ads & consumer behaviour, Acta Psychologica 2024 — https://doi.org/10.1016/j.actpsy.2024.104333
- Zoghaib, typology of ad music components, RAM 2019 — https://doi.org/10.1177/2051570718828893
- Tran & Getz (Univ. San Diego), pitch/tempo/timbre & product perception, Music Perception 2023 — https://doi.org/10.1525/mp.2023.41.1.59
- Teses BR: Vasconcelos 2008 (UNICAMP); Oliveira 2017 (USP); Alvarenga 2020 (UFPE); Porto 2023 (UFRGS); Souza 2018 (USP)

## Log

- 2026-07-07 — Criada. Pesquisa 4-canais no alvo REAL (trilha filme+comercial, lente BR)
  apos redirect (era AI-tooling, ver [[pesquisa-clima-ancorar-musica-filme]]). deep-research
  synthesize morreu 2x no limite → sintese a mao dos 18 claims + NotebookLM. Proximo:
  tabela de traducao VLM-mood→clima; camada exa proxima sessao; aplicar nos packs.
- 2026-07-07 — **Secao 6 adicionada (camada academica exa).** 4 buscas exa `research paper`
  (film-scoring · valence/arousal · musica em ad · trilha BR); outputs gigantes extraidos via
  subagents. Effect sizes duros ancoram a secao 2: modo=38,9% da variancia de valence, attack
  rate=63,2% de arousal (Schutz/McMaster); Tempo→arousal β=.55, Harmonic Complexity→valence
  β=−.43 (Gu 2026). Padrao transversal: **arousal confiavel, valence ruidosa** — reforca o
  erro Pringles. Labs de topo: Berkeley/Duke, McGill, McMaster, Max Planck, Macquarie, UCL.
  Berklee nao rende paper empirico (conservatorio). Open question exa: fechada.
- 2026-07-07 — **Auto-auditoria** (pedido "audite a pesquisa"). Achado grave: a tese "arousal
  confiavel, valence ruidosa" estava overstated (cherry-pick) — Schutz na verdade modela
  valence MELHOR (81% vs 50%); o correto e "modo e dificil de ler de video + cultura-dependente".
  Corrigido em 6.2 (ressalva) + Caveats. Tambem: "Berklee nao rende paper" → suavizado pra
  "nao apareceu nas buscas"; caveat de confianca da secao 6 (extracao por subagent, nao reli
  PDFs). Numeros β conferidos, mantidos.
