import json
from pathlib import Path
from datetime import datetime

class HistoryManager:
    MAX_HISTORY_SIZE = 100

    def __init__(self):
        self.history_file = self._get_history_path()
        self.history = self._load_history()

    def _get_history_path(self) -> Path:
        home_dir = Path.home()
        db_dir = home_dir / ".mov-watch" / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "history.json"

    def _load_history(self) -> dict:
        if not self.history_file.exists():
            return {}
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {}
                return data
        except (json.JSONDecodeError, IOError, OSError):
            return {}

    def save_history(self):
        try:
            if len(self.history) > self.MAX_HISTORY_SIZE:
                sorted_items = sorted(
                    self.history.items(),
                    key=lambda x: x[1].get('last_updated', ''),
                    reverse=True
                )
                self.history = dict(sorted_items[:self.MAX_HISTORY_SIZE])

            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=4, ensure_ascii=False)
        except (IOError, OSError) as e:
            import sys
            print(f"Warning: Failed to save history: {e}", file=sys.stderr)

    def mark_watched(self, media_title, episode_title):
        self.history[media_title] = {
            'episode': episode_title,
            'last_updated': datetime.now().isoformat()
        }
        self.save_history()

    def get_last_watched(self, media_title):
        data = self.history.get(media_title)
        if data:
            return data.get('episode')
        return None

    def get_history(self):
        items = []
        for media_title, data in self.history.items():
            items.append({
                'title': media_title,
                'episode': data.get('episode', '?'),
                'last_updated': data.get('last_updated', '')
            })
        items.sort(key=lambda x: x['last_updated'], reverse=True)
        return items
