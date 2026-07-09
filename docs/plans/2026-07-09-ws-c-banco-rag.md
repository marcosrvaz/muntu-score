# WS-C — Banco Supabase + RAG híbrido (camada 3, premium) — Plano de Implementação

> **Para workers agênticos:** REQUIRED SUB-SKILL: use superpowers:executing-plans task a task.
> Leia ANTES: `docs/plans/2026-07-09-arquitetura-learn-ads-master.md` (decisões D1-D10).
> Pré-requisito: commit do `muntu/tags.py` (WS-A Task 1). **NUNCA commite** — testes verdes +
> PARAR e avisar. Escopo: SÓ arquivos novos + `requirements.txt`. NÃO toque em `reader.py`,
> `trilha.py`, `epidemic.py`, `pipeline.py`, `tagueador.py`.
> **Migrations: SÓ via Supabase CLI ou MCP postgres — NUNCA conexão postgres direta.**
> **GATE D10: Tasks 1-5 (infra) podem rodar já; a INGESTÃO EM MASSA do acervo real (Task 6
> passo final) só depois do veredito do spike (WS-B Task 4).**

**Goal:** banco curado de assets (música/SFX/VO) em Supabase + pgvector com retrieval híbrido: filtros SQL + RRF de 2 vetores (text-embed do descritor + CLAP do áudio), incluindo o bridge A→B (draft gerado como query de áudio).

**Architecture:** tabela única `assets` (D5); função Postgres `busca_hibrida` com RRF em SQL puro k=60 (D1), sem índice ANN (D2); `muntu/banco.py` cliente via `supabase-py` (rpc), best-effort; text-embedding via OpenRouter `/api/v1/embeddings` (`openai/text-embedding-3-small`, 1536-dim, mesma key `MUNTU_MOOD_API_KEY` — D4 atualizada); audio-embedding (CLAP `laion/larger_clap_music` 512-dim, D3) num venv dedicado torch-CPU acessado por subprocess — o venv de spike já provou torch CPU liso.

**Tech Stack:** Supabase (Postgres + pgvector ≥0.7), `supabase-py`, OpenRouter embeddings (httpx, já no repo), venv separado com `torch` (CPU) + `transformers` + `librosa` (só CLAP).

## Global Constraints

Herdadas do plano-mestre. Env novos: `SUPABASE_URL`, `SUPABASE_KEY` (service role só local; NUNCA commitado), `MUNTU_EMBED_PYTHON` (python do venv CLAP). Text-embedding usa `MUNTU_MOOD_API_KEY` (OpenRouter, já existe). Supabase = projeto NOVO dedicado (resposta 2 do usuário; o antigo será apagado). Gated: sem env → banco indisponível → fallback silencioso (padrão epidemic).

---

### Task 1: migration — extensão, tabela `assets`, função `busca_hibrida` (RRF)

**Files:**

- Create: `supabase/migrations/20260709000001_assets.sql`

**Interfaces:**

- Produces: tabela `assets`; RPC `busca_hibrida(q_text, q_audio, tipo, filtro_era, so_licenciados, k, n, peso_texto, peso_audio)` → `(id, pointer, titulo, descritor, tags, rrf)`.

- [ ] **Step 1: Escrever a migration**

