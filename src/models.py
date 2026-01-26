from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Media:
    """Base class for media."""
    title: str
    url: str
    poster: Optional[str] = None
    year: Optional[str] = None


@dataclass
class Movie(Media):
    """Represents a movie."""
    pass


class Episode:
    def __init__(self, title: str, url: str, data_id: Optional[str] = None, poster: Optional[str] = None):
        self.title = title
        self.url = url
        self.data_id = data_id
        self.poster = poster


@dataclass
class Season:
    """Represents a season of a TV show."""
    title: str
    episodes: List[Episode] = field(default_factory=list)


@dataclass
class TVShow(Media):
    """Represents a TV show."""
    seasons: List[Season] = field(default_factory=list)