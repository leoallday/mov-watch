import json
from pathlib import Path
from datetime import datetime

class FavoritesManager:
    MAX_FAVORITES = 100

    def __init__(self):
        self.file_path = self._get_path()
        self.favorites = self._load()

    def _get_path(self) -> Path:
        home_dir = Path.home()
        db_dir = home_dir / ".mov-watch" / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "favorites.json"

    def _load(self) -> dict:
        if not self.file_path.exists():
            return {}
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {}
                return data
        except (json.JSONDecodeError, IOError, OSError):
            return {}

    def save(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, indent=4, ensure_ascii=False)
        except (IOError, OSError) as e:
            import sys
            print(f"Warning: Failed to save favorites: {e}", file=sys.stderr)

    def add(self, media_title, poster_url):
        if media_title in self.favorites:
            self.favorites[media_title]['added_at'] = datetime.now().isoformat()
            self.save()
            return

        if len(self.favorites) >= self.MAX_FAVORITES:
            oldest = min(self.favorites.items(), key=lambda x: x[1]['added_at'])
            del self.favorites[oldest[0]]

        self.favorites[media_title] = {
            'title': media_title,
            'poster': poster_url,
            'added_at': datetime.now().isoformat()
        }
        self.save()

    def remove(self, media_title):
        if media_title in self.favorites:
            del self.favorites[media_title]
            self.save()

    def is_favorite(self, media_title):
        return media_title in self.favorites

    def get_all(self):
        return sorted(
            [{'title': k, **v} for k, v in self.favorites.items()],
            key=lambda x: x['added_at'],
            reverse=True
        )