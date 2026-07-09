# Handoff — Muntu Score (2026-07-07, sessão PIN + camadas + refs + A/B)

Ler antes de continuar. Repo `~/Documentos/muntu-score`. **NADA COMMITADO** — commits são
mão do Marcos, sem trailer ([[muntu-score-commits-sem-trailer]]). Supersede
`handoff-2026-07-07-trilha-por-parte.md` (que segue válido pra história do reframe).

## TL;DR

Sessão longa dirigida por ouvido no comercial Pringles (`real.mp4`). Resolvido o **problema
central da sessão anterior** (estocasticidade do reader) com um **mecanismo de PIN de 2
camadas** + uma pilha de determinismo em cima. **130 testes verdes.** Demo APROVADA pelo
usuário ("achei legal") e TRAVADA em áudio (`outputs/pinned/*.mp3` + `bed_file` no PIN =
100% reproduzível). Pesquisa A vs B fechada (nota `career/pesquisa/apis-musica-licenciada-2026-07.md`).

## O mecanismo de PIN (a espinha da sessão)

Contra a estocasticidade do VLM (reader varia run-a-run) e do gerador de música:

1. **PIN camada 1 — a LEITURA.** `reader.le_timeline` auto-grava `outputs/timeline_<stem>.json`
   a cada read. `pipeline.run(..., timeline_path=X)` carrega o JSON e PULA a re-leitura do
   filme. Loop: roda sem pin → ouve → quando boa, preserva o JSON com outro nome → re-roda
   com `timeline_path`. Separa "ler o filme" de "gerar áudio". `reader.salva_timeline`/
   `carrega_timeline`/`timeline_scratch_path`.
2. **PIN camada 2 — o ÁUDIO.** `parte["bed_file"]` = caminho de áudio TRAVADO (qualquer
   mp3/wav — gerado, de biblioteca, do usuário). `parte["bed_offset"]` (s) = de onde a
   faixa entra (pula intro, pega refrão). Se `bed_file` existe, NÃO gera. É o que corta
   música pronta HOJE.
3. **O JSON é EDITÁVEL** — o usuário (ouvido) crava um beat, Claude (técnico) edita o campo.
   Reader não precisa acertar no chute; a timeline travada é hand-tunable.

**PIN atual do Pringles:** `outputs/timeline_real_PIN.json` — demo aprovada, com
`bed_file` apontando `outputs/pinned/{festa,balada}_aprovada_2026-07-07.mp3`.

## Arquitetura da trilha (o que ficou)

```
analyze (cortes) → reader.le_timeline (VLM Gemini) → timeline:
  { narrativa, era, comico(bool), climax_t, stop_t, stop_fim_t,
    pontuacoes[{cena,t,sfx,gain_db}], citacoes[{cena,t,melodia}],
    partes[{start,end,tipo:diegetic|score, clima(vocab), mood(free), confianca_valence,
            sobe_t, sobe_estilos[], bed_file, bed_offset, provider}] }
  → trilha.monta_trilha(timeline, cortes): música POR PARTE
       score c/ pack curado (clima→pack) + composition_plan (arco Build→Apice)
       diegetico → band-limit+reverb+nivel (som do ambiente)
       STOP diegetico comico → wind-down de vitrola (stop_t..stop_fim_t)
       pontuacoes → SFX overlay (agulha) no beat, gain do PIN
  → mix (música-forward, foley SOB) → mux
```

## O que foi CONSTRUÍDO nesta sessão (não commitado)

**Determinismo do reader → apply:**

- `comico` film-level (reader) → gag dispara mesmo com partes tocadas RETAS (comédia séria).
- `pontuacoes` (reader→apply): SFX no beat narrativo (agulha de vinil), `gain_db` por
  pontuação no PIN. `reader._beats` normaliza (compartilhado c/ citações).
