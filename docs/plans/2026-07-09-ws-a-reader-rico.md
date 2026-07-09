# WS-A — Reader rico + tag-schema (camada 1, wow) — Plano de Implementação

> **Para workers agênticos:** REQUIRED SUB-SKILL: use superpowers:executing-plans task a task.
> Leia ANTES: `docs/plans/2026-07-09-arquitetura-learn-ads-master.md` (constraints globais +
> tag-schema canônico). Checkboxes (`- [ ]`) para tracking. **NUNCA commite** — checkpoint =
> testes verdes + PARAR e avisar o usuário.

**Goal:** o reader passa a emitir tags ricas por parte (ironia/cultura/instrumentação) e a geração A compõe o prompt a partir delas — a comédia deixa de virar "romantic sincero" (bug Pringles). ZERO banco.

**Architecture:** `muntu/tags.py` (schema canônico, criado verbatim do plano-mestre) → `reader.PROMPT` ganha 3 dimensões + viés cômico obrigatório → `_normaliza` valida os campos novos → `trilha._prompt_da_parte` compõe cultura/instrumentação e troca o kitsch binário (`comico`) pelo eixo `ironia` → `epidemic` usa ironia pra corrigir o mood da busca.

**Tech Stack:** Python 3, pytest. Sem dependência nova.

## Global Constraints

Herdadas do plano-mestre (commits só do usuário; reader escolhe/apply executa; best-effort; PT-BR; 157 testes verdes intocáveis). Escopo de arquivos: SÓ os listados nas tasks abaixo.

---

### Task 1: `muntu/tags.py` + testes (PRÉ-REQUISITO dos outros workstreams)

**Files:**

- Create: `muntu/tags.py`
- Test: `tests/test_tags.py`

**Interfaces:**

- Produces: `valida_tags(tags: dict, tipo: str = "music") -> dict`, `descritor(tags: dict, tipo: str = "music") -> str`, `normaliza_ironia(valor) -> str`, constantes `IRONIA`, `FUNCAO`, `MODE`, `TAGS_MUSICA`, `TAGS_SFX`, `TAGS_VO`. WS-B e WS-C importam tudo daqui.

- [ ] **Step 1: Escrever testes que falham**

```python
"""Tag-schema — vocabulário compartilhado (valida_tags/descritor)."""
from muntu import tags


def test_valida_tags_musica_default_de_lixo():
    # entrada lixo -> schema default, nunca levanta (best-effort)
    out = tags.valida_tags(None)
    assert out["ironia"] == "sincero"
    assert out["mode"] == "ambiguous"
    assert out["instrumentacao"] == []
    assert out["bpm"] is None


def test_valida_tags_clampa_enums_e_listas():
    out = tags.valida_tags({
        "ironia": "KITSCH", "mode": "banana", "funcao": "payoff",
        "instrumentacao": ["sax", "", "piano", "tuba", "extra"],
        "bpm": 118.0, "campo_desconhecido": "x",
    })
    assert out["ironia"] == "kitsch"          # case-insensitive
    assert out["mode"] == "ambiguous"          # fora do vocab -> default
    assert out["funcao"] == "payoff"
    assert out["instrumentacao"] == ["sax", "piano", "tuba"]   # máx 3, vazio fora
    assert out["bpm"] == 118
    assert "campo_desconhecido" not in out


def test_valida_tags_vo_clampa_energia():
    assert tags.valida_tags({"energia": 99}, "vo")["energia"] == 5
    assert tags.valida_tags({"energia": "x"}, "vo")["energia"] == 3


def test_normaliza_ironia():
    assert tags.normaliza_ironia("deadpan") == "deadpan"
    assert tags.normaliza_ironia("") == "sincero"
    assert tags.normaliza_ironia(None) == "sincero"
    assert tags.normaliza_ironia(42) == "sincero"


def test_descritor_ordem_fixa_e_omite_vazios():
    d = tags.descritor({"era": "1980s", "registro": "power ballad", "ironia": "kitsch",
                        "instrumentacao": ["saxophone"], "bpm": 72})
    assert d == "1980s, power ballad, kitsch, saxophone, 72 BPM"
    # sincero/ambiguous = neutros -> omitidos
    assert "sincero" not in tags.descritor({"registro": "piano"})
    assert "ambiguous" not in tags.descritor({"registro": "piano"})


def test_descritor_sfx_e_vo():
    assert tags.descritor({"ambiencia": "party crowd", "eventos": ["glass clink"]},
                          "sfx") == "party crowd, glass clink"
    assert "energy 4/5" in tags.descritor({"genero": "female", "energia": 4}, "vo")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_tags.py -v` — Expected: FAIL `ModuleNotFoundError: muntu.tags`

