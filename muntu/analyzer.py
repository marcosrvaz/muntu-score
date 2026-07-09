from scenedetect import ContentDetector, SceneManager, open_video


def analyze(video_path: str) -> dict:
    video = open_video(video_path)              # 1 decodificacao so; passada ao SceneManager
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video=video)
    scenes = scene_manager.get_scene_list()
    duracao = video.duration.seconds
    cortes = [s[0].seconds for s in scenes if s[0].seconds > 0]
    return {"duracao": duracao, "cortes": cortes, "cenas": []}
