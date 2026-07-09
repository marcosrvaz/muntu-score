# Muntu Score

Web app que recebe um **video curto (10-30s)** e devolve o mesmo video com uma
**trilha sincronizada aos cortes** — cama-base de IA + stems de assinatura, dirigidos
por um _context pack_ de publicidade.

## Como funciona

```
video → analyzer → mood → director → stems → signature ─┐
        (cortes)  (clima)  (grade    (papel)  (acentos)  ├─ mix → mux → video scoreado
                            BPM)                base_bed ─┘ (normaliza  (ffmpeg)
                                                (cama IA)    + fades)
```

O truque anti-"tosco": um beep no corte cru cai fora da batida e soa amador. O
**director** deriva um pulso (BPM + fase) dos proprios cortes, monta uma grade musical e
**quantiza** os acentos pra caírem NA batida (≤50ms do corte — o olho nao ve, o ouvido
funde). Os stems de assinatura carregam o sync (timing exato); a cama IA e so atmosfera
embaixo. E onde o ouvido do produtor vira regra de codigo (`packs/*.json`).

- **analyzer** — PySceneDetect acha os cortes.
- **mood** — 1 frame/cena → VLM (Replicate) → clima + energia. _Opcional._
- **director** — BPM+fase dos cortes, grade, quantiza acentos, seleciona seletivo
  (troca de energia = acento forte). O coracao. Puro Python.
- **stems** — escolhe o stem por papel (hit/perc/riser) + clima (`manifest.json`).
- **signature** — renderiza os acentos nos tempos quantizados (pydub).
- **base_bed** — cama-base instrumental via ElevenLabs Music V2. _Opcional (gated na key)._
- **packs** — regras de direcao por contexto (default/natal): `bpm_range`, `tol`,
  antecipacao, densidade, estilo da cama.
- **mixer** — cola o audio no video (ffmpeg), com gain staging + fades.
- **app** — interface Gradio: sobe clipe, escolhe pack, recebe scoreado.

Cada camada de IA e _gated_: sem key ElevenLabs/Replicate, cai no skeleton (so stems) —
o binario nunca quebra.

## Rodar local

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# coloca um video em assets/sample.mp4 e um stem em assets/stems/default/hit.wav
python app.py            # abre http://127.0.0.1:7860
pytest                   # testes
```

## Stack

Python · ffmpeg · PySceneDetect · pydub · ElevenLabs Music V2 (cama) · Replicate/LLaVA (clima) · Gradio + Hugging Face Spaces.
