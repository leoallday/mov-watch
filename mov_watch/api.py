import requests
from typing import List, Union, Optional

import sys
import os
from mov_watch.models import Movie, TVShow, Season, Episode, Media, StreamInfo

# The public API can be pointed at a mirror with MOV_WATCH_API_BASE_URL.
API_BASE_URL = os.environ.get("MOV_WATCH_API_BASE_URL", "https://api.xleo.nl").rstrip("/")
API_SECRET_KEY = "mw_sk_lK8xR2mN4vP7jH9w"

HEADERS = {
    'User-Agent': 'mov-watch/1.0',
    'X-API-Key': API_SECRET_KEY,
}

DEBUG_LOG_FILE = os.path.expanduser("~/.mov-watch/debug.log")

# Playwright installs Chromium into ~/.cache by default, which is a throwaway
# location: a cache cleaner deletes it and the next play re-downloads ~170 MB.
# Keep the browser in the app's own data directory so it survives that.
BROWSERS_PATH = os.path.expanduser("~/.mov-watch/browsers")
LEGACY_BROWSERS_PATH = os.path.expanduser("~/.cache/ms-playwright")


def log_debug(message: str):
    try:
        os.makedirs(os.path.dirname(DEBUG_LOG_FILE), exist_ok=True)
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(f"[DEBUG] {message}\n")
    except Exception as e:
        print(f"[DEBUG ERROR] Failed to write log: {e}", file=sys.stderr)


def _migrate_cached_browsers() -> None:
    """Move a browser an older version downloaded into ~/.cache."""
    if not os.path.isdir(LEGACY_BROWSERS_PATH):
        return
    if os.path.isdir(BROWSERS_PATH) and os.listdir(BROWSERS_PATH):
        return
    import shutil
    for entry in os.listdir(LEGACY_BROWSERS_PATH):
        if not entry.startswith("chromium"):
            continue
        src = os.path.join(LEGACY_BROWSERS_PATH, entry)
        dst = os.path.join(BROWSERS_PATH, entry)
        try:
            shutil.move(src, dst)
            log_debug(f"Migrated Playwright browser {src} -> {dst}")
        except OSError as e:
            log_debug(f"Could not migrate Playwright browser {src}: {e}")


def _use_persistent_browsers() -> str:
    """Point Playwright at the app's own browser directory."""
    os.makedirs(BROWSERS_PATH, exist_ok=True)
    _migrate_cached_browsers()
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = BROWSERS_PATH
    return BROWSERS_PATH


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

    if not isinstance(data, list):
        log_debug(f"API search returned unexpected payload: {type(data).__name__}")
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

    if not isinstance(data, dict):
        log_debug(f"API episodes returned unexpected payload: {type(data).__name__}")
        return tv_show

    tv_show.seasons.clear()
    for sd in data.get('seasons') or []:
        season_number = sd.get('season')
        season = Season(title=sd.get('title') or f"Season {season_number}")
        for ep in sd.get('episodes') or []:
            num = ep.get('episode')
            if num is None:
                log_debug("Skipping episode without an episode number")
                continue
            season.episodes.append(Episode(
                title=ep.get('title', f'Episode {num}'),
                url=f"https://www.themoviedb.org/tv/{tv_show.tmdb_id}/season/{season_number}/episode/{num}",
                season_number=season_number,
                episode_number=num,
                tmdb_id=tv_show.tmdb_id,
            ))
        tv_show.seasons.append(season)

    log_debug(f"API episodes: {len(tv_show.seasons)} seasons for {tv_show.title}")
    return tv_show