```sql
-- Banco curado learn-from-ads (plano-mestre 2026-07-09, decisões D1-D5, D8).
-- Tabela ÚNICA multi-tipo: filtro SQL barato antes do blend vetorial.
create extension if not exists vector;

create table if not exists assets (
  id          uuid primary key default gen_random_uuid(),
  asset_type  text not null check (asset_type in ('music', 'sfx', 'vo')),
  source      text not null check (source in ('own', 'artlist', 'epidemic')),
  pointer     text not null,   -- path local (own/artlist) ou 'epidemic:<track_id>' (ponteiro)
  titulo      text not null default '',
  era         text not null default '',
  bpm         int,
  license_ok  boolean not null default false,
  tags        jsonb not null default '{}'::jsonb,   -- tags completas (muntu/tags.py)
  descritor   text not null,                        -- tags.descritor() -> input do text_emb
  text_emb    vector(1536),    -- text-embedding-3-small via OpenRouter (D4): intenção.
                               -- Cobre TODOS incl. epidemic-ponteiro
  audio_emb   vector(512),     -- CLAP larger_clap_music (D3): som. NULL p/ epidemic (D8)
  created_at  timestamptz not null default now(),
  unique (source, pointer)
);

-- RRF em SQL puro (D1): rank-fusion evita normalizar distribuições incompatíveis
-- (cosine de espaços text vs audio). k=60 (Cormack 2009). Sem índice ANN (D2):
-- <10k rows -> seq scan exato, recall 100%.
create or replace function busca_hibrida(
  q_text        vector(1536),
  q_audio       vector(512) default null,
  tipo          text default 'music',
  filtro_era    text default null,
  so_licenciados boolean default false,
  k             int default 60,
  n             int default 10,
  peso_texto    float default 1.0,
  peso_audio    float default 1.0
) returns table (id uuid, pointer text, titulo text, descritor text, tags jsonb, rrf float)
language sql stable as $$
  with base as (
    select a.* from assets a
    where a.asset_type = tipo
      and (filtro_era is null or a.era = filtro_era)
      and (not so_licenciados or a.license_ok)
  ),
  rt as (
    select b.id, row_number() over (order by b.text_emb <=> q_text) as r
    from base b where b.text_emb is not null and q_text is not null
  ),
  ra as (
    select b.id, row_number() over (order by b.audio_emb <=> q_audio) as r
    from base b where b.audio_emb is not null and q_audio is not null
  )
  select b.id, b.pointer, b.titulo, b.descritor, b.tags,
         coalesce(peso_texto / (k + rt.r), 0) + coalesce(peso_audio / (k + ra.r), 0) as rrf
  from base b
  left join rt on rt.id = b.id
  left join ra on ra.id = b.id
  where rt.id is not null or ra.id is not null
  order by rrf desc, b.id
  limit n;
$$;
```

- [ ] **Step 2: Aplicar via Supabase CLI** — `supabase db push` (ou MCP postgres se ativo). NUNCA `psql` direto.

- [ ] **Step 3: Smoke test SQL** (via CLI/MCP): inserir 2 rows fake com vetores literais pequenos? Não — dimensão é 1536/512; usar `select busca_hibrida(null, null)` → 0 rows sem erro; `insert` de 1 row com `text_emb = (select array_fill(0.1, array[1536])::vector(1536))` e conferir que `busca_hibrida(<mesmo vetor>, null)` retorna a row com `rrf > 0`. Limpar a row fake depois.

- [ ] **Step 4: PARAR — usuário confere no dashboard + commita a migration.**

---

### Task 2: venv de embedding de ÁUDIO (CLAP) + script CLI

(Text-embedding NÃO fica aqui — vai via OpenRouter API direto no `banco.py`, Task 3.)

**Files:**

- Create: `scripts/embeddings/README.md`, `scripts/embeddings/requirements.txt`, `scripts/embeddings/embed_audio.py`

**Interfaces:**

- Produces: CLI stdin/stdout-JSON chamado via subprocess por `banco.py`:
  - `embed_audio.py`: stdin `{"paths": ["/abs/a.mp3", ...]}` → stdout `{"vetores": [[...512 floats...]|null, ...]}` (null = arquivo falhou)
- Contrato de erro: falha total → exit code ≠ 0 + mensagem no stderr.

- [ ] **Step 1: `scripts/embeddings/requirements.txt`**

```
torch --index-url https://download.pytorch.org/whl/cpu
transformers
librosa
numpy
```

- [ ] **Step 2: `scripts/embeddings/README.md`** — instruções curtas:

```markdown
# Venv de embeddings (torch CPU — pesado, ISOLADO do venv principal)

python3 -m venv .venv-embed
.venv-embed/bin/pip install -r scripts/embeddings/requirements.txt
export MUNTU_EMBED_PYTHON=$PWD/.venv-embed/bin/python

Modelo baixa no 1º uso: laion/larger_clap_music (~2GB).
Spike 2026-07-08 provou: instala liso, roda CPU. `.venv-embed/` no .gitignore.
```

- [ ] **Step 3: `embed_audio.py`**

