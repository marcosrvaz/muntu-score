from scenedetect import detect, ContentDetector, open_video


def analyze(video_path: str) -> dict:
    video = open_video(video_path)
    scenes = detect(video_path, ContentDetector())
    duracao = video.duration.seconds
    cortes = [s[0].seconds for s in scenes if s[0].seconds > 0]
    return {"duracao": duracao, "cortes": cortes, "cenas": [], "bpm_sugerido": 120}