def _ensure_playwright_browser() -> bool:
    """Make sure Playwright and its Chromium build are usable.

    The browser is a one-time ~170 MB download, so it is only fetched when a
    launch check fails, and the install is verified afterwards instead of
    being assumed to have worked.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log_debug("playwright python package is not installed")
        return False
    _use_persistent_browsers()

    def _can_launch() -> bool:
        try:
            with sync_playwright() as p:
                p.chromium.launch(headless=True).close()
            return True
        except Exception as e:
            log_debug(f"Chromium launch check failed: {e}")
            return False

    if _can_launch():
        return True

    print("\n[ mov-watch ] One-time download: Chromium for stream extraction (~170 MB).")
    print(f"[ mov-watch ] Stored in {BROWSERS_PATH} - pre-install with")
    print("[ mov-watch ]   python -m playwright install chromium")
    import subprocess, sys
    try:
        # No timeout: a hard cap aborts the download halfway and leaves a
        # browser that cannot start, which looks like a stream failure later.
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"],
                       check=True)
    except Exception as e:
        log_debug(f"Chromium install failed: {e}")
        print("[ mov-watch ] Failed to install Chromium. Try: python -m playwright install chromium")
        return False

    if not _can_launch():
        print("[ mov-watch ] Chromium installed but cannot start.")
        print("[ mov-watch ] Try: python -m playwright install-deps chromium")
        return False

    print("[ mov-watch ] Chromium ready, starting...")
    return True


def _get_vixsrc_embed_url(tmdb_id: int, media_type: str,
                           season: Optional[int] = None,
                           episode: Optional[int] = None) -> Optional[str]:
    try:
        if media_type == 'movie':
            url = f"https://vixsrc.to/api/movie/{tmdb_id}"
        else:
            url = f"https://vixsrc.to/api/tv/{tmdb_id}/{season}/{episode}"

        log_debug(f"Fetching vixsrc embed URL: {url}")
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code != 200:
            log_debug(f"vixsrc API returned {r.status_code}")
            return None
        data = r.json()
        embed_path = data.get("src")
        if not embed_path:
            log_debug("vixsrc API returned no src")
            return None
        return f"https://vixsrc.to{embed_path}"
    except Exception as e:
        log_debug(f"vixsrc embed fetch failed: {e}")
        return None


def _resolve_stream_with_playwright(tmdb_id: int, media_type: str,
                                     season: Optional[int] = None,
                                     episode: Optional[int] = None) -> Optional[StreamInfo]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log_debug("playwright not installed")
        return None

    if not _ensure_playwright_browser():
        return None

    _use_persistent_browsers()

    embed_url = _get_vixsrc_embed_url(tmdb_id, media_type, season, episode)
    if not embed_url:
        log_debug("Could not get vixsrc embed URL")
        return None

    log_debug(f"Resolving stream via Playwright: {embed_url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    viewport={'width': 1280, 'height': 720},
                )
                page = context.new_page()

                # Fallback for players that never expose a playlist: the manifest
                # request itself is still visible on the wire.
                media_urls: List[str] = []

                def _capture(request):
                    if '.m3u8' in request.url or '.mp4' in request.url:
                        media_urls.append(request.url)

                page.on('request', _capture)

                # vixsrc only serves the embed when a Referer is present. Without
                # it the response is a 403 "Forbidden" page, jwplayer never
                # loads, and every extraction fails with "No playlist URL".
                page.goto(embed_url, wait_until='load', timeout=30000,
                          referer='https://vixsrc.to/')

                # The player is created asynchronously - poll instead of sleeping
                # for a guessed number of seconds.
                try:
                    page.wait_for_function(
                        "() => typeof window.jwplayer === 'function'", timeout=15000)
                except Exception:
                    log_debug(f"jwplayer never loaded (page title: {page.title()!r})")

                playlist_url = page.evaluate('''
                    () => {
                        try {
                            for (const item of jwplayer().getPlaylist() || [])
                                for (const source of item.sources || [])
                                    if (source && source.file) return source.file;
                        } catch (e) {}
                        const video = document.querySelector('video');
                        return (video && (video.currentSrc || video.src)) || null;
                    }
                ''') or (media_urls[0] if media_urls else None)

                cookies = context.cookies()
            finally:
                browser.close()

            if not playlist_url:
                log_debug("No playlist URL found on the embed page")
                return None

            log_debug(f"Stream URL resolved ({len(playlist_url)} chars), {len(cookies)} cookies")
            return StreamInfo(
                video_url=playlist_url,
                cookies=cookies,
                referer=embed_url,
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
