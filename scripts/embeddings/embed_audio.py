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
        inputs = proc(audio=j, sampling_rate=SR, return_tensors="pt")
        e = model.get_audio_features(**inputs).pooler_output.detach().numpy()[0]
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
