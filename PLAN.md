# Muntu Score — Plano de Implementacao

> **Pra voce, Marcos.** Vibe coding ok. Claude pode ser pair (opcional) — mas o repo e
> o deploy saem com o TEU nome: e isso que a Sonda A&D testa (estudo invisivel -> prova
> publica). Cada passo e 1 acao pequena. Faca em ordem. Commite frequente.

**Goal:** Web app que recebe video curto (10-30s) e devolve com trilha gerada (cama-base
IA + teus stems sincronizados aos cortes, dirigidos por context pack de publicidade).

**Architecture:** Pipeline de 6 unidades isoladas (Analyzer -> Director -> Base ∥
Signature -> Mixer -> Web App). Walking skeleton: binario rodando na semana 1, aprofunda
depois. Design: `docs/superpowers/specs/2026-06-09-muntu-score-design.md`.

**Tech Stack:** Python 3.11 · ffmpeg · PySceneDetect · pydub/numpy · Replicate (gen de
musica) · Gradio + Hugging Face Spaces (deploy).

**Entregavel binario:** repo GitHub publico + HF Space rodando. **Prazo ~2026-07-09.**

---

## Pre-requisitos (faca antes da Semana 1)

- [ ] Conta no GitHub (ja tem).
- [ ] Conta no [Hugging Face](https://huggingface.co) (gratis) — pro deploy.
- [ ] Conta no [Replicate](https://replicate.com) (gratis pra comecar; gen de musica e pago
      por uso, centavos por clipe) — guarda o API token.
- [ ] `ffmpeg` instalado: `ffmpeg -version` (se faltar: `sudo apt install ffmpeg`).
- [ ] Python 3.11+: `python3 --version`.
- [ ] Separa 1 video de teste curto (10-30s, com 3-5 cortes) — pode ser qualquer clipe.

---

## Estrutura de arquivos

```
muntu-score/
  app.py                  # Gradio: UI + chama pipeline
  pipeline.py             # orquestra: video -> video scoreado
  muntu/
    analyzer.py           # video -> brief JSON (cortes, clima)
    director.py           # brief + context pack -> plano de score
    base_bed.py           # prompt -> cama-base (Replicate)
    signature.py          # plano + stems -> camada de assinatura sincronizada
    mixer.py              # base + assinatura + video -> video final
  assets/
    stems/<pack>/         # teus stems .wav + manifest.json
    sample.mp4            # video de teste
  packs/
    default.json          # 1o context pack
  tests/
    test_analyzer.py
    test_signature.py
  requirements.txt
  README.md               # pro recrutador: o que e, como roda, screenshot
  .gitignore              # ignora .env, venv, outputs
```

Regra: 1 arquivo = 1 responsabilidade. Se um cresce demais, ta fazendo coisa a mais.

---

## Chunk 1 — Semana 1: Walking Skeleton (BINARIO)

Meta da semana: **URL no ar que recebe video e devolve video com som nos cortes.** Feio
ta OK. Som = 1 stem fixo batendo nos cortes. Isso ja e o entregavel binario.

### Task 0: Scaffold do repo

**Files:** Create `muntu-score/` (tudo)

- [ ] **Passo 1:** Cria repo e ambiente

```bash
mkdir muntu-score && cd muntu-score
git init
python3 -m venv venv && source venv/bin/activate
```

- [ ] **Passo 2:** `requirements.txt`

```
gradio
scenedetect[opencv]
pydub
numpy
replicate
python-dotenv
```

- [ ] **Passo 3:** Instala: `pip install -r requirements.txt`
- [ ] **Passo 4:** `.gitignore`

```
venv/
.env
outputs/
__pycache__/
*.pyc
```

- [ ] **Passo 5:** Cria pastas e copia o video de teste

```bash
mkdir -p muntu assets/stems/default packs tests outputs
cp /caminho/do/seu/video.mp4 assets/sample.mp4
```

- [ ] **Passo 6:** Commit

```bash
git add -A && git commit -m "chore: scaffold muntu-score"
```

### Task 1: Analyzer — detectar cortes

**Files:** Create `muntu/analyzer.py`, `tests/test_analyzer.py`

- [ ] **Passo 1: Teste que falha** — `tests/test_analyzer.py`

```python
from muntu.analyzer import analyze

def test_analyze_returns_brief():
    brief = analyze("assets/sample.mp4")
    assert brief["duracao"] > 0
    assert isinstance(brief["cortes"], list)
    # cortes em ordem crescente, dentro da duracao
    assert brief["cortes"] == sorted(brief["cortes"])
    assert all(0 <= t <= brief["duracao"] for t in brief["cortes"])
```

- [ ] **Passo 2: Roda, ve falhar** — `pytest tests/test_analyzer.py -v` -> FAIL (no module)
- [ ] **Passo 3: Implementa** — `muntu/analyzer.py`

```python
from scenedetect import detect, ContentDetector, open_video

def analyze(video_path: str) -> dict:
    video = open_video(video_path)
    scenes = detect(video_path, ContentDetector())
    duracao = video.duration.get_seconds()
    cortes = [s[0].get_seconds() for s in scenes if s[0].get_seconds() > 0]
    return {"duracao": duracao, "cortes": cortes, "cenas": [], "bpm_sugerido": 120}
```

- [ ] **Passo 4: Roda, ve passar** — `pytest tests/test_analyzer.py -v` -> PASS
- [ ] **Passo 5: Commit** — `git add -A && git commit -m "feat: analyzer detecta cortes"`

### Task 2: Signature — colocar 1 stem nos cortes

**Files:** Create `muntu/signature.py`, `tests/test_signature.py`. Add 1 stem: `assets/stems/default/hit.wav` (qualquer hit curto teu, <2s).

- [ ] **Passo 1: Teste que falha** — math de timing, sem audio real

```python
from muntu.signature import placement_plan

def test_placement_at_cuts():
    cuts = [1.0, 2.5, 4.0]
    plan = placement_plan(cuts, duracao=5.0)
    assert [p["t"] for p in plan] == cuts
    assert all(p["stem"] == "hit.wav" for p in plan)
```

- [ ] **Passo 2: Roda, ve falhar**
- [ ] **Passo 3: Implementa** — `muntu/signature.py`

```python
from pydub import AudioSegment

def placement_plan(cuts: list, duracao: float, stem: str = "hit.wav") -> list:
    return [{"t": t, "stem": stem} for t in cuts]

def render_signature(plan: list, duracao: float, stems_dir: str) -> AudioSegment:
    track = AudioSegment.silent(duration=int(duracao * 1000))
    for p in plan:
        hit = AudioSegment.from_wav(f"{stems_dir}/{p['stem']}")
        track = track.overlay(hit, position=int(p["t"] * 1000))
    return track
```

- [ ] **Passo 4: Roda, ve passar** (so `test_placement_at_cuts` — render testa na mao)
- [ ] **Passo 5: Testa render na orelha**

```python
# scratch: gera wav e escuta
from muntu.signature import placement_plan, render_signature
plan = placement_plan([1.0, 2.5, 4.0], 5.0)
render_signature(plan, 5.0, "assets/stems/default").export("outputs/sig.wav", format="wav")
```

Escuta `outputs/sig.wav` — hit deve bater em 1.0/2.5/4.0s.

- [ ] **Passo 6: Commit** — `git commit -am "feat: signature coloca stem nos cortes"`

### Task 3: Mixer — colar audio no video

**Files:** Create `muntu/mixer.py`

- [ ] **Passo 1: Implementa** (ffmpeg substitui o audio do video)

```python
import subprocess

def mux(video_path: str, audio_path: str, out_path: str):
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path, "-i", audio_path,
        "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
        "-shortest", out_path
    ], check=True)
    return out_path
```

- [ ] **Passo 2: Testa na mao** — roda, abre o mp4, ve se o hit bate nos cortes.
- [ ] **Passo 3: Commit** — `git commit -am "feat: mixer cola audio no video"`

### Task 4: Pipeline — amarrar tudo

**Files:** Create `pipeline.py`

- [ ] **Passo 1: Implementa**

```python
from muntu.analyzer import analyze
from muntu.signature import placement_plan, render_signature
from muntu.mixer import mux

def run(video_path: str, out_path: str = "outputs/scored.mp4",
        stems_dir: str = "assets/stems/default") -> str:
    brief = analyze(video_path)
    plan = placement_plan(brief["cortes"], brief["duracao"])
    sig = render_signature(plan, brief["duracao"], stems_dir)
    sig.export("outputs/_audio.wav", format="wav")
    return mux(video_path, "outputs/_audio.wav", out_path)
```

- [ ] **Passo 2: Roda end-to-end** — `python -c "from pipeline import run; print(run('assets/sample.mp4'))"`. Abre `outputs/scored.mp4`.
- [ ] **Passo 3: Commit** — `git commit -am "feat: pipeline end-to-end (skeleton)"`

### Task 5: Web App — Gradio

**Files:** Create `app.py`

- [ ] **Passo 1: Implementa**

```python
import gradio as gr
from pipeline import run

def score(video):
    return run(video, out_path="outputs/scored.mp4")

demo = gr.Interface(
    fn=score,
    inputs=gr.Video(label="Sobe teu clipe (10-30s)"),
    outputs=gr.Video(label="Com trilha Muntu"),
    title="Muntu Score",
    description="Gera trilha sincronizada aos cortes do video.",
)

if __name__ == "__main__":
    demo.launch()
```

- [ ] **Passo 2: Roda local** — `python app.py` -> abre `http://127.0.0.1:7860`. Sobe o video, ve sair scoreado.
- [ ] **Passo 3: Commit** — `git commit -am "feat: gradio app"`

### Task 6: Deploy — Hugging Face Space (BINARIO HIT)

- [ ] **Passo 1:** Cria um Space em huggingface.co/new-space -> SDK = **Gradio**.
- [ ] **Passo 2:** Adiciona `packages.txt` na raiz com uma linha: `ffmpeg` (o Space instala ffmpeg).
- [ ] **Passo 3:** Adiciona o secret `REPLICATE_API_TOKEN` nas Settings do Space (so vai usar na semana 2, mas ja deixa).
- [ ] **Passo 4:** Sobe o codigo pro Space (git push pro remote do HF). Commita `assets/sample.mp4` e 1 stem pra demo funcionar.
- [ ] **Passo 5:** Espera o build. Abre a URL publica. Sobe um video. **Sai scoreado = BINARIO BATIDO.**

### Task 7: GitHub publico

- [ ] **Passo 1:** Cria repo publico `muntu-score` no GitHub.
- [ ] **Passo 2:** `README.md` minimo: o que e, 1 screenshot/gif, link do HF Space, como rodar local.
- [ ] **Passo 3:** `git remote add origin ...` e `git push -u origin main`.
- [ ] **Passo 4:** Confere: repo publico + Space no ar. **Sonda passou no binario.** O resto e qualidade.

---

## Chunk 2 — Semana 2: Cama-base IA + manifest de stems

Meta: o som deixa de ser "1 hit nos cortes" e ganha uma cama musical sob tudo.

### Task 8: Base Bed via Replicate

**Files:** Create `muntu/base_bed.py`

- [ ] Implementa `gerar_cama(prompt: str, duracao: float) -> AudioSegment` chamando um modelo de musica no Replicate (ex: `meta/musicgen` ou Stable Audio). Input = prompt textual + duracao. Baixa o wav, retorna AudioSegment.
- [ ] Cache: salva por hash do (prompt, duracao) em `outputs/cache/` pra nao pagar 2x.
- [ ] Pipeline: mistura cama (volume baixo) + signature (volume alto) antes do mux: `cama.overlay(sig)`.
- [ ] Testa: roda 1 clipe, escuta — cama embaixo, hits em cima. Commit.

### Task 9: Manifest de stems

**Files:** Create `assets/stems/default/manifest.json`

- [ ] Cura 5-8 stems do teu catalogo (so material TEU/livre — nada de cliente antigo). Coloca em `assets/stems/default/`.
- [ ] `manifest.json`: lista cada stem com `{arquivo, clima, papel}` (papel = hit/pad/perc/riser).
- [ ] `signature.placement_plan` passa a escolher stem por papel (ainda regra simples). Commit.

---

## Chunk 3 — Semana 3: Director + clima + context pack

Meta: a escolha do som passa a depender do VIDEO (clima) e do CONTEXTO (pack). Aqui mora
teu ouvido.

### Task 10: Analise de clima

**Files:** Modify `muntu/analyzer.py`

- [ ] Amostra 1 frame por cena, manda pra um VLM barato (descreve clima -> tags: alegre/tenso/sofisticado/etc). Preenche `brief["cenas"]` com `{start, end, clima, energia}`.
- [ ] Testa: roda em 2 videos diferentes, ve se as tags fazem sentido. Commit.

### Task 11: Music Director + Context Pack

**Files:** Create `muntu/director.py`, `packs/default.json`, `packs/natal.json`

- [ ] `packs/default.json`: regras mapeando clima -> escolha de stem + estilo de prompt da cama-base, pra um contexto publicitario.
- [ ] `director.plano_de_score(brief, pack)`: usa o clima das cenas + o pack pra decidir prompt da cama e quais stems em quais cortes. **Esta e a camada da tua direcao — refina as regras na orelha.**
- [ ] Cria 1 pack extra (`natal.json`) pra provar que troca de contexto. UI ganha um dropdown de pack.
- [ ] Pipeline usa o director no lugar do placement burro. Commit.

### Task 12: Hits frescos

- [ ] Compoe 2-3 hits/elementos novos pros pontos de assinatura que faltam nos packs. Adiciona ao manifest. Commit.

---

## Chunk 4 — Semana 4: Polir + showreel

Meta: o entregavel binario ja existe ha 3 semanas; agora vira peca de portfolio.

### Task 13: Polish

- [ ] Gain staging decente (cama nao abafa, hits nao estouram). Fade in/out. Normaliza saida.
- [ ] README com gif/screenshot bom + 1 paragrafo "como funciona" (vende a engenharia).
- [ ] Trata erro: video sem corte, video longo demais (corta em 30s), formato invalido.

### Task 14: Produzir showreel Muntu

- [ ] Roda a tool em 1-2 clipes publicitarios escolhidos a dedo -> 1-2 pecas boas.
- [ ] Essas pecas viram material das 10 abordagens da Sonda D ([[caminhos/audio]]).
- [ ] Posta sob a marca Muntu (Instagram). Commit final + tag `v1`.

---

## Definition of Done

- [ ] **Binario (semana 1):** repo GitHub publico + HF Space rodando, recebe video e devolve scoreado.
- [ ] **Qualidade (semana 4):** cama IA + teus stems + context pack + 1-2 pecas de showreel sob Muntu.
- [ ] Prazo: **~2026-07-09**. Cobrado pelo check-in agendado do Claude.

## O que a sonda mede (dado, nao criterio)

O binario so testa "voce construiu e publicou". O DADO vem depois: as pecas alimentam as
10 abordagens da Sonda D — quantas respostas a credencial + a tool geram. E: a tool
publicada gera inbound/credibilidade? Ver `Estado e Handoff.md` e `caminhos/audio.md`.
