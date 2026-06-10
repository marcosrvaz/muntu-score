# Music Director — design (Task 11)

> O coração da ferramenta. Skeleton põe beep no corte cru (tosco). Aqui a edição
> **dita o tempo da música** e os acentos travam numa grade musical, não no corte cru.
> É onde 30 anos de ouvido viram regra de código.

## Problema

Dois tempos que não conversam:

- **Cortes do vídeo** — caem onde o editor cortou (arbitrário).
- **Grade musical** — batida regular num BPM.

Hit no timestamp do corte cru → cai fora da batida → soa amador.

## Princípio arquitetural (decide tudo)

| Camada                          | Controle de timing              | Papel                                                     |
| ------------------------------- | ------------------------------- | --------------------------------------------------------- |
| **Accents** (teus stems, pydub) | exato, ao ms                    | **carregam o sync** — travam na grade                     |
| **Bed** (gen Replicate)         | frouxo (modelo não obedece BPM) | **atmosfera** — textural, embaixo, não rítmico-dependente |

Regra: nunca dependa do bed gerado pra sync. Quem trava são os stems. Bed rítmico
travado → montar de loops de BPM conhecido (material teu), não confiar no gen.

## Pipeline do Director

```
cortes ──> [1] estima BPM+fase ──> [2] classifica edição ──> [3] monta grade
                                                                   │
       [6] plano de score <── [5] seleciona quais cortes <── [4] quantiza acentos
```

### [1] Estima BPM + fase a partir dos cortes

Edição publicitária boa tem ritmo escondido. Acha a grade `{φ + k·P}` (P = período da
batida em s, φ = fase/offset) que melhor encaixa nos cortes. Busca em grade (brute force,
barato — poucos cortes):

```python
def estima_bpm(cortes, bpm_range=(90, 140), tol=0.05):
    melhor = None
    for bpm in range(bpm_range[0], bpm_range[1] + 1):
        P = 60.0 / bpm
        for fase_step in range(50):                 # varre fase dentro de 1 batida
            phi = fase_step / 50.0 * P
            # residuo = distancia de cada corte a linha de grade mais proxima
            res = []
            for t in cortes:
                k = round((t - phi) / P)
                res.append(abs(t - (phi + k * P)))
            dentro = sum(1 for r in res if r <= tol)   # cortes "na grade"
            erro = sum(res)
            score = (dentro, -erro)                     # max cortes na grade, min erro
            if melhor is None or score > melhor[0]:
                melhor = (score, bpm, phi, dentro / len(cortes))
    _, bpm, phi, confianca = melhor
    return {"bpm": bpm, "fase": phi, "confianca": confianca}
```

Notas:

- `bpm_range` vem do **pack** (ex: "corporate upbeat" 110-128; "natal suave" 80-100).
- Cuidado de oitava: 60 BPM = 120 half-time. Restringir range resolve.
- `tol` = janela de "tá na batida". 50ms ≈ 1.2 frame a 24fps — o olho não vê.

### [2] Classifica a edição (regime)

```python
if confianca >= 0.6:   modo = "ritmico"   # maioria dos cortes cai na grade
else:                  modo = "livre"      # cortes espalhados, sem pulso claro
```

- **rítmico** → acentos percussivos travados na grade (hits, impacts).
- **livre** → elementos que toleram estar fora da grade: **swells, risers, transições**
  (sobem ATÉ o corte). Percussivo fora de grade = tosco; transição não.

### [3] Monta a grade

`grade = [φ + k·P for k in range(...)]` cobrindo a duração. Marca **downbeats**
(cada 4 batidas) — carregam peso; acento grande vai em downbeat, pequeno em batida.

### [4] Quantiza acentos (o truque anti-tosco)

Para cada corte que vai virar acento:

```python
t_video = corte                       # corte fica onde tá (visual intocado)
t_audio = phi + round((corte - phi) / P) * P   # acento snap na grade
# |t_audio - t_video| <= tol  -> cérebro funde imagem+som
```

Opcional ear-tuned: **antecipação** — `t_audio -= lead_ms` (~40-80ms, tunável por pack).
Resolução musical cai ON the cut visual. Sensação pro de montador.

### [5] Seleciona quais cortes acentuar

**Não acentua todo corte.** Pro acentua seletivo — senão cansa, também tosco.

- Troca de cena/energia/clima (vem da análise de clima, Task 10) → acento forte
  (impact/riser-into no downbeat).
- Corte menor → hit leve na batida, ou nada.
- **Cap de densidade**: máx N acentos por compasso.

(Sem Task 10 ainda → heurística: acentua os cortes de maior `confianca` de grade +
respeitando o cap. Refina quando o clima entrar.)

### [6] Plano de score (saída)

```json
{
  "bpm": 116,
  "fase": 0.18,
  "confianca": 0.72,
  "modo": "ritmico",
  "bed_prompt": "warm corporate bed, soft pads, 116 BPM, no drums",
  "acentos": [
    { "t_video": 3.0, "t_audio": 2.97, "tipo": "impact", "stem": "hit_low.wav", "ganho_db": 0 },
    { "t_video": 6.0, "t_audio": 6.03, "tipo": "perc", "stem": "tick.wav", "ganho_db": -6 }
  ]
}
```

Mixer: bed (baixo, textural) + acentos (na grade, na frente). Signature renderiza os
acentos nos `t_audio`.

## Onde tua direção vive (regras tuas, refinadas na orelha)

- `bpm_range` por pack
- `tol` e `lead_ms` (o quão "à frente" o acento entra)
- política de seleção [5]: o que merece impact vs perc vs nada
- mapa clima → tipo de acento + escolha de stem
- densidade máx por compasso

Estas são as perilhas que **só teu ouvido calibra**. O algoritmo dá a grade; você diz o
que entra nela.

## Versão pro (depois — não V1)

**Tempo-map variável**: cortes irregulares → varia o BPM entre seções pra uma batida
cair EXATA em cada corte (warp tipo Cubase hit-points / Ableton). Mais complexo. Só vale
quando o modo "livre" não estiver bom o suficiente.

## Resumo do que ataca o "tosco"

1. BPM derivado dos cortes (não chumbado)
2. Acentos snap na grade, não no corte cru (≤ tol, olho não vê)
3. Bed atmosfera, sync vem dos teus stems (controle exato)
4. Acento seletivo, não em todo corte
5. Antecipação opcional (resolução ON the cut)
6. Modo livre (swells/risers) quando não há pulso
