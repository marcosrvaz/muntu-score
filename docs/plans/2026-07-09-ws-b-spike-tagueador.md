# WS-B — Spike do tagueador (camada 2, o CRUX) — Plano de Implementação

> **Para workers agênticos:** REQUIRED SUB-SKILL: use superpowers:executing-plans task a task.
> Leia ANTES: `docs/plans/2026-07-09-arquitetura-learn-ads-master.md`. Pré-requisito: commit
> do `muntu/tags.py` (WS-A Task 1) no main. **NUNCA commite** — testes verdes + PARAR e avisar.
> Escopo: SÓ arquivos novos listados aqui. NÃO toque em `muntu/reader.py`, `trilha.py`,
> `epidemic.py`, `banco.py` nem nada de outro workstream.

**Goal:** provar (ou refutar) que um VLM/áudio-model lê o registro FINO de um comercial real — ironia, cultura, instrumentação, traços de VO — no tag-schema. Se não ler, banco+RAG não adiantam (spec §2.7). Deliverable: JSONs de 3-4 ads reais pro usuário julgar de ouvido/olho.

**Architecture:** `muntu/tagueador.py` reusa a infra de visão do repo (`mood.montagem_do_filme` pra vídeo) + envia o ÁUDIO do ad (wav via ffmpeg, base64) pro mesmo Gemini 2.5 Pro via OpenRouter — VO/SFX são análise de áudio, não de frame (spec §2.2). Saída normalizada por `tags.valida_tags`. Script `scripts/spike_tagueador.py` roda o lote e gera relatório.

**Tech Stack:** Python 3, httpx (já no repo via reader), ffmpeg (já usado em trilha/mixer), pytest.

## Global Constraints

Herdadas do plano-mestre. Gates: `MUNTU_MOOD_API_KEY` (mesmo do reader). Best-effort: sem key/falha → `{}`. PT-BR, docstrings de porquê.

---

### Task 1: esqueleto do tagueador + prompt de MÚSICA (vídeo)

**Files:**

- Create: `muntu/tagueador.py`
- Test: `tests/test_tagueador.py`

**Interfaces:**

- Consumes: `mood.montagem_do_filme(video_path, cortes, duracao)`, `mood._cenas_de_cortes`, `mood._parse_json`, `tags.valida_tags`.
- Produces: `tagueia_musica(video_path, cortes, duracao) -> list[dict]` (uma entrada por parte musical detectada, cada uma = `TAGS_MUSICA` validada + `span` texto livre); `_normaliza_musica(data) -> list[dict]` (testável sem rede).

- [ ] **Step 1: Testes que falham**

```python
"""Tagueador — VLM/audio-model etiqueta ads REAIS no tag-schema (spike do crux)."""
from muntu import tagueador


def test_normaliza_musica_valida_cada_parte():
    data = {"partes": [
        {"span": "opening party", "era": "1980s", "registro": "cheesy synth pop",
         "ironia": "KITSCH", "cultura": "brega", "instrumentacao": ["synth", "sax"],
         "mode": "major", "bpm": 118},
        {"span": "payoff", "registro": "quirky pizzicato", "ironia": "banana"},
    ]}
    out = tagueador._normaliza_musica(data)
    assert len(out) == 2
    assert out[0]["ironia"] == "kitsch" and out[0]["bpm"] == 118
    assert out[1]["ironia"] == "sincero"           # enum inválido -> default
    assert out[0]["span"] == "opening party"


def test_normaliza_musica_lixo_nao_levanta():
    assert tagueador._normaliza_musica({}) == []
    assert tagueador._normaliza_musica({"partes": ["x", None]}) == []
```

- [ ] **Step 2: Rodar e ver falhar** — `pytest tests/test_tagueador.py -v` → FAIL (módulo não existe).

- [ ] **Step 3: Implementar `muntu/tagueador.py`**

