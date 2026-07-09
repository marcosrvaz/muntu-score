# Handoff — learn-from-ads: execução 2026-07-09 (ler ANTES de continuar)

Sessão Fable 2026-07-09 executou a arquitetura do spec `docs/spec-arquitetura-learn-ads-2026-07-08.md`
via 3 terminais paralelos (esquema Fable planeja / executores executam / review forte).
Planos: `docs/plans/2026-07-09-*.md` (master + ws-a/b/c). Issues #1-#3 fechráveis.

## O que está PRONTO e commitado (main, até ~`ece21c7`+)

- **WS-A (camada 1, wow) COMPLETO:** `muntu/tags.py` (schema canônico), reader emite
  `ironia/cultura/instrumentacao` + viés cômico calibrado (sincero-sobre-absurdo = kitsch;
  deadpan só footage seco; MAX_TOKENS 64k), `_prompt_da_parte` compõe tags (ironia governa
  kitsch), `epidemic._clima_efetivo` (kitsch/parodia → busca comedic). Validado: leitura
  kitsch do Pringles cravada; PIN continua o entregável (`outputs/timeline_real_kitsch.json`).
- **WS-B (camada 2, crux) COMPLETO:** `muntu/tagueador.py` — música OUVE a trilha (32kHz;
  só-frames chutava), SFX/VO por áudio, `muntu/faixa_id.py` (AudD fingerprinting; matches
  são CANDIDATOS no prompt, não ground truth — falsos positivos frequentes, só Danúbio
  confirmou). `scripts/spike_tagueador.py` → JSONs + RELATORIO em `outputs/spike_tags/`.
- **WS-C (camada 3, premium) COMPLETO (infra):** migration `supabase/.../assets.sql`
  (RRF SQL puro k=60, text_emb vector(1536) OpenRouter 3-small, audio_emb vector(512)),
  `muntu/banco.py` (embed_texto via OpenRouter API; embed_audio via venv `.venv-embed`;
  `popula_beds` mesmo contrato do epidemic; `busca_por_draft` = bridge A→B),
  `scripts/ingere_assets.py` (sidecar obrigatório). Migration APLICADA no projeto novo.
- **Regras do diretor:** `packs/regras_diretor.md` (33 regras ditadas pelo Marcos) —
  injetadas no prompt do reader via `reader._bloco_regras()`. Arquivo vivo.
- **Suite:** 252+ verdes (`venv/bin/pytest tests/ -q` — usar o venv do repo SEMPRE).

## Decisões técnicas NÃO óbvias (não re-litigar)

- CLAP: `laion/clap-htsat-unfused` (o `larger_clap_music` está DEGENERADO: embeddings
  colapsados, provado no sanity — ver docstring `scripts/embeddings/embed_audio.py`).
  Pin `transformers<5` no venv-embed. Receita: `.pooler_output[0]`, janelas 10s, mean-pool L2.
- Gemini descreve registro mas NÃO nomeia faixa; AudD nomeia mas mente (falso positivo) —
  por isso "candidato verificável" no prompt.
- OpenRouter TEM endpoint de embeddings (D4) — mesma key `MUNTU_MOOD_API_KEY`.
- GraphRAG/TwelveLabs/Vertex avaliados e descartados/diferidos (master D11 + conversa).
- Commits: mão do Marcos OU Claude commitando SEM trailer (convenção do repo).
  rtk engole exit code de pytest em cadeia `&&` — rodar pytest SEPARADO antes de commitar.

## LOTE DOS 47: CONCLUÍDO (2026-07-09 fim do dia)

- **47/47 com música, 16 com faixa nomeada (AudD), 37 com VO** — dataset em
  `outputs/spike_tags/*.json` + `RELATORIO.md` consolidado. Gate D10 APROVADO.
- Fixes de calibração descobertos no lote (todos commitados): áudio vai como MP3
  (wav de ad longo estourava payload); montagem grande SUPRIME o ouvido → fallback
  só-áudio quando partes vêm vazias; score synth atmosférico ≠ ambiência.
- MP Marte: JSON curado manualmente com output validado do modelo (só-áudio) — a
  chamada com montagem re-sorteava vazio mesmo com fallback; conferir na retaguagem.
- Gabarito do Marcos: `outputs/spike_tags/GABARITO.md` (ground truth + pendências).
- Token AudD: Marcos tem (passar inline; `.env` protegido contra escrita de agente).
- **Regra de APPLY ditada e NÃO implementada:** `packs/regras_apply.md` — vinyl
  slow-down em stop diegético SÓ quando gênero fun/comédia, sem needle scratch.
  Implementar na camada 1.5 (condicionar `_stop_diegetico` + suprimir pontuação).

## PRÓXIMOS PASSOS (ordem)

1. **Terminar/conferir lote 47** — falhas pontuais: re-rodar só os ads faltantes.
2. **Camada 1.5 (PRECISA DE PLANO NOVO — Fable planeja antes de executar):**
   a. Few-shot de ironia no reader a partir do corpus tagueado (exemplos reais > regra abstrata).
   b. Reader emitir direção de clímax (`sobe_estilos` — o arco/sax que o A/B do Pringles mostrou
   que falta; hoje é só PIN manual).
3. **Ingestão do banco** — bloqueada em INPUT DO MARCOS: faixas de música dele (own/Artlist)
   com sidecar JSON de tags. Ingestão em massa liberada (gate D10 aprovado).
4. Camada 4 (SFX bank + VO): deferida; VO bloqueado em roteiro do usuário.
5. Segurança pendente (Marcos adiou): rotacionar ElevenLabs/Replicate/Anthropic/AudD.

## Como retomar

Sessão nova (Sonnet serve pra execução; Fable pra planejar a 1.5):
"Leia docs/handoff-2026-07-09-learn-ads-execucao.md e docs/plans/2026-07-09-arquitetura-learn-ads-master.md"
