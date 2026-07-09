---
tipo: pesquisa
data: 2026-07-07
url: multi-fonte (ver secao Fontes)
---

# Sound design automatico por IA — estado jun/2026

Pesquisa pra camada de SFX do [[caminhos/ia-aplicada|Muntu Score]]. Pergunta do usuario:
"existe ferramenta de IA que faz sound design automaticamente?" — motivacao: nao travar
o MESMO one-shot em todo corte (repetitivo/enfadonho). Metodo: firecrawl search (2
rodadas) + NotebookLM com 7 fontes (notebook "Sound Design Automatico IA jun-2026 —
Muntu Score", id `7c6de200-5a76-4985-8d8a-dbb025ca6482`). Irma de
[[geradores-musica-ia-2026-06]].

## Veredito de uma linha

**Existe, em 2 niveis: video→som automatico (MMAudio v2, ElevenLabs video-to-sound —
veem o video e geram som contextual sincronizado) e texto→SFX (ElevenLabs SFX, Adobe
Firefly). Pro Muntu: hibrido ElevenLabs (mesma API key da trilha) com MMAudio como
alternativa pay-per-call.**

## Nivel 1 — video → som automatico (sound design automatico real)

| Ferramenta                    | Como funciona                                                                                                                                                                                                        | API / custo                                            | Licenca                                           |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------- |
| **MMAudio v2**                | analise multimodal (imagem + movimento + contexto de cena) → foley/ambiencia sincronizada; prompt de texto como hint; **limite ~8s** → video de 30s = janelas de 2-3s ao redor de cada corte, processadas individual | REST via WaveSpeed, pay-per-generation, sem assinatura | uso comercial OK                                  |
| **ElevenLabs video-to-sound** | visao computacional analisa frames (identifica veiculos, pessoas, cenario) + SFX API → **4 variacoes por video**                                                                                                     | API ElevenLabs (mesma key do Music)                    | royalty-free comercial/publicidade com conta paga |
| **PixVerse**                  | audio a partir do movimento do video; foco video-IA/social                                                                                                                                                           | —                                                      | —                                                 |
| **Google V2A (DeepMind)**     | research, acoplado ao Veo; sem API standalone                                                                                                                                                                        | —                                                      | —                                                 |

## Nivel 2 — texto → SFX (prompt, nao automatico)

- **ElevenLabs SFX** — qualquer som por texto, controle de duracao + prompt influence;
  royalty-free comercial (conta paga; Starter ~US$6/mes mai/2026).
- **Adobe Firefly SFX generator** — diferencial: controle por VOZ (usuario "atua" o som
  com a boca, timing/intensidade viram o som real). Instrumento de sound designer.
- Stable Audio (SFX tambem), Kling, Canva (basicos).

## Implicacoes pro Muntu Score

1. **Cortes deixam de ser monotonos** — em vez do mesmo one-shot em todo corte, janela
   de 2-3s ao redor de cada corte → video-to-sound → transicao UNICA e contextual por
   corte. Resolve o "enfadonho" apontado pelo usuario.
2. **Hierarquia preservada (assinatura > variedade):** se TODO som for gerado, a peca
   perde a digital sonora Muntu (diferencial = curadoria/marca, nao o gerador, que
   qualquer um aluga). Regra: **SFX gerado varia nos cortes comuns; stem de assinatura
   crava climax + fechamento (brand sting).**
3. **Recomendacao hibrida** (NotebookLM): video-to-audio pros impactos fisicos nos
   cortes (timing nasce da imagem) + text-to-SFX pra transicoes estilizadas com prompt
   contextual do VLM (que ja le o mood). Ecossistema ElevenLabs cobre os dois com a
   mesma key do Music; MMAudio/WaveSpeed = alternativa pay-per-call barata.
4. **Escopo: camada 2 (semana 2-3), junto do sync matematico.** NAO entra na barra de
   demo (stem real + Task 8 + Task 11-VLM) — disciplina anti-poco-sem-fundo do
   "impressionar".

## Fontes

- mmaudio.net (MMAudio v2 — video-to-audio, limites, prompt hint)
- wavespeed.ai/collections/audio-for-video (MMAudio v2 via REST API, pricing por call)
- elevenlabs.io/blog/...video-to-sound-generator (video-to-sound: frames → 4 variacoes)
- elevenlabs.io/studio (Studio 3.0 — timeline unica voz+musica+SFX)
- elevenlabs.io/sound-effects (SFX API text-to-sound, royalty-free)
- adobe.com/products/firefly/features/sound-effect-generator (Firefly SFX, controle por voz)
- pixverse.ai/en/blog/best-ai-sound-effect-generator (comparativo 9 tools, PixVerse motion-to-audio)

## Teste empirico 2026-07-07 (A/B/C/D no comercial real)

Deep-research verificada (106 agentes) + build/teste no Muntu Score, comercial Pringles
"Stuck In" (16s). Comparadas 5 variantes de sound design:

- **A** = HunyuanVideo-Foley (video inteiro, cego)
- **B** = Hunyuan inteiro + prompt de descricao (VLM)
- **D1/D2** = Hunyuan POR CENA (cego / + prompt time-aware por cena)
- **C** = VLM (Gemini 2.5 Pro) le a cena -> descricao detalhada (ambiencia + foley com
  contagem) -> **ElevenLabs text-to-SFX** one-shot -> colado no TEMPO EXATO do corte.

**Veredito do usuario (ouvido): C ganha.** Motivo decisivo: **Hunyuan (A/D1/D2) gera
MUSICA junto** e NAO da pra excluir — bate com o achado da deep-research: os modelos
video->audio (MMAudio/ThinkSound/Hunyuan) **nao expoem negative-prompt** pra tirar
voz/musica; controle so via prompt positivo, e detalhe extra ate PIORA o sync. Pro
pipeline em CAMADAS (musica = layer separado), contaminacao com musica desqualifica o
video->audio. O **C** e o unico com foley/ambiencia limpo e controlavel.

**Correcoes a esta nota (deep-research verificada):**

- **HunyuanVideo-Foley (Tencent) = novo SOTA** de video->audio (bate MMAudio/ThinkSound em
  fidelidade+sync); API Replicate `tencent/hunyuanvideo-foley` (~$0.02-0.05/run) + WaveSpeed.
  Nao estava nesta nota.
- **ElevenLabs video-to-sound e SO WEB** (a API deles e text-to-SFX). A tabela de Nivel 1
  acima da a entender que tem API de video — nao tem.

**Arquitetura decidida (Muntu Score):** camada de sound design = **C** — VLM le o filme
(indoor/outdoor + reverb + acao com contagem) -> ElevenLabs text-SFX -> colado no tempo
(sync = nosso, frame-tight, igual aos stems). Trade-off aceito: o one-shot nao conta cada
passo (4 passos != 4), mas evita a musica-contaminacao do video->audio. Ver
[[muntu-sfx-cena-nao-mood]]. Reader = Gemini 2.5 Pro (mais preciso que GLM: pegou o gag
exato "mao presa na lata" + contagens tipo "3 keyboard clicks").

## Log

- **2026-07-07** — re-query NotebookLM (mesmo notebook `7c6de200`, CLI `notebooklm ask`)
  confirmou veredito. Sem mudanca de recomendacao. Detalhes novos:
  - **PixVerse**: baseado em creditos (~14 creditos / video 6s); automacao via ID de
    video; permite manter audio original e so somar camada SFX.
  - **Adobe Firefly**: reforco do controle-por-voz (ditar timing/intensidade com mic).
  - **Recomendacao final cristalizada** (bate com [[muntu-sfx-cena-nao-mood]] da memoria):
    foley/cortes de acao → **MMAudio v2** ou **PixVerse** (som segue movimento); design
    criativo/transicao sem gancho visual → **ElevenLabs** text-to-SFX; pipeline full-audio
    → **API ElevenLabs + Studio 3.0**. Combo producao = **MMAudio (foley) + ElevenLabs
    (design)**. Nao existe ferramenta unica "melhor".