```python
"""Tagueador — LLM/VLM etiqueta comerciais REAIS no tag-schema (learn-from-ads).

O "aprendizado" do sistema É a extração: nada de treinar modelo — o VLM assiste a
montagem (música/cena) e o áudio-model OUVE o ad (SFX/VO) e devolvem tags no schema
de muntu/tags.py. Este módulo é o SPIKE do crux (spec §2.7): validar que o modelo lê
registro fino (ironia, cultura, traço de voz) ANTES de construir banco. Reusa a infra
de visão de mood.py; gated na mesma key. Best-effort: falha -> [] / {}.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile

from muntu import mood, tags

MAX_TOKENS = 16000


PROMPT_MUSICA = (
    "You are a MUSIC SUPERVISOR analyzing ONE real TV commercial as a montage of N scenes "
    "labeled S1..SN (chronological). Your job is to TAG the music actually used, part by "
    "part, in a fixed schema — this builds a reference library of how real ads score story.\n"
    "For each musical part (a stretch with one musical treatment) return:\n"
    "  - span: which scenes it covers, free text (e.g. \"S1-S3, the party opening\").\n"
    "  - era: the SOUND's period (\"1980s\", \"1960s\", \"modern\").\n"
    "  - registro: short specific register/genre description of what you HEAR implied by "
    "the footage (\"cheesy 80s power ballad\", \"quirky comedic pizzicato\").\n"
    "  - ironia: \"sincero\" (straight emotion) | \"kitsch\" (deliberately cheesy/campy) | "
    "\"deadpan\" (straight music AGAINST absurdity) | \"parodia\" (mocks a genre).\n"
    "  - cultura: cultural/regional reference (\"brega\", \"bossa nova\", \"balkan brass\", "
    "\"surf rock\") or \"\".\n"
    "  - funcao: setup | build | payoff | reveal | transicao | assinatura.\n"
    "  - instrumentacao: up to 3 signature instruments.\n"
    "  - mode: major | minor | ambiguous.  - bpm: estimated int or null.\n"
    'Return ONLY JSON: {"partes": [{"span": "...", "era": "...", "registro": "...", '
    '"ironia": "...", "cultura": "...", "funcao": "...", "instrumentacao": [...], '
    '"mode": "...", "bpm": <int|null>}]}'
)


def disponivel() -> bool:
    """Mesmo gate do reader/mood (le o filme)."""
    return mood.clima_disponivel()


def _chama(content: list, max_tokens: int = MAX_TOKENS) -> dict:
    """POST OpenRouter (mesmo backend do reader) com content multimodal arbitrário."""
    import httpx
    r = httpx.post(
        url=mood.MOOD_URL,
        headers={"Authorization": f"Bearer {os.environ['MUNTU_MOOD_API_KEY']}"},
        json={"model": mood.MODEL, "max_tokens": max_tokens,
              "messages": [{"role": "user", "content": content}]},
        timeout=240.0,
    )
    r.raise_for_status()
    return mood._parse_json(r.json()["choices"][0]["message"]["content"])


def _normaliza_musica(data: dict) -> list[dict]:
    """Saída do VLM -> lista de TAGS_MUSICA validadas (+span). Item ilegível cai fora."""
    out = []
    for p in (data.get("partes") or []) if isinstance(data, dict) else []:
        if not isinstance(p, dict):
            continue
        t = tags.valida_tags(p, "music")
        t["span"] = (p.get("span") or "").strip()
        out.append(t)
    return out


def tagueia_musica(video_path: str, cortes: list[float], duracao: float) -> list[dict]:
    """Ad real -> tags de música por parte. [] se indisponível/falha (best-effort)."""
    if not disponivel():
        return []
    try:
        m = mood.montagem_do_filme(video_path, cortes, duracao)
        if m is None:
            return []
        b64 = base64.standard_b64encode(m).decode("utf-8")
        return _normaliza_musica(_chama([
            {"type": "text", "text": PROMPT_MUSICA},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ]))
    except Exception as e:                     # noqa: BLE001 — best-effort
        import sys
        print(f"[muntu] tagueador musica falhou ({type(e).__name__}: {e})", file=sys.stderr)
        return []
```

