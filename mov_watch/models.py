from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Media:
    title: str
    url: str
    poster: Optional[str] = None
    year: Optional[str] = None
    tmdb_id: Optional[int] = None


@dataclass
class Movie(Media):
    pass


@dataclass
class StreamInfo:
    video_url: str
    subtitle_urls: List[str] = field(default_factory=list)
    cookies: List[dict] = field(default_factory=list)
    referer: str = ""


class Episode:
    def __init__(self, title: str, url: str, data_id: Optional[str] = None,
                 poster: Optional[str] = None, season_number: Optional[int] = None,
                 episode_number: Optional[int] = None, tmdb_id: Optional[int] = None):
        self.title = title
        self.url = url
        self.data_id = data_id
        self.poster = poster
        self.season_number = season_number
        self.episode_number = episode_number
        self.tmdb_id = tmdb_id


@dataclass
class Season:
    title: str
    episodes: List[Episode] = field(default_factory=list)


@dataclass
class TVShow(Media):
    seasons: List[Season] = field(default_factory=list)