```python
"""Audio-embedding CLAP (laion/larger_clap_music, D3): casa por SOM.
Janelas de 10s @48kHz + mean-pool L2-normalizado (prática padrão pra faixa longa).
CLI stdin/stdout-JSON; arquivo que falha -> null na posição (lote não morre)."""
import json
import sys

SR = 48000
JANELA_S = 10


def _embeda(path, model, proc, np, librosa):
    y, _ = librosa.load(path, sr=SR, mono=True)
    passo = SR * JANELA_S
    embs = []
    for i in range(0, max(len(y), 1), passo):
        j = y[i:i + passo]
        if len(j) < SR:            # janela < 1s não carrega sinal útil
            continue
        inputs = proc(audios=j, sampling_rate=SR, return_tensors="pt")
        e = model.get_audio_features(**inputs).detach().numpy()[0]
        embs.append(e / np.linalg.norm(e))
    if not embs:
        return None
    v = np.mean(embs, axis=0)
    return [float(x) for x in v / np.linalg.norm(v)]


def main():
    paths = json.load(sys.stdin)["paths"]
    import librosa
    import numpy as np
    from transformers import ClapModel, ClapProcessor
    model = ClapModel.from_pretrained("laion/larger_clap_music")
    proc = ClapProcessor.from_pretrained("laion/larger_clap_music")
    out = []
    for p in paths:
        try:
            out.append(_embeda(p, model, proc, np, librosa))
        except Exception as e:     # noqa: BLE001 — lote best-effort
            print(f"[embed_audio] {p}: {type(e).__name__}: {e}", file=sys.stderr)
            out.append(None)
    json.dump({"vetores": out}, sys.stdout)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Smoke manual** — criar o venv, `echo '{"paths": ["<um mp3 de outputs/>"]}' | $MUNTU_EMBED_PYTHON scripts/embeddings/embed_audio.py` → 512 floats. Adicionar `.venv-embed/` ao `.gitignore` se ainda não está.

- [ ] **Step 5: PARAR — usuário revisa+commita.**

---

### Task 3: `muntu/banco.py` — cliente, embed-bridge, inserção e busca

**Files:**

- Create: `muntu/banco.py`
- Test: `tests/test_banco.py`
- Modify: `requirements.txt` (adicionar linha `supabase`)

**Interfaces:**

- Consumes: `tags.descritor` / `tags.valida_tags`; RPC `busca_hibrida` (Task 1); CLI CLAP (Task 2); OpenRouter `/api/v1/embeddings` (key `MUNTU_MOOD_API_KEY`).
- Produces:
  - `banco_disponivel() -> bool` (env `SUPABASE_URL` + `SUPABASE_KEY` + lib)
  - `embed_texto(textos: list[str]) -> list[list[float]]` (OpenRouter API, 1536-dim)
  - `embed_audio(paths: list[str]) -> list[list[float] | None]` (subprocess bridge CLAP)
  - `insere_asset(asset_type, source, pointer, tags_dict, titulo="", era="", bpm=None, license_ok=False, audio_path=None) -> str|None` (id; embeda descritor sempre; áudio quando `audio_path`)
  - `busca_hibrida(texto=None, audio_path=None, tipo="music", era=None, so_licenciados=False, n=10, peso_texto=1.0, peso_audio=1.0) -> list[dict]`

- [ ] **Step 1: Testes que falham** (sem rede: monkeypatch no client/subprocess)

```python
"""Banco curado — bridge de embeddings + retrieval híbrido (mocks, sem rede)."""
import json

from muntu import banco


def test_banco_indisponivel_sem_env(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    assert banco.banco_disponivel() is False
    assert banco.busca_hibrida(texto="x") == []      # best-effort: [] sem crash


def test_embed_texto_via_openrouter(monkeypatch):
    class R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [{"index": 1, "embedding": [0.2] * 1536},
                             {"index": 0, "embedding": [0.1] * 1536}]}

    import httpx
    monkeypatch.setenv("MUNTU_MOOD_API_KEY", "k")
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: R())
    out = banco.embed_texto(["a", "b"])
    assert len(out[0]) == 1536
    assert out[0][0] == 0.1                    # reordenado por index


def test_embed_texto_sem_key_retorna_vazio(monkeypatch):
    monkeypatch.delenv("MUNTU_MOOD_API_KEY", raising=False)
    assert banco.embed_texto(["abc"]) == []


