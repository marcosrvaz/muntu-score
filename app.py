import uuid

import gradio as gr
from dotenv import load_dotenv

load_dotenv()          # local: carrega .env (gitignored). HF Space: usa secret do ambiente.

from pipeline import run


def score(video, pack, banco):
    if not video:
        raise gr.Error("Sobe um clipe primeiro.")
    # out_path unico por request: HF Space e multi-sessao, path fixo faz request concorrente
    # sobrescrever o video de outro usuario.
    out_path = f"outputs/scored_{uuid.uuid4().hex[:8]}.mp4"
    try:
        return run(video, out_path=out_path, pack=pack or "auto", banco=banco)
    except ValueError as e:
        raise gr.Error(str(e))


demo = gr.Interface(
    fn=score,
    inputs=[
        gr.Video(label="Sobe teu clipe (10-30s)"),
        gr.Dropdown(["auto", "default", "playful", "surf", "natal", "romantico"],
                    value="auto", label="Contexto (auto = detecta o mood do video)"),
        gr.Checkbox(value=False, label="Banco licenciado (Epidemic) — faixa real no lugar da "
                                       "gerada; precisa EPIDEMIC_API_KEY"),
    ],
    outputs=gr.Video(label="Com trilha Muntu"),
    title="Muntu Score",
    description="Gera trilha sincronizada aos cortes do video. Acentos travam na grade "
                "musical (nao no corte cru); musica IA embaixo quando ha key ElevenLabs.",
)

if __name__ == "__main__":
    demo.launch()
