import subprocess


def mux(video_path: str, audio_path: str, out_path: str):
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path, "-i", audio_path,
            "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
            "-shortest", out_path
        ], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or b"").decode(errors="replace")
        resumo = "\n".join(stderr.strip().splitlines()[-3:])
        raise ValueError(f"ffmpeg falhou no mux: {resumo}") from e
    return out_path