def test_embed_audio_via_subprocess(monkeypatch):
    class R:
        returncode = 0
        stdout = json.dumps({"vetores": [[0.1] * 512]})
        stderr = ""
    monkeypatch.setenv("MUNTU_EMBED_PYTHON", "/fake/python")
    monkeypatch.setattr(banco.subprocess, "run", lambda *a, **kw: R())
    assert len(banco.embed_audio(["a.mp3"])[0]) == 512


def test_embed_audio_sem_venv_retorna_vazio(monkeypatch):
    monkeypatch.delenv("MUNTU_EMBED_PYTHON", raising=False)
    assert banco.embed_audio(["a.mp3"]) == []


def test_busca_hibrida_monta_rpc(monkeypatch):
    chamadas = {}

    class FakeClient:
        def rpc(self, nome, params):
            chamadas["nome"], chamadas["params"] = nome, params

            class E:
                def execute(self):
                    class R:
                        data = [{"pointer": "p.mp3", "rrf": 0.03}]
                    return R()
            return E()

    monkeypatch.setattr(banco, "_client", lambda: FakeClient())
    monkeypatch.setattr(banco, "embed_texto", lambda t: [[0.1] * 1536])
    out = banco.busca_hibrida(texto="80s ballad", era="1980s", n=5)
    assert chamadas["nome"] == "busca_hibrida"
    assert chamadas["params"]["filtro_era"] == "1980s"
    assert chamadas["params"]["q_audio"] is None
    assert out[0]["pointer"] == "p.mp3"
