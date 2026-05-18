import requests
from typing import List, Union, Optional

import sys
import os
from mov_watch.models import Movie, TVShow, Season, Episode, Media, StreamInfo

API_BASE_URL = "https://api.xleo.nl"

HEADERS = {
    'User-Agent': 'mov-watch/1.0',
}

DEBUG_LOG_FILE = os.path.expanduser("~/.mov-watch/debug.log")


def log_debug(message: str):
    try:
        os.makedirs(os.path.dirname(DEBUG_LOG_FILE), exist_ok=True)
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(f"[DEBUG] {message}\n")
    except Exception as e:
        print(f"[DEBUG ERROR] Failed to write log: {e}", file=sys.stderr)


def search(query: str) -> List[Union[Movie, TVShow]]:
    url = f"{API_BASE_URL}/search?q={requests.utils.quote(query)}"
    log_debug(f"API search URL: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        log_debug(f"API search failed: {e}")
        return []

    results: List[Union[Movie, TVShow]] = []
    for item in data:
        tmdb_id = item.get('id')
        title = item.get('title', 'Unknown')
        media_type = item.get('type', 'movie')
        poster = item.get('poster')
        year = item.get('year', '')
        if media_type == 'movie':
            results.append(Movie(
                title=title,
                url=f"https://www.themoviedb.org/movie/{tmdb_id}",
                poster=poster,
                year=year,
                tmdb_id=tmdb_id,
            ))
        elif media_type == 'tv':
            results.append(TVShow(
                title=title,
                url=f"https://www.themoviedb.org/tv/{tmdb_id}",
                poster=poster,
                year=year,
                tmdb_id=tmdb_id,
            ))
    log_debug(f"API search returned {len(results)} results")
    return results


def get_episodes(tv_show: TVShow) -> TVShow:
    if not tv_show.tmdb_id:
        log_debug("Cannot fetch episodes: missing TMDB ID")
        return tv_show

    url = f"{API_BASE_URL}/tv/{tv_show.tmdb_id}"
    log_debug(f"API episodes URL: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        log_debug(f"API episodes fetch failed: {e}")
        return tv_show

    for sd in data.get('seasons', []):
        season = Season(title=sd.get('title', f"Season {sd['season']}"))
        for ep in sd.get('episodes', []):
            num = ep['episode']
            season.episodes.append(Episode(
                title=ep.get('title', f'Episode {num}'),
                url=f"https://www.themoviedb.org/tv/{tv_show.tmdb_id}/season/{sd['season']}/episode/{num}",
                season_number=sd['season'],
                episode_number=num,
                tmdb_id=tv_show.tmdb_id,
            ))
        tv_show.seasons.append(season)

    log_debug(f"API episodes: {len(tv_show.seasons)} seasons for {tv_show.title}")
    return tv_show


def _resolve_stream_with_playwright(tmdb_id: int, media_type: str,
                                     season: Optional[int] = None,
                                     episode: Optional[int] = None) -> Optional[StreamInfo]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log_debug("playwright not installed")
        return None

    pw_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if not pw_path:
        for candidate in ["/tmp/playwright-browsers",
                          os.path.expanduser("~/.cache/ms-playwright")]:
            if os.path.isdir(candidate):
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = candidate
                pw_path = candidate
                break

    if media_type == 'movie':
        target_url = f"https://www.vidking.net/embed/movie/{tmdb_id}"
    else:
        target_url = f"https://www.vidking.net/embed/tv/{tmdb_id}?s={season}&e={episode}"

    log_debug(f"Resolving stream via Playwright: {target_url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                viewport={'width': 1280, 'height': 720},
            )
            page = context.new_page()

            stream_url = None

            def on_response(response):
                nonlocal stream_url
                if '.m3u8' in response.url and stream_url is None:
                    stream_url = response.url

            page.on('response', on_response)

            page.goto(target_url, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(15000)

            if not stream_url:
                log_debug("No .m3u8 URL found via Playwright")
                browser.close()
                return None

            cookies = context.cookies()
            browser.close()

            log_debug(f"Stream URL resolved ({len(stream_url)} chars), {len(cookies)} cookies")
            return StreamInfo(
                video_url=stream_url,
                cookies=cookies,
                referer=target_url,
            )
    except Exception as e:
        log_debug(f"Playwright stream resolution failed: {e}")
        return None


def get_stream_url(media: Media,
                   subs_language: str = "english") -> Optional[StreamInfo]:
    log_debug(f"Getting stream URL for: {media.title}")

    if isinstance(media, Movie):
        if not media.tmdb_id:
            log_debug("Movie has no TMDB ID")
            return None
        return _resolve_stream_with_playwright(media.tmdb_id, 'movie')

    if isinstance(media, Episode):
        if not media.tmdb_id:
            log_debug("Episode has no TMDB ID")
            return None
        return _resolve_stream_with_playwright(
            media.tmdb_id, 'tv',
            season=media.season_number,
            episode=media.episode_number,
        )

    log_debug(f"Unknown media type: {type(media)}")
    return None