- [ ] **Step 3: Criar `muntu/tags.py` VERBATIM da seção "Tag-schema v1 CANÔNICO" do plano-mestre**

Copiar o bloco de código inteiro de `docs/plans/2026-07-09-arquitetura-learn-ads-master.md`. Não improvisar campo nem renomear — WS-B/WS-C dependem dos nomes exatos.

- [ ] **Step 4: Rodar testes** — `pytest tests/test_tags.py -v` → PASS; `pytest tests/` → tudo verde.

- [ ] **Step 5: PARAR — avisar usuário pra commitar** (este commit destrava WS-B e WS-C).

---

### Task 2: reader emite ironia/cultura/instrumentação + viés cômico

**Files:**

- Modify: `muntu/reader.py` (PROMPT linhas 25-93; `_normaliza` linhas 193-246)
- Test: `tests/test_reader.py`

**Interfaces:**

- Consumes: `tags.normaliza_ironia` (Task 1).
- Produces: cada item de `timeline["partes"]` ganha `ironia: str` (vocab IRONIA), `cultura: str` (lower, pode ser ""), `instrumentacao: list[str]` (máx 3). Timelines antigas (sem os campos) continuam válidas — `_normaliza` põe defaults.

- [ ] **Step 1: Testes que falham** (adicionar em `tests/test_reader.py`, seguindo o padrão existente de chamar `reader._normaliza(payload_fake, cenas, duracao)`)

```python
def test_normaliza_tags_ricas(cenas_2):   # usar/criar fixture de 2 cenas como as existentes
    data = {"partes": [{"cena_ini": 1, "cena_fim": 2, "tipo": "score", "clima": "comedic",
                        "mood": "cheesy ballad", "ironia": "Kitsch", "cultura": "Brega",
                        "instrumentacao": ["saxophone", "", "strings", "drums", "x"]}]}
    p = reader._normaliza(data, cenas_2, 10.0)["partes"][0]
    assert p["ironia"] == "kitsch"
    assert p["cultura"] == "brega"
    assert p["instrumentacao"] == ["saxophone", "strings", "drums"]


def test_normaliza_tags_ausentes_viram_default(cenas_2):
    # timeline PINada antiga (sem campos novos) segue válida
    data = {"partes": [{"cena_ini": 1, "cena_fim": 2, "tipo": "score", "clima": "joyful"}]}
    p = reader._normaliza(data, cenas_2, 10.0)["partes"][0]
    assert p["ironia"] == "sincero"
    assert p["cultura"] == ""
    assert p["instrumentacao"] == []


def test_prompt_menciona_ironia_e_vies_comico():
    # trava de regressão do prompt: as instruções novas existem
    assert "ironia" in reader.PROMPT
    assert "kitsch" in reader.PROMPT
    assert "never plain sincero" in reader.PROMPT
```

- [ ] **Step 2: Rodar e ver falhar** — `pytest tests/test_reader.py -v` → FAIL (KeyError `ironia`).

- [ ] **Step 3: Editar `reader.PROMPT`** — inserir depois do bloco de `confianca_valence` (linha ~62), antes de `papel`:

```python
    "  - ironia: how the musical register relates to the scene: \"sincero\" (music takes "
    "the emotion straight), \"kitsch\" (deliberately cheesy/campy — the rom-com that takes "
    "itself TOO seriously on purpose), \"deadpan\" (straight music played AGAINST absurdity "
    "— the comedy of contrast), \"parodia\" (mocks a recognizable genre). In a COMEDY film "
    "every score part MUST take a comedic stance — kitsch, deadpan or parodia — never plain "
    "sincero: a sincere register in a comedy loses the joke (a romantic scene in a comedy "
    "is brega/kitsch or deadpan, not a sincere love ballad).\n"
    "  - cultura: a cultural/regional musical reference when the scene calls for one "
    "(\"brega\", \"bossa nova\", \"sertanejo\", \"balkan brass\", \"surf rock\", \"mariachi\"); "
    "empty string if none.\n"
    "  - instrumentacao: up to 3 signature instruments that DEFINE the register "
    "([\"saxophone\"], [\"pizzicato strings\", \"ukulele\"]); [] if no strong signature.\n"
```