- [ ] **Step 4: Rodar** — `pytest tests/test_tagueador.py -v` → PASS; `pytest tests/` → verde.

- [ ] **Step 5: PARAR — usuário revisa+commita.**

---

### Task 2: extração de áudio + tagueamento de SFX e VO (análise de ÁUDIO)

**Files:**

- Modify: `muntu/tagueador.py`
- Test: `tests/test_tagueador.py`

**Interfaces:**

- Produces: `tagueia_audio(video_path) -> dict` com `{"sfx": TAGS_SFX validado, "vo": TAGS_VO validado | None}` (`vo=None` quando o ad não tem locução); `_extrai_wav(video_path) -> str` (path temp, 16kHz mono — suficiente pra análise de fala/SFX e barato de subir); `_normaliza_audio(data) -> dict`.

- [ ] **Step 1: Testes que falham**

```python
def test_normaliza_audio_valida_sfx_e_vo():
    data = {"sfx": {"ambiencia": "indoor party", "eventos": ["glass clink", ""],
                    "assinatura": "cork pop"},
            "vo": {"genero": "male", "idade": "middle-aged", "tom": "deadpan-comico",
                   "timbre": "warm", "pace": "slow", "sotaque": "neutro BR", "energia": 2}}
    out = tagueador._normaliza_audio(data)
    assert out["sfx"]["eventos"] == ["glass clink"]
    assert out["vo"]["tom"] == "deadpan-comico"


def test_normaliza_audio_sem_vo():
    out = tagueador._normaliza_audio({"sfx": {"ambiencia": "street"}, "vo": None})
    assert out["vo"] is None
    assert out["sfx"]["ambiencia"] == "street"
    assert tagueador._normaliza_audio("lixo") == {"sfx": None, "vo": None}
```

- [ ] **Step 2: Rodar e ver falhar.**

- [ ] **Step 3: Implementar** (acrescentar em `tagueador.py`)

```python
PROMPT_AUDIO = (
    "You are a SOUND DESIGNER + VOICE CASTING DIRECTOR listening to the full audio of ONE "
    "real TV commercial. Tag what you HEAR (ignore the music — another pass covers it):\n"
    "1) sfx: {\"ambiencia\": \"<bed/room tone, e.g. 'indoor party crowd'>\", "
    "\"eventos\": [up to 3 short foley/event sounds], \"assinatura\": \"<the ONE sound that "
    "lands the climax, or ''>\"}.\n"
    "2) vo: the voiceover/narration VOICE (null if there is NO spoken voiceover): "
    "{\"genero\": \"male|female|neutral\", \"idade\": \"young adult|middle-aged|elderly\", "
    "\"tom\": \"autoritario|caloroso|hype|luxo-sussurro|deadpan-comico\", "
    "\"timbre\": \"deep|warm|gravelly|smooth|raspy|breathy\", "
    "\"pace\": \"fast|measured|slow\", \"sotaque\": \"<accent, e.g. 'neutro BR'>\", "
    "\"energia\": <1-5>}.\n"
    'Return ONLY JSON: {"sfx": {...}, "vo": {...}|null}'
)


def _extrai_wav(video_path: str) -> str:
    """Trilha de áudio do ad -> wav 16kHz mono temp (análise de fala/SFX não precisa de
    mais, e o payload base64 fica pequeno). Chamador apaga."""
    fd, dst = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    subprocess.run(["ffmpeg", "-y", "-i", video_path, "-ac", "1", "-ar", "16000", dst],
                   check=True, capture_output=True)
    return dst


def _normaliza_audio(data) -> dict:
    """Saída do modelo -> {sfx, vo} validados. vo null preservado (ad sem locução)."""
    if not isinstance(data, dict):
        return {"sfx": None, "vo": None}
    sfx = tags.valida_tags(data["sfx"], "sfx") if isinstance(data.get("sfx"), dict) else None
    vo = tags.valida_tags(data["vo"], "vo") if isinstance(data.get("vo"), dict) else None
    return {"sfx": sfx, "vo": vo}


def tagueia_audio(video_path: str) -> dict:
    """Ad real -> tags de SFX + VO OUVINDO o áudio (não os frames — traço de voz é
    análise de áudio, spec §2.2). {"sfx": None, "vo": None} se indisponível/falha."""
    if not disponivel():
        return {"sfx": None, "vo": None}
    wav = None
    try:
        wav = _extrai_wav(video_path)
        with open(wav, "rb") as f:
            b64 = base64.standard_b64encode(f.read()).decode("utf-8")
        return _normaliza_audio(_chama([
            {"type": "text", "text": PROMPT_AUDIO},
            {"type": "input_audio", "input_audio": {"data": b64, "format": "wav"}},
        ]))
    except Exception as e:                     # noqa: BLE001 — best-effort
        import sys
        print(f"[muntu] tagueador audio falhou ({type(e).__name__}: {e})", file=sys.stderr)
        return {"sfx": None, "vo": None}
    finally:
        if wav and os.path.exists(wav):
            os.remove(wav)
```

