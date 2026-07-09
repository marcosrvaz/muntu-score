---
tipo: pesquisa
data: 2026-06-10
url: multi-fonte (ver secao Fontes)
---

# Geradores de musica por IA — estado jun/2026

Pesquisa pra escolha da cama-base IA do [[caminhos/ia-aplicada|Muntu Score]] (Task 8).
Pergunta do usuario: "qual a melhor geradora de musica por IA hoje? ja usei o Suno".
Metodo: firecrawl search (2 rodadas) + NotebookLM com 6 fontes de 2026 (notebook
"Geradores de Musica IA jun-2026 — Muntu Score", id `7d4b9580-1150-4c55-a378-9d312d44077e`).
Complementa [[viabilidade-sync-ad-audio]] (que ja vetava Suno em 2026-06-09).

## Veredito de uma linha

**"Melhor" depende do eixo: qualidade bruta = Suno v5.5; pro pipeline Muntu (API +
brand-safety pra publicidade) = ElevenLabs Music V2, com Stable Audio 3 como
fallback barato de instrumental.**

## Ranking por eixo

| Eixo                        | Lider                     | Detalhe                                                                                                                                                                           |
| --------------------------- | ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Vocais / musica completa    | **Suno v5.5** (mar/2026)  | vocal rivaliza humano; **sem API oficial**; litigio Sony ATIVO (acordo so Warner nov/2025)                                                                                        |
| Fidelidade sonora           | **Udio v4**               | 48kHz stereo, cinematografico, inpainting + stems; **downloads DESABILITADOS jun/2026** (transicao plataforma UMG) — fora de pipeline externo                                     |
| Brand-safety + API          | **ElevenLabs Music V2**   | treino 100% licenciado (Merlin/Kobalt) desde dia 1; API oficial + SDK Python/TS; `composition_plan` (estrutura secao-a-secao); instrumental mode; ate 10min; ~US$0,80/min via FAL |
| Custo de API                | **MiniMax Music 2.5**     | US$0,035/geracao via FAL; uso comercial OK; sem litigio conhecido                                                                                                                 |
| Instrumental barato + legal | **Stable Audio 3 / 2.5**  | so instrumental/SFX (vocal fraco); ~US$0,024/faixa; treino licenciado Warner/UMG; ate 6m20s; inpainting; variante **open weights** (roda local)                                   |
| Controle em tempo real      | **Google Lyria RealTime** | API Gemini (WebSocket): **pilota BPM 60-200**, densidade, brilho, escala, mute de baixo/bateria ao vivo. Instrumental/streaming. Lyria 3 (vocais, fev/2026) ainda sem API         |

## Implicacoes pro Muntu Score

1. **ElevenLabs Music V2 confirmado** como base da Task 8 — unica com API pronta +
   seguranca juridica limpa. Publicidade e onde brand-safety pesa
   ([[viabilidade-sync-ad-audio]]: barreira real de ad = legal, nao qualidade).
2. **Stable Audio 3 = fallback/custo a testar na Task 8.** Cama instrumental e o caso
   de uso exato (trilha de comercial nao precisa de vocal). ~30x mais barato que
   ElevenLabs, mesma classe de seguranca legal (treino licenciado). Testar os dois
   lado a lado.
3. **Lyria RealTime = experimento futuro pro sync.** Pilotar BPM via API conversa
   direto com o estagio 1 do sync matematico (BPM calculado da grade de cortes) —
   geraria ja no BPM alvo, reduzindo/eliminando warp pos-geracao. Nao bloqueia Task 8.
4. **Suno segue vetado** pro pipeline (sem API oficial + litigio + anti-brand-safety).
   Uso pessoal/referencia de qualidade apenas.
5. **Udio fora por indisponibilidade** (downloads pausados na transicao UMG), apesar
   de API oficial e acordos de licenca. Reavaliar se/quando a plataforma co-licenciada
   abrir.

## Fontes

- teamday.ai/blog/best-ai-music-models-2026 (Suno v5, ElevenLabs, Lyria 3, Udio, MiniMax, Stable Audio — APIs e precos)
- aimagicx.com/blog/suno-vs-udio-vs-elevenlabs-music-comparison-2026 (copyright/litigios; "ElevenLabs = licenca comercial mais limpa")
- felloai.com/best-ai-music-generators/ (ranking geral; Suno v5.5)
- undetectr.com/blog/best-ai-music-generators-2026 (Suno features / Udio qualidade / Eleven vocais)
- elevenlabs.io/music-api (API oficial: composition_plan, streaming, licenca comercial, SDKs)
- mindstudio.ai/blog/elevenlabs-music-v2-vs-suno-ai-comparison-2 (Eleven V2 vs Suno)
