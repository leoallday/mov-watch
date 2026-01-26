# Dummy monitoring system since the original API for it is removed.
class MonitoringSystem:
    def __init__(self):
        pass

    def track_app_start(self):
        pass

    def track_video_play(self, media_title: str, episode: str, mode: str = "stream"):
        pass

monitor = MonitoringSystem()