Nota: `input_audio` é o formato OpenRouter/OpenAI-compat pra áudio inline; Gemini 2.5 Pro aceita áudio. Se o endpoint recusar (400), fallback documentado: reduzir a 8kHz ou cortar a 60s — registrar o que aconteceu no relatório do spike, NÃO silenciar.

- [ ] **Step 4: Rodar** — `pytest tests/test_tagueador.py -v` → PASS; `pytest tests/` → verde.

- [ ] **Step 5: PARAR — usuário revisa+commita.**

---

### Task 3: agregador `tagueia_ad` + script do spike

**Files:**

- Modify: `muntu/tagueador.py`
- Create: `scripts/spike_tagueador.py`
- Test: `tests/test_tagueador.py`

**Interfaces:**

- Produces: `tagueia_ad(video_path) -> dict` = `{"video": path, "musica": [...], "sfx": {...}|None, "vo": {...}|None}`. É o contrato que o WS-C (ingestão) e a camada 4 vão consumir.

- [ ] **Step 1: Teste que falha** (monkeypatch nas duas funções pra não bater rede)

```python
def test_tagueia_ad_agrega(monkeypatch):
    monkeypatch.setattr(tagueador, "tagueia_musica", lambda *a: [{"registro": "x"}])
    monkeypatch.setattr(tagueador, "tagueia_audio",
                        lambda *a: {"sfx": {"ambiencia": "y"}, "vo": None})
    monkeypatch.setattr(tagueador, "_analisa_video", lambda p: ([1.0], 10.0))
    out = tagueador.tagueia_ad("fake.mp4")
    assert out["musica"] == [{"registro": "x"}]
    assert out["sfx"]["ambiencia"] == "y" and out["vo"] is None
```

- [ ] **Step 2: Rodar e ver falhar.**

- [ ] **Step 3: Implementar**

```python
def _analisa_video(video_path: str) -> tuple[list[float], float]:
    """Cortes+duração via analyzer (import tardio: cv2/scenedetect pesados)."""
    from muntu.analyzer import analyze
    brief = analyze(video_path)
    return brief["cortes"], brief["duracao"]


def tagueia_ad(video_path: str) -> dict:
    """Ad completo -> tags de música (vídeo) + SFX/VO (áudio). O deliverable do spike."""
    cortes, duracao = _analisa_video(video_path)
    audio = tagueia_audio(video_path)
    return {"video": video_path,
            "musica": tagueia_musica(video_path, cortes, duracao),
            "sfx": audio["sfx"], "vo": audio["vo"]}
```

E `scripts/spike_tagueador.py`:

```python
"""Spike do crux (spec §2.7): taguear 3-4 ads reais pro usuário julgar de ouvido/olho.

Uso: python scripts/spike_tagueador.py <ad1.mp4> <ad2.mp4> ...
Saída: outputs/spike_tags/<stem>.json por ad + outputs/spike_tags/RELATORIO.md
Julgamento (usuário): o modelo leu ironia/cultura/traço de voz FINO? Se não, calibrar
prompt e re-rodar; se nem calibrado ler, o banco (WS-C) não deve ser populado em massa.
"""
import json
import os
import sys

from muntu import tagueador


def main(paths):
    os.makedirs("outputs/spike_tags", exist_ok=True)
    linhas = ["# Spike tagueador — julgamento de registro fino\n"]
    for p in paths:
        r = tagueador.tagueia_ad(p)
        stem = os.path.splitext(os.path.basename(p))[0]
        dst = f"outputs/spike_tags/{stem}.json"
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
        linhas.append(f"\n## {stem}\n")
        for m in r["musica"]:
            linhas.append(f"- musica [{m.get('span', '')}]: {m['registro']} | ironia={m['ironia']}"
                          f" | cultura={m['cultura'] or '—'} | instr={m['instrumentacao']}")
        vo = r["vo"]
        linhas.append(f"- vo: {vo}" if vo else "- vo: (sem locução)")
        linhas.append(f"- sfx: {r['sfx']}")
        print(f"[spike] {stem} -> {dst}")
    with open("outputs/spike_tags/RELATORIO.md", "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))
    print("[spike] relatório: outputs/spike_tags/RELATORIO.md")


if __name__ == "__main__":
    main(sys.argv[1:])
```

- [ ] **Step 4: Rodar** — `pytest tests/test_tagueador.py -v` → PASS; `pytest tests/` → verde.

- [ ] **Step 5: PARAR — usuário revisa+commita.**

---

### Task 4: corpus do canal do usuário + rodar o spike

Corpus = canal YouTube do usuário (resposta 3, 2026-07-09): `https://www.youtube.com/@muntu_co` — e o usuário quer LEITURA AMPLA (>>10 ads). Fluxo em 2 estágios: (a) **calibração** = amostra pequena julgada por humano (barato de iterar prompt); (b) **lote amplo** = corpus inteiro tagueado com o prompt calibrado. Ads externos de referência entram via `corpus/urls.txt` (uma URL por linha) — mesmo yt-dlp.

- [ ] **Baixar o corpus** (yt-dlp; instalar no venv se faltar):

```bash
mkdir -p corpus/ads
yt-dlp -f "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b" \
  -o "corpus/ads/%(upload_date)s_%(title).60s.%(ext)s" \
  --restrict-filenames \
  "https://www.youtube.com/@muntu_co/videos"
```

Adicionar `corpus/` ao `.gitignore` (vídeo não entra no repo).

- [ ] **Ads externos (opcional, leitura ampla):** se o usuário listar referências em `corpus/urls.txt`, baixar com `yt-dlp -a corpus/urls.txt -o "corpus/ads/ext_%(title).60s.%(ext)s" --restrict-filenames -f "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b"`. Uso interno de análise (não redistribuir).
- [ ] **Estágio (a) — calibração:** amostra de 8-12 ads variados do corpus (mix: comédia kitsch/brega, sério/sincero, VO forte, cultura marcada). `python scripts/spike_tagueador.py corpus/ads/<escolhidos...>` → JSONs + RELATORIO.md.
- [ ] **Julgamento do usuário (o gate D10):** ironia certa? cultura certa? VO com traço fino (tom/pace/sotaque)? Errou → calibrar SÓ os prompts (`PROMPT_MUSICA`/`PROMPT_AUDIO`) e re-rodar a MESMA amostra (regra: output errado = calibra o reader/tagueador, nunca o apply). Iterar até o usuário aprovar.
- [ ] Veredito registrado no RELATORIO.md à mão.
- [ ] **Estágio (b) — lote amplo (só com prompt aprovado):** `python scripts/spike_tagueador.py corpus/ads/*.mp4` no corpus INTEIRO. É 2 chamadas Gemini/ad (vídeo + áudio) — rodar em lote sequencial, best-effort por ad (falhou 1, segue). Os JSONs de `outputs/spike_tags/` viram o dataset learn-from-ads: insumo da ingestão do WS-C e da futura calibração do reader. **Aprovação do estágio (a) também destrava a ingestão em massa do WS-C.**
