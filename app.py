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
