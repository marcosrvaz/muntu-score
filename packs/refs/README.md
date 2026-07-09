# Sistema de referências (refs)

Referência musical por pack — **curadoria versionada, determinística**. Um `.md` por pack
(`refs/<pack>.md`) com faixas-referência: o que o pack DEVE soar. É craft do usuário
(ouvido); Claude ajuda a levantar candidatas.

## Por que arquivo, não busca

Busca (YouTube/NotebookLM) é ferramenta de **curadoria** (adicionar refs), nunca de
runtime. O arquivo versionado é a fonte: mesma ref hoje e daqui a 6 meses. Mesmo espírito
do PIN: travar o que o ouvido aprovou.

## Formato

```
| Faixa | Artista | Ano | O que roubar |
```

"O que roubar" = o elemento concreto (timbre do sax, gated drums, andamento, fraseado) —
vira vocabulário de `prompt_template`/`arco` do pack.

## Fluxo de curadoria

1. Sessão Claude: `/yt-search <faixa>` ou NotebookLM pra levantar candidatas + links.
2. Usuário ouve, corta, anota "o que roubar".
3. O que sobrou vira linha da tabela; o vocabulário migra pro pack JSON.

## Futuro (R&D)

O schema de chunk do ElevenLabs expõe `conditioning_ref` + `condition_strength`
(visto no probe 2026-07-07) — potencial ancoragem da geração em áudio de referência =
determinismo de timbre real. Não documentado publicamente; investigar.