E no JSON de retorno (linha ~91), dentro do objeto de parte, acrescentar:

```python
    '"ironia": "sincero"|"kitsch"|"deadpan"|"parodia", "cultura": "<ref or empty>", '
    '"instrumentacao": ["<instrument>"], '
```

- [ ] **Step 4: Editar `_normaliza`** — no dict do `partes.append` (linha ~210), depois de `"papel"`:

```python
            # tags ricas (learn-from-ads camada 1): o que o clima não segura.
            # Ausentes (timeline PINada antiga) -> defaults; ver muntu/tags.py
            "ironia": tags_mod.normaliza_ironia(p.get("ironia")),
            "cultura": (p.get("cultura") or "").strip().lower() if isinstance(p.get("cultura"), str) else "",
            "instrumentacao": [str(i).strip() for i in (p.get("instrumentacao") or [])
                               if isinstance(i, str) and i.strip()][:3],
```

Import no topo: `from muntu import mood` vira `from muntu import mood, tags as tags_mod`.

- [ ] **Step 5: Rodar** — `pytest tests/test_reader.py -v` → PASS; `pytest tests/` → verde.

- [ ] **Step 6: PARAR — usuário revisa+commita.**

---

### Task 3: `_prompt_da_parte` compõe as tags (cultura, instrumentação, ironia governa kitsch)

**Files:**

- Modify: `muntu/trilha.py` (`_prompt_da_parte`, linhas 90-135)
- Test: `tests/test_trilha.py`

**Interfaces:**

- Consumes: campos `ironia`/`cultura`/`instrumentacao` da parte (Task 2).
- Produces: assinatura de `_prompt_da_parte` INALTERADA (`parte, era, packs_dir, comico, cortes`). Comportamento novo só quando os campos existem.

- [ ] **Step 1: Testes que falham** (padrão existente do arquivo: montar `parte` dict e chamar `trilha._prompt_da_parte`)

```python
def test_prompt_compoe_cultura_e_instrumentacao():
    parte = {"tipo": "score", "clima": "", "mood": "romantic ballad",
             "cultura": "brega", "instrumentacao": ["saxophone"],
             "start": 0.0, "end": 10.0}
    p = trilha._prompt_da_parte(parte)
    assert "brega" in p and "saxophone" in p


def test_ironia_kitsch_aplica_mesmo_sem_comico():
    parte = {"tipo": "score", "clima": "", "mood": "romantic ballad",
             "ironia": "kitsch", "start": 0.0, "end": 10.0}
    assert "kitsch" in trilha._prompt_da_parte(parte, comico=False)


def test_ironia_deadpan_bloqueia_kitsch_mesmo_comico():
    # deadpan = música straight contra o absurdo — kitsch destruiria o contraste
    parte = {"tipo": "score", "clima": "", "mood": "elegant piano",
             "ironia": "deadpan", "start": 0.0, "end": 10.0}
    assert "kitsch" not in trilha._prompt_da_parte(parte, comico=True)


def test_comico_sem_ironia_mantem_kitsch_legado():
    # timeline antiga (sem ironia): comportamento atual preservado
    parte = {"tipo": "score", "clima": "", "mood": "romantic ballad",
             "start": 0.0, "end": 10.0}
    assert "kitsch" in trilha._prompt_da_parte(parte, comico=True)
```

- [ ] **Step 2: Rodar e ver falhar** — `pytest tests/test_trilha.py -v` → FAIL.

- [ ] **Step 3: Editar `_prompt_da_parte`** — substituir o bloco atual `if comico and not diegetic and not gated:` (linhas 120-124) por:

```python
    cultura = (parte.get("cultura") or "").strip()
    instr = [i for i in (parte.get("instrumentacao") or []) if isinstance(i, str) and i.strip()]
    ironia = (parte.get("ironia") or "").strip().lower()
    if cultura and cultura not in base.lower():
        base = f"{base}, {cultura} style"
    if instr:
        base = f"{base}, featuring {', '.join(instr[:3])}"
    # IRONIA (reader manda) governa o kitsch: kitsch/parodia -> cafona deliberado;
    # deadpan -> NUNCA kitsch (a comédia é o contraste, música straight contra o absurdo).
    # Sem ironia (timeline antiga) -> fallback legado: `comico` film-level aplica kitsch.
    # NUNCA sobre o AMBIGUO do gate: over-sentimental commitaria a valence segurada.
    kitsch = (ironia in ("kitsch", "parodia")) or (comico and not ironia)
    if kitsch and not diegetic and not gated:
        base = f"{base}, deliberately kitsch and cheesy, over-sentimental tongue-in-cheek melodrama"
```

- [ ] **Step 4: Rodar** — `pytest tests/test_trilha.py -v` → PASS; `pytest tests/` → verde.

- [ ] **Step 5: PARAR — usuário revisa+commita.**

---

### Task 4: Epidemic usa ironia pra corrigir o mood da busca (fix durável do bug Pringles no B)

**Files:**

- Modify: `muntu/epidemic.py` (`popula_beds` linhas ~330; helper novo `_clima_efetivo`)
- Test: `tests/test_epidemic.py`

**Interfaces:**

- Consumes: campo `ironia` da parte (Task 2); `CLIMA_EPIDEMIC` existente.
- Produces: `_clima_efetivo(parte) -> str` — clima usado na busca; contrato externo de `popula_beds` inalterado.

- [ ] **Step 1: Testes que falham**

```python
def test_clima_efetivo_kitsch_vira_comedic():
    # bug Pringles: parte "romantic" sincera perdeu o humor; ironia corrige a QUERY
    assert epidemic._clima_efetivo({"clima": "romantic", "ironia": "kitsch"}) == "comedic"
    assert epidemic._clima_efetivo({"clima": "tender", "ironia": "parodia"}) == "comedic"


def test_clima_efetivo_sincero_e_deadpan_preservam():
    assert epidemic._clima_efetivo({"clima": "romantic", "ironia": "sincero"}) == "romantic"
    # deadpan: a graça é a música straight -> busca o clima como está
    assert epidemic._clima_efetivo({"clima": "epic", "ironia": "deadpan"}) == "epic"
    assert epidemic._clima_efetivo({"clima": "tense"}) == "tense"
```

- [ ] **Step 2: Rodar e ver falhar** — `pytest tests/test_epidemic.py -v` → FAIL.

- [ ] **Step 3: Implementar** — em `epidemic.py`, antes de `popula_beds`:

```python
def _clima_efetivo(parte: dict) -> str:
    """Clima usado na BUSCA do catálogo. ironia kitsch/parodia -> a faixa certa é cômica
    (quirky/kitsch), não o clima sincero que o rótulo diz — o bug Pringles: 'romantic'
    sincero perdeu o humor. deadpan preserva (a graça É a música straight)."""
    clima = (parte.get("clima") or "").strip().lower()
    if (parte.get("ironia") or "").strip().lower() in ("kitsch", "parodia"):
        return "comedic"
    return clima
```

E dentro de `popula_beds`, onde o clima da parte é lido pra chamar `bed_para_clima`, trocar a leitura direta por `_clima_efetivo(parte)`.

- [ ] **Step 4: Rodar** — `pytest tests/test_epidemic.py -v` → PASS; `pytest tests/` → verde.

- [ ] **Step 5: PARAR — usuário revisa+commita.**

---

### Task 5: Validação de ouvido (manual, usuário)

- [ ] Re-rodar o filme Pringles SEM override manual de clima: `python -c "import pipeline; pipeline.run('<pringles.mp4>')"` (timeline nova, reader com prompt rico).
- [ ] Conferir na `outputs/timeline_<stem>.json`: partes score com `ironia != "sincero"` e clima cômico onde a comédia pede.
- [ ] A/B de ouvido vs `outputs/ab/A_pinned.mp4`. Veredito do usuário fecha a camada 1.