- `citacoes` (reader→apply): motivo de melodia de **domínio público** p/ situação clássica
  (casamento→marcha nupcial, funeral→Chopin, Natal→Jingle Bells...). Tecido na SEÇÃO do
  beat. **Fraseado ToS-safe: "incorporating a <melodia> melodic motif"** — "quoting the
  <obra>" dispara o filtro anti-cover do ElevenLabs em TODA run (probe confirmado).
- `stop_fim_t` (fim da cena do stop) → wind-down ocupa beat→corte (pitch desce a cena
  inteira, agulha no corte), não 0.8s fixo.

**Arco/estrutura (o FILME dita, não o modelo):**

- `_plano_da_parte`: composition_plan Build→Apice, ápice ancorado em `sobe_t` (PIN) ou
  `climax_t`. **Seções alinhadas aos CORTES de cena** (`cortes`) — música troca de movimento
  no corte; âncora do ápice tem prioridade sobre corte vizinho.
- `sobe_estilos` (PIN/reader): direções criativas extras do ápice (reprise do sax).
- Arco do PACK usado (romantico Climax = sax solo + violinos), não genérico.
- **Cauda** descartável (4s no clima do ápice): o modelo INSISTE em resolver/apagar o fim →
  deixa ele morrer na cauda, o corte em dur_ms cai em plena energia. + `_garante_rabo_vivo`
  (detecta rabo morto no ponto de corte, re-rola 1x).

**Fixes de modelo (ElevenLabs):**

- `musica._reconcilia_chunks` — **BUG-CHAVE**: `composition_plan.create()` re-sintetiza os
  chunks e REDISTRIBUI estilos entre seções (o sax solo / marcha / pico migravam pra Cauda
  descartada). Força os estilos locais de volta em cada chunk; Cauda vira espelho da anterior.
- `musica._sugestao_de_plano` + retry: 400 `bad_composition_plan` (ToS) devolve
  `composition_plan_suggestion` (plano reescrito aceito) → re-gera 1x com ela.
- **Full-band fix**: removido "sits under voiceover"/"sparse under voiceover" (fazia caminha
  de piano rala); pack `negativos` injetados em TODAS as seções (mata "épico"/tambores
  orquestrais no lugar do sax); `packs/romantico.json` = balada COMPLETA (drums+bass+sax).

**BPM/warp determinístico:**

- `_bpm_da_parte`: BPM dentro do range do pack cuja GRADE encaixa nos cortes da parte
  (`estima_bpm`, grid search puro Python).
- `warp` RE-LIGADO no score: librosa mede tempo real → rubberband trava na grade dos cortes
  (cap 6%, só score com pack não-gated).

**Gate de valence estático** (`director.pack_por_clima(confianca=)`): pack MINOR
(tenso/melancolico) gated pela `mood.CONFIANCA_VALENCE` (tabela β de
`career/pesquisa/mapa-vlm-mood-clima-muntu-2026-07.md`) — path de música única. Path
por-parte usa confiança por-leitura do reader (AMBIGUO local em vez de default).

**Provider (2 APIs):** default ElevenLabs em TUDO (A/B: festa Stability perdeu de ouvido,
revertido); `parte["provider"]` no PIN força alternativo. Mecanismo fica.

**Housekeeping:** montagem de frames extraída 1x compartilhada (mood/reader/sfx_map, eram 3);
`sfx_map.MAX_TOKENS` 24k→64k; **rename `cama`→`musica` no repo inteiro** (módulo
`base_bed.py`→`musica.py`, `gerar_cama`→`gera_musica`, `com_cama`→`com_musica`) — pedido do
usuário (é música, não cama de fundo).

## Sistema de REFERÊNCIAS (`packs/refs/`)