```

- [ ] **Step 2: Rodar e ver falhar** — `pytest tests/test_banco.py -v` → FAIL.

- [ ] **Step 3: Implementar `muntu/banco.py`**

```python
"""Banco curado learn-from-ads — Supabase + pgvector, retrieval híbrido (RRF).

2 vetores complementares por asset: text-embed do descritor (INTENÇÃO — cobre tudo,
incl. Epidemic-ponteiro) + CLAP do áudio (SOM — só own/artlist, de-riska o tagueador:
tag errada, som ainda acha). Fusão por RRF na função Postgres busca_hibrida (D1).
Text-embed via OpenRouter /api/v1/embeddings (mesma key do reader — D4); audio-embed
(CLAP) num venv dedicado torch-CPU (MUNTU_EMBED_PYTHON) via subprocess — torch não
entra no venv principal. Gated em SUPABASE_URL/SUPABASE_KEY; best-effort:
indisponível/falha -> []/None, pipeline nunca cai por causa do banco (padrão epidemic).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from muntu import tags as tags_mod

_TIMEOUT_EMBED = 600   # 1º uso baixa modelo (~2GB) — generoso de propósito


def banco_disponivel() -> bool:
    if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY")):
        return False
    try:
        import supabase  # noqa: F401
        return True
    except ImportError:
        return False


def _client():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def _roda_embed(script: str, payload: dict) -> list:
    """Bridge pro venv de embeddings. [] se venv não configurado/falha (best-effort)."""
    py = os.environ.get("MUNTU_EMBED_PYTHON")
    if not py:
        return []
    try:
        r = subprocess.run(
            [py, os.path.join("scripts", "embeddings", script)],
            input=json.dumps(payload), capture_output=True, text=True,
            timeout=_TIMEOUT_EMBED,
        )
        if r.returncode != 0:
            print(f"[muntu] {script} falhou: {r.stderr[-500:]}", file=sys.stderr)
            return []
        return json.loads(r.stdout)["vetores"]
    except Exception as e:                     # noqa: BLE001 — best-effort
        print(f"[muntu] {script} indisponivel ({type(e).__name__}: {e})", file=sys.stderr)
        return []


EMBED_URL = "https://openrouter.ai/api/v1/embeddings"
EMBED_MODEL = "openai/text-embedding-3-small"   # 1536-dim (D4)


def embed_texto(textos: list[str]) -> list[list[float]]:
    """Text-embedding via OpenRouter (endpoint OpenAI-compat, MESMA key do reader —
    zero key nova, zero modelo local). [] se key ausente/falha (best-effort)."""
    key = os.environ.get("MUNTU_MOOD_API_KEY")
    if not key or not textos:
        return []
    try:
        import httpx
        r = httpx.post(EMBED_URL, headers={"Authorization": f"Bearer {key}"},
                       json={"model": EMBED_MODEL, "input": textos}, timeout=60.0)
        r.raise_for_status()
        data = sorted(r.json()["data"], key=lambda d: d["index"])
        return [d["embedding"] for d in data]
    except Exception as e:                     # noqa: BLE001 — best-effort
        print(f"[muntu] embed_texto falhou ({type(e).__name__}: {e})", file=sys.stderr)
        return []


def embed_audio(paths: list[str]) -> list:
    return _roda_embed("embed_audio.py", {"paths": paths})


def insere_asset(asset_type: str, source: str, pointer: str, tags_dict: dict,
                 titulo: str = "", era: str = "", bpm=None, license_ok: bool = False,
                 audio_path: str | None = None):
    """Insere/atualiza 1 asset (upsert em source+pointer). Descritor+text_emb sempre;
    audio_emb quando há áudio local (own/artlist). None se banco/embeds indisponíveis."""
    if not banco_disponivel():
        return None
    t = tags_mod.valida_tags(tags_dict, "music" if asset_type == "music" else asset_type)
    desc = tags_mod.descritor(t, "music" if asset_type == "music" else asset_type)
    vt = embed_texto([desc])
    if not vt:
        return None
    va = None
    if audio_path:
        vs = embed_audio([audio_path])
        va = vs[0] if vs else None
    try:
        r = _client().table("assets").upsert({
            "asset_type": asset_type, "source": source, "pointer": pointer,
            "titulo": titulo, "era": era or t.get("era", ""), "bpm": bpm or t.get("bpm"),
            "license_ok": license_ok, "tags": t, "descritor": desc,
            "text_emb": vt[0], "audio_emb": va,
        }, on_conflict="source,pointer").execute()
        return r.data[0]["id"] if r.data else None
    except Exception as e:                     # noqa: BLE001 — best-effort
        print(f"[muntu] insere_asset falhou ({type(e).__name__}: {e})", file=sys.stderr)
        return None


def busca_hibrida(texto: str | None = None, audio_path: str | None = None,
                  tipo: str = "music", era: str | None = None,
                  so_licenciados: bool = False, n: int = 10,
                  peso_texto: float = 1.0, peso_audio: float = 1.0) -> list[dict]:
    """Retrieval híbrido: texto casa INTENÇÃO, áudio casa SOM, RRF funde (no Postgres).
    audio_path é o bridge A→B (D9): o draft gerado é a query de áudio. [] best-effort."""
    if not banco_disponivel() or not (texto or audio_path):
        return []
    q_text = None
    if texto:
        vt = embed_texto([texto])
        q_text = vt[0] if vt else None
    q_audio = None
    if audio_path:
        va = embed_audio([audio_path])
        q_audio = va[0] if va and va[0] else None
    if q_text is None and q_audio is None:
        return []
    try:
        r = _client().rpc("busca_hibrida", {
            "q_text": q_text, "q_audio": q_audio, "tipo": tipo, "filtro_era": era,
            "so_licenciados": so_licenciados, "n": n,
            "peso_texto": peso_texto, "peso_audio": peso_audio,
        }).execute()
        return r.data or []
    except Exception as e:                     # noqa: BLE001 — best-effort
        print(f"[muntu] busca_hibrida falhou ({type(e).__name__}: {e})", file=sys.stderr)
        return []
```

Nota: RPC com `q_text=null` exige cast — se o supabase-py reclamar de vector null, mandar `q_text` como lista vazia NÃO serve; usar sobrecarga: sempre mandar `q_text` (buscar só por áudio é caso raro; quando acontecer, gerar `q_text` do descritor vazio é aceitável) — documentar o que for observado.

- [ ] **Step 4: Rodar** — `pytest tests/test_banco.py -v` → PASS; `pytest tests/` → verde.

- [ ] **Step 5: PARAR — usuário revisa+commita.**

---

### Task 4: `banco.popula_beds` — plugin no encanamento PIN camada 2

**Files:**

- Modify: `muntu/banco.py`
- Test: `tests/test_banco.py`

**Interfaces:**

- Consumes: contrato de `epidemic.popula_beds` (mesma forma: muta `timeline["partes"]` setando `bed_file`). Partes com tags ricas (WS-A): `ironia`, `cultura`, `instrumentacao`.
- Produces: `popula_beds(timeline: dict, so_score: bool = True) -> None`. Pointer `epidemic:<id>` NÃO vira bed_file aqui (sem áudio local) — só own/artlist com path existente.

- [ ] **Step 1: Testes que falham**

```python
def test_popula_beds_seta_bed_file(monkeypatch, tmp_path):
    mp3 = tmp_path / "faixa.mp3"
    mp3.write_bytes(b"x")
    monkeypatch.setattr(banco, "banco_disponivel", lambda: True)
    monkeypatch.setattr(banco, "busca_hibrida",
                        lambda **kw: [{"pointer": str(mp3), "rrf": 0.03}])
    tl = {"era": "1980s", "partes": [
        {"tipo": "score", "clima": "romantic", "mood": "cheesy ballad",
         "ironia": "kitsch", "start": 0.0, "end": 10.0},
        {"tipo": "diegetic", "clima": "joyful", "start": 10.0, "end": 20.0},
    ]}
    banco.popula_beds(tl)
    assert tl["partes"][0]["bed_file"] == str(mp3)
    assert "bed_file" not in tl["partes"][1]          # so_score default


def test_popula_beds_ignora_ponteiro_epidemic(monkeypatch):
    monkeypatch.setattr(banco, "banco_disponivel", lambda: True)
    monkeypatch.setattr(banco, "busca_hibrida",
                        lambda **kw: [{"pointer": "epidemic:abc123", "rrf": 0.03}])
    tl = {"partes": [{"tipo": "score", "clima": "epic", "mood": "big", "start": 0, "end": 9}]}
    banco.popula_beds(tl)
    assert "bed_file" not in tl["partes"][0]          # ponteiro sem áudio local
```

- [ ] **Step 2: Rodar e ver falhar.**

- [ ] **Step 3: Implementar** (acrescentar em `banco.py`)

```python
def _query_da_parte(parte: dict, era_filme: str = "") -> str:
    """Parte da timeline -> texto de query (mesmo vocabulário do descritor de ingestão:
    consistência query<->documento é o que faz o text-embed casar)."""
    return tags_mod.descritor({
        "era": era_filme, "registro": parte.get("mood") or parte.get("clima") or "",
        "ironia": parte.get("ironia"), "cultura": parte.get("cultura") or "",
        "funcao": parte.get("papel") or "",
        "instrumentacao": parte.get("instrumentacao") or [],
    })


def popula_beds(timeline: dict, so_score: bool = True) -> None:
    """A->B via banco curado: MESMO contrato de epidemic.popula_beds (muta partes
    setando bed_file -> reusa o encanamento PIN camada 2 de trilha.py, zero mudança lá).
    Ponteiro epidemic (sem áudio local) não vira bed aqui. Best-effort por parte."""
    if not banco_disponivel():
        return
    era = (timeline.get("era") or "").strip()
    for parte in timeline.get("partes") or []:
        if so_score and parte.get("tipo") == "diegetic":
            continue
        if parte.get("bed_file"):              # PIN do usuário vence sempre
            continue
        hits = busca_hibrida(texto=_query_da_parte(parte, era), tipo="music", n=3)
        for h in hits:
            p = h.get("pointer") or ""
            if not p.startswith("epidemic:") and os.path.exists(p):
                parte["bed_file"] = p
                break
```

- [ ] **Step 4: Rodar** — `pytest tests/test_banco.py -v` → PASS; `pytest tests/` → verde.

- [ ] **Step 5: PARAR — usuário revisa+commita.** (Integração no `pipeline.run` fica pra depois do veredito do spike — decisão de UI/flag junto com o usuário; NÃO mexer em pipeline.py neste WS.)

---

### Task 5: bridge A→B — draft gerado como query de áudio (D9)

**Files:**

- Modify: `muntu/banco.py`
- Test: `tests/test_banco.py`

**Interfaces:**

- Produces: `busca_por_draft(draft_path: str, texto: str | None = None, n: int = 5) -> list[dict]` — CLAP do draft + (opcional) texto, RRF funde; é "a geração A guia o retrieval de B".

- [ ] **Step 1: Teste que falha**

```python
def test_busca_por_draft_passa_audio(monkeypatch):
    visto = {}

    def fake_busca(**kw):
        visto.update(kw)
        return [{"pointer": "real.mp3"}]

    monkeypatch.setattr(banco, "busca_hibrida", fake_busca)
    out = banco.busca_por_draft("/tmp/draft.mp3", texto="80s ballad")
    assert visto["audio_path"] == "/tmp/draft.mp3"
    assert visto["peso_audio"] > visto["peso_texto"]   # o SOM do draft manda
    assert out[0]["pointer"] == "real.mp3"
```

- [ ] **Step 2: Rodar e ver falhar.**

- [ ] **Step 3: Implementar**

```python
def busca_por_draft(draft_path: str, texto: str | None = None, n: int = 5) -> list[dict]:
    """Bridge A->B (D9): o draft que a geração A criou (e que ACERTA o brief) vira a
    query de áudio — CLAP acha a faixa REAL mais parecida no banco. peso_audio > texto:
    quem manda é o SOM que o usuário já aprovou, o texto só desempata."""
    return busca_hibrida(texto=texto, audio_path=draft_path, tipo="music", n=n,
                         peso_texto=0.5, peso_audio=1.0)
```

- [ ] **Step 4: Rodar** — verde. **Step 5: PARAR — usuário revisa+commita.**

---

### Task 6: ingestão — `scripts/ingere_assets.py` (own/artlist + epidemic-ponteiro)

**Files:**

- Create: `scripts/ingere_assets.py`

**Interfaces:**

- Consumes: `banco.insere_asset`, `tagueador.tagueia_ad` NÃO (áudio puro não é ad); tags manuais via sidecar JSON.
- Produces: CLI de ingestão em lote.

- [ ] **Step 1: Implementar**

```python
"""Ingestão do banco curado. Duas fontes:

1) Diretório de áudio local (own/artlist): cada faixa.mp3 com sidecar faixa.json
   (tags no schema TAGS_MUSICA de muntu/tags.py, escritas na curadoria) ->
   text_emb (descritor) + audio_emb (CLAP). Sem sidecar -> PULA e loga (curadoria
   é obrigatória: banco mal-etiquetado = lixo bem-organizado, spec §2.7).
2) --epidemic <json>: lista [{track_id, titulo, tags...}] -> ponteiro só-texto (D8).

Uso:
  python scripts/ingere_assets.py --dir <pasta_mp3> --source own [--license-ok]
  python scripts/ingere_assets.py --epidemic <curados.json>

GATE D10: rodar em MASSA só depois do veredito do spike (WS-B).
"""
import argparse
import glob
import json
import os

from muntu import banco


def ingere_dir(pasta: str, source: str, license_ok: bool):
    ok = pulados = 0
    for mp3 in sorted(glob.glob(os.path.join(pasta, "**", "*.mp3"), recursive=True)):
        sidecar = os.path.splitext(mp3)[0] + ".json"
        if not os.path.exists(sidecar):
            print(f"[ingere] SEM SIDECAR (pulado): {mp3}")
            pulados += 1
            continue
        with open(sidecar, encoding="utf-8") as f:
            t = json.load(f)
        rid = banco.insere_asset("music", source, mp3, t,
                                 titulo=os.path.basename(mp3), license_ok=license_ok,
                                 audio_path=mp3)
        print(f"[ingere] {'ok' if rid else 'FALHOU'}: {mp3}")
        ok += 1 if rid else 0
    print(f"[ingere] {ok} inseridos, {pulados} sem sidecar")


def ingere_epidemic(path: str):
    with open(path, encoding="utf-8") as f:
        faixas = json.load(f)
    for fx in faixas:
        rid = banco.insere_asset("music", "epidemic", f"epidemic:{fx['track_id']}",
                                 fx.get("tags") or {}, titulo=fx.get("titulo", ""))
        print(f"[ingere] {'ok' if rid else 'FALHOU'}: epidemic:{fx['track_id']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("--source", default="own", choices=["own", "artlist"])
    ap.add_argument("--license-ok", action="store_true")
    ap.add_argument("--epidemic")
    args = ap.parse_args()
    if args.dir:
        ingere_dir(args.dir, args.source, args.license_ok)
    if args.epidemic:
        ingere_epidemic(args.epidemic)
```

- [ ] **Step 2: Smoke com 2-3 faixas de `outputs/`** (sidecars escritos à mão) → conferir rows no dashboard + `busca_hibrida` de ouvido: query "cheesy 80s ballad saxophone" retorna a faixa certa primeiro.

- [ ] **Step 3: PARAR — usuário revisa+commita. Ingestão EM MASSA do acervo real: SÓ após veredito do spike (GATE D10).**
