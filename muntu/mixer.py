import subprocess


def mux(video_path: str, audio_path: str, out_path: str):
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path, "-i", audio_path,
        "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
        "-shortest", out_path
    ], check=True)
    return out_path