Curadoria versionada, **determinística** (mesma filosofia do PIN: busca é ferramenta de
curadoria, arquivo é a fonte). `.md` por pack — tabela Faixa/Artista/Ano/**BPM**/o-que-roubar.
`README.md` documenta o fluxo (`/yt-search`/NotebookLM levanta → usuário ouve/corta →
vocabulário migra pro pack JSON). `romantico.md` semeado (Careless Whisper, Lionel Richie,
Foreigner + BR brega Reginaldo Rossi/Tim Maia); 9 skeletons. **Decisão: NÃO virar banco/
Obsidian** — markdown+git aguenta centenas (÷12 packs = 20-40 linhas/arquivo). Banco só
quando o RUNTIME precisar consultar refs sozinho (gatilho: `conditioning_ref` do ElevenLabs
ou busca-por-ref automática).

## DECISÃO ESTRATÉGICA — A vs B (o gargalo)

**Gargalo = MODELO de música**, não refs (API secundária). Evidência: create() redistribui
estilos, ignora eventos (sax/marcha), estocástico. Consequência: tirar responsabilidade do
modelo.

- **A (gen IA + camadas):** modelo gera só a vibe; marcha (MIDI DP), sax (gen isolada),
  pontuações = overlays NOSSOS, exatos e PINáveis. Wow máximo (tool-isca 100% IA).
- **B (biblioteca licenciada):** Epidemic Partner API (self-serve + Soundmatch vídeo→faixa +
  licença ads + PT-BR) = qualidade real, estocasticidade zero. `bed_file` já é a porta.
- **Recomendação: A agora (demo/wow), B via Epidemic quando houver cliente.** Detalhe +
  fontes: `career/pesquisa/apis-musica-licenciada-2026-07.md`.

## Como rodar

```bash
cd ~/Documentos/muntu-score && source venv/bin/activate
python -m pytest tests/ -q                       # 130 verdes
# regen da demo aprovada (usa bed_file pinado — determinístico, sem re-gerar):
python -c "from dotenv import load_dotenv; load_dotenv(); from pipeline import run; print(run('outputs/real.mp4', out_path='outputs/demo_partes.mp4', com_musica=True, timeline_path='outputs/timeline_real_PIN.json'))"
```

## Config (.env — gitignored, TODAS queimadas em chat → ROTACIONAR)

```
MUNTU_MOOD_API_KEY=<OpenRouter>  MUNTU_MOOD_MODEL=google/gemini-2.5-pro  # reader+mood+sfx_map
ELEVENLABS_API_KEY=<sound_generation + music>   # SFX + música (composition_plan só aqui)
MUNTU_BED_PROVIDER=elevenlabs
STABILITY_API_KEY / REPLICATE_API_TOKEN         # provider alternativo / sem uso
```

## Pendências ordenadas (próxima sessão)

1. **COMMIT** (mão do Marcos, sem trailer) — bloco grande, 130 testes, ~15 arquivos +
   módulo renomeado. **Nada commitado.**
2. **ROTACIONAR TODAS as keys** (queimadas em chat).
3. **sfx-map estoura tokens ainda** (3ª vez, já em 64k = teto Gemini) → foley fica fora.
   Fix real = ENCOLHER o output pedido (descrições menores) ou dividir em 2 calls, NÃO subir
   teto.
4. **Marcha/sax em A ainda são aposta de prompt** (negativos + banda completa melhoram odds,
   não garantem). Garantia = overlays (marcha MIDI DP + sax gen isolada) OU B.
5. **Experimento A/B barato:** API key free do Epidemic → Soundmatch no `real.mp4` →
   `bed_file` → comparar de ouvido balada-IA vs faixa-real.
6. Chaves JSON/constantes ainda em EN (`bed_prompt`/`bed_estilo`/`BED_GAIN_DB`) — 2ª passada
   do rename se quiser.

## Memórias tocadas

[[muntu-trilha-regras-criativas]] (o reader SEMPRE escolhe; output errado = calibra o
reader), [[muntu-trilha-por-parte]], [[muntu-foley-decidido-text-sfx]],
[[muntu-produto-elefante-branco]] (A-agora/B-depois = mesma disciplina anti-elefante).
