# Muntu Score

Web app que recebe um **video curto (10-30s)** e devolve o mesmo video com uma
**trilha sincronizada aos cortes** — cama-base de IA + stems de assinatura, dirigidos
por um _context pack_ de publicidade.

> Walking skeleton em construcao. Semana 1 = pipeline ponta-a-ponta (deteccao de corte
> → stem nos cortes → mux ffmpeg → web app). Cama-base IA, analise de clima e context
> packs entram nas semanas seguintes.

## Como funciona

```
video → analyzer → signature → mixer → video scoreado
        (cortes)   (stem nos    (ffmpeg)
                    cortes)
```

- **analyzer** — PySceneDetect acha os cortes do video.
- **signature** — posiciona stems de assinatura nos timestamps dos cortes (pydub).
- **mixer** — cola o audio gerado de volta no video (ffmpeg).
- **app** — interface Gradio: sobe clipe, recebe scoreado.

## Rodar local

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# coloca um video em assets/sample.mp4 e um stem em assets/stems/default/hit.wav
python app.py            # abre http://127.0.0.1:7860
pytest                   # testes
```

## Stack

Python · ffmpeg · PySceneDetect · pydub · Replicate (gen de musica) · Gradio + Hugging Face Spaces.
