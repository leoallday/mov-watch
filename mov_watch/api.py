import requests
from bs4 import BeautifulSoup
import re
import json
from typing import List, Union, Optional
from urllib.parse import urljoin
import sys
import base64
from Crypto.Cipher import AES
from Crypto.Hash import MD5
from mov_watch.models import Movie, TVShow, Season, Episode, Media

BASE_URL = "https://flixhq.to" # Changed to flixhq.to

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest' # Added X-Requested-With header
}

DECODER_API_URL = "https://dec.eatmynerds.live"

from datetime import datetime
import os

DEBUG_LOG_FILE = os.path.expanduser("~/.mov-watch/debug.log")
DEBUG_PRINTS_STDERR = False  # Set to True to enable debug output to stderr

def log_debug(message: str):
    """Debug logging to stderr when DEBUG mode is enabled."""
    # Always write to debug log file
    try:
        os.makedirs(os.path.dirname(DEBUG_LOG_FILE), exist_ok=True)
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(f"[DEBUG] {message}\n")
    except Exception as e:
        print(f"[DEBUG ERROR] Failed to write log: {e}", file=sys.stderr)
    
    if DEBUG_PRINTS_STDERR:
        print(f"[DEBUG] {message}", file=sys.stderr)

# Force debug output on startup
# print("[DEBUG] api.py loaded! DEBUG_PRINTS_STDERR =", DEBUG_PRINTS_STDERR, file=sys.stderr)

def search(query: str) -> List[Union[Movie, TVShow]]:
    """
    Searches for media on flixhq.to.
    """
    search_url = f"{BASE_URL}/search/{query.replace(' ', '-')}"
    log_debug(f"Search URL: {search_url}")
    response = requests.get(search_url, headers=HEADERS)
    response.raise_for_status()
    log_debug(f"Search response status: {response.status_code}")

    soup = BeautifulSoup(response.text, 'html.parser')
    results: List[Union[Movie, TVShow]] = []

    
    items = soup.find_all("div", class_="flw-item")
    if not items:
        log_debug("No flw-item results found for query.")
        return []

    for i, item in enumerate(items[:10]): 
        log_debug(f"Processing item: {item.prettify()[:200]}...")
        poster_link = item.find("div", class_="film-poster")
        detail_section = item.find("div", class_="film-detail")
        if poster_link and detail_section:
            link_elem = poster_link.find("a")
            title_elem = detail_section.find("h2", class_="film-name")
            if link_elem and title_elem:
                href = link_elem.get("href", "")
                title_link = title_elem.find("a")
                title = (
                    title_link.get("title", "Unknown Title") if title_link else "Unknown Title"
                )
                info_elem = detail_section.find("div", class_="fd-infor")
                year = ""
                # media_type_str = "" # Not used anymore, infer from href
                if info_elem:
                    spans = info_elem.find_all("span")
                    if spans:
                        year = spans[0].text.strip() if spans else ""
                
                url = urljoin(BASE_URL, href) 
                poster_img = item.find('img', class_='film-poster-img')
                poster = poster_img['data-src'] if poster_img and 'data-src' in poster_img.attrs else None

                log_debug(f"Extracted -> Title: {title}, URL: {url}, Poster: {poster}, Year: {year}") # Removed Type: {media_type_str}

                if "/movie/" in href:
                    results.append(Movie(title=title, url=url, poster=poster, year=year))
                elif "/tv/" in href:
                    results.append(TVShow(title=title, url=url, poster=poster, year=year))

    log_debug(f"Returning {len(results)} results.")
    return results

def get_episodes(tv_show: TVShow) -> TVShow:
    """
    Gets the seasons and episodes for a TV show from flixhq.to.
    """
    log_debug(f"BEGIN get_episodes for TV Show: {tv_show.title} ({tv_show.url})")
    
    # Extract media_id from tv_show.url
    media_id_match = re.search(r"/tv/[^/]*-(\d+)", tv_show.url)
    if not media_id_match:
        log_debug(f"Could not extract media ID from TV Show URL: {tv_show.url}")
        return tv_show # Return with empty seasons if ID cannot be extracted
    media_id = media_id_match.group(1)
    log_debug(f"Extracted media_id for TV Show: {media_id}")

    try:
        # Fetching seasons for TV Show via AJAX
        seasons_url = f"{BASE_URL}/ajax/v2/tv/seasons/{media_id}"
        log_debug(f"Fetching seasons for TV Show via AJAX: {seasons_url}")
        response = requests.get(seasons_url, headers=HEADERS)
        response.raise_for_status()
        log_debug(f"Seasons AJAX response status: {response.status_code}")

        # Parses text response with regex
        season_soup = BeautifulSoup(response.text, 'html.parser')
        
        seasons_data = []
        # Regex for seasons: r'href="[^"]*-(\d+)"[^>]*>([^<]*)</a>'
        # Which implies links like <a href="/tv-series/show-name-season-ID">Season Title</a>
        # Let's find all 'a' tags within 'div.dropdown-menu' or directly under 'li'
        
        # A more robust search for season links based on HTML context
        season_elements = season_soup.find_all('a', href=re.compile(r'/tv-series/[^"]+-(\d+)$'))
        if not season_elements:
             # Fallback to general link-items if direct tv-series-season pattern not found
            season_elements = season_soup.find_all('a', class_='dropdown-item')
        
        for season_link in season_elements:
            # Extract season_id from href
            season_id_match = re.search(r'-(\d+)$', season_link['href'])
            if season_id_match:
                season_id = season_id_match.group(1)
                season_title = season_link.text.strip()
                seasons_data.append({'id': season_id, 'title': season_title})

        log_debug(f"Extracted {len(seasons_data)} seasons: {seasons_data}")

        if not seasons_data:
            log_debug("No seasons found via AJAX /v2/tv/seasons/. Falling back to direct list.")
            return _get_episodes_from_direct_list(tv_show) # Removed soup parameter
        
        # Fetch episodes for each season via AJAX
        for s_data in seasons_data:
            season = Season(title=s_data['title'])
            # Fetch episodes for season via AJAX
            episodes_ajax_url = f"{BASE_URL}/ajax/v2/season/episodes/{s_data['id']}"
            log_debug(f"Fetching episodes for season {s_data['title']} via AJAX: {episodes_ajax_url}")
            
            episodes_response = requests.get(episodes_ajax_url, headers=HEADERS)
            episodes_response.raise_for_status()
            log_debug(f"Episodes AJAX response status for season {s_data['title']}: {episodes_response.status_code}")
            
            # Parses text response with regex
            episodes_soup = BeautifulSoup(episodes_response.text, 'html.parser')
            episode_items = episodes_soup.find_all('a', class_='eps-item') # Common class for episode links
            
            # For TV, data_id is passed to get_episode_servers
            for ep_item in episode_items:
                episode_data_id = ep_item.get('data-id') 
                episode_title = ep_item.get('title', 'Unknown Episode').strip() # Full title
                if episode_data_id:
                    # Construct episode URL as per our project's model, using a best guess for the base.
                    # This URL is primarily for identification, not direct streaming.
                    # The `get_stream_url` will resolve the actual stream.
                    episode_url = f"{tv_show.url}/season/{s_data['id']}/episode/{episode_data_id}"
                    season.episodes.append(Episode(title=episode_title, url=episode_url, data_id=episode_data_id, poster=tv_show.poster)) # Add data_id and poster to Episode
            
            log_debug(f"Found {len(season.episodes)} episodes for season {s_data['title']}.")
            tv_show.seasons.append(season)

        return tv_show

    except requests.exceptions.RequestException as e:
        log_debug(f"Request failed in get_episodes for {tv_show.url}: {e}")
        return tv_show # Return original TVShow object on error
    except Exception as e:
        log_debug(f"Unexpected error in get_episodes for {tv_show.url}: {e}")
        return tv_show # Return original TVShow object on error

def _get_episodes_from_direct_list(tv_show: TVShow) -> TVShow:
    """
    Fallback for TV shows that might list episodes directly without season selection.
    """
    log_debug(f"Attempting _get_episodes_from_direct_list for {tv_show.title}. This implies seasons were not found in JSON data.")
    main_season = Season(title="Season 1") # Assume a single season if no explicit selection
    
    # For now, just return the show with an empty season if no direct list is found
    tv_show.seasons.append(main_season)
    return tv_show

def _get_episode_servers(episode_data_id: str) -> Optional[str]:
    """
    Gets the server ID for a given episode data ID.
    """
    try:
        servers_url = f"{BASE_URL}/ajax/v2/episode/servers/{episode_data_id}"
        log_debug(f"Fetching episode servers: {servers_url}")
        response = requests.get(servers_url, headers=HEADERS)
        response.raise_for_status()
        log_debug(f"Episode servers response status: {response.status_code}")

        content = response.text.replace("\n", "").replace(
            'class="nav-item"', '\nclass="nav-item"' 
        )
        server_pattern = re.compile(r'data-id="(\d+)"[^>]*title="([^"]*)"') # Fixed regex here
        matches = server_pattern.findall(content)
        
        servers = []
        for server_id, server_name in matches:
            servers.append({"id": server_id, "name": server_name.strip()})
        log_debug(f"Found servers: {servers}")

        preferred_provider = "Vidcloud" 
        for server in servers:
            if preferred_provider.lower() in server["name"].lower():
                log_debug(f"Selected preferred server: {server['name']} with ID: {server['id']}")
                return server["id"]
        if servers:
            log_debug(f"Selected first available server: {servers[0]['name']} with ID: {servers[0]['id']}")
            return servers[0]["id"]
        
        log_debug("No servers found for episode.")
        return None
    except requests.exceptions.RequestException as e:
        log_debug(f"Request failed in _get_episode_servers: {e}")
        return None
    except Exception as e:
        log_debug(f"Unexpected error in _get_episode_servers: {e}")
        return None

def _get_embed_link(server_id: str) -> Optional[str]:
    """
    Gets the embed link for a given server ID.
    """
    try:
        sources_url = f"{BASE_URL}/ajax/episode/sources/{server_id}"
        _debug_print(f"Fetching embed link: {sources_url}")
        response = requests.get(sources_url, headers=HEADERS)
        response.raise_for_status()
        _debug_print(f"Embed link response status: {response.status_code}")

        # Parse JSON response properly instead of using fragile regex
        json_data = response.json()
        _debug_print(f"Embed link response data: {json_data}")
        
        if "link" in json_data:
            embed_link = json_data["link"]
            _debug_print(f"Extracted embed link: {embed_link}")
            return embed_link
        
        _debug_print("No 'link' found in embed link response.")
        return None
    except requests.exceptions.RequestException as e:
        _debug_print(f"Request failed in _get_embed_link: {e}")
        return None
    except ValueError as e:
        # ValueError catches both json.JSONDecodeError and requests.exceptions.JSONDecodeError
        _debug_print(f"JSON decode error in _get_embed_link: {e}. Response was: {response.text[:500]}")
        return None
    except Exception as e:
        _debug_print(f"Unexpected error in _get_embed_link: {e}")
        return None

def _debug_print(message: str):
    """Print debug messages to stderr to avoid being captured by TUI."""
    print(f"[DEBUG] {message}", file=sys.stderr)


def config_aes_unsalt(key: bytes, salt: bytes, key_len=32, iv_len=16):
    key_iv = b""
    prev = b""
    while len(key_iv) < (key_len + iv_len):
        prev = MD5.new(prev + key + salt).digest()
        key_iv += prev
    return key_iv[:key_len], key_iv[key_len : key_len + iv_len]

def config_aes_decrypt(ciphertext_b64: str, key: str):
    ciphertext = base64.b64decode(ciphertext_b64)
    key_encoded = key.encode()
    if ciphertext[:8] == b"Salted__":
        salt = ciphertext[8:16]
        ciphertext = ciphertext[16:]
        key_encoded, iv_encoded = config_aes_unsalt(key_encoded, salt)
    else:
        return ""
    cipher = AES.new(key_encoded, AES.MODE_CBC, iv_encoded)
    decrypted = cipher.decrypt(ciphertext)
    pad_len = decrypted[-1]
    return decrypted[:-pad_len].decode("latin-1")

def decrypt_stream_url(embed_link: str, preferred_subs_languages: list[str]) -> tuple[Optional[str], list[str]]:
    """
    Decodes an embed-1 link to get the actual streamable URL locally.
    """
    _debug_print(f"Attempting to extract stream from embed link: {embed_link}")
    
    try:
        response = requests.get(embed_link, headers={"User-Agent": HEADERS["User-Agent"], "Referer": BASE_URL})
        response.raise_for_status()
        html = response.text
        
        token = None
        match = re.search(r"[a-zA-Z0-9]{48}", html)
        if match:
            token = match.group(0)
        if not token:
            match = re.search(r"window\._lk_db\s*=\s*({.*?});", html)
            if match:
                token_parts = re.findall(r'"(.*?)"', match.group(1))
                token = "".join(token_parts)
                
        base_url_match = re.match(r"https://[a-zA-Z0-9.-]+", embed_link)
        if not base_url_match:
            _debug_print("Could not extract domain from embed link.")
            return None, []
        domain = base_url_match.group(0)
        
        embed_id_match = re.search(r"/e-1/([^?]+)", embed_link)
        if not embed_id_match:
            _debug_print("Could not extract embed ID from embed link.")
            return None, []
            
        embed_id = embed_id_match.group(1)
        sources_url = f"{domain}/embed-1/v3/e-1/getSources?id={embed_id}"
        if token:
            sources_url += f"&_k={token}"
            
        s_res = requests.get(sources_url, headers={
            "User-Agent": HEADERS["User-Agent"],
            "Referer": embed_link,
            "X-Requested-With": "XMLHttpRequest"
        })
        s_res.raise_for_status()
        data = s_res.json()
        
        sources = None
        if data.get("encrypted") or isinstance(data.get("sources"), str):
            sources_encrypted = data["sources"]
            keys_urls = ["https://keys.hs.vc/", "https://key.hi-anime.site/"]
            aes_keys = []
            for u in keys_urls:
                try:
                    k_res = requests.get(u)
                    if k_res.status_code == 200:
                        kd = k_res.json()
                        if "rabbitstream" in kd and kd["rabbitstream"].get("success"):
                            aes_keys.append(kd["rabbitstream"]["key"])
                        elif "rabbit" in kd:
                            aes_keys.append(kd["rabbit"])
                except Exception as e:
                    _debug_print(f"Failed to fetch key from {u}: {e}")
            for key in aes_keys:
                try:
                    dec = config_aes_decrypt(sources_encrypted, key)
                    sources = json.loads(dec)
                    break
                except Exception:
                    pass
        else:
            sources = data.get("sources", [])
            
        video_link = None
        if sources and isinstance(sources, list):
            video_link = sources[0].get("file")
            
        subs_links = []
        found_subs: dict[str, str] = {}
        tracks = data.get("tracks", [])
        for track in tracks:
            file_url = track.get("file")
            label = track.get("label", "").lower()
            if file_url and label:
                for lang_pref in preferred_subs_languages:
                    if lang_pref in label and lang_pref not in found_subs:
                        found_subs[lang_pref] = file_url
                        break
        
        subs_links = [found_subs[lang] for lang in preferred_subs_languages if lang in found_subs]
        return video_link, subs_links
        
    except Exception as e:
        _debug_print(f"Unexpected error in decrypt_stream_url: {e}")
        return None, []

def get_stream_url(media: Media, subs_language: str = "english") -> tuple[Optional[str], list[str]]:
    """
    Gets the streamable URL for a movie or a TV show episode from flixhq.to.
    """
    log_debug(f"Attempting to get stream URL for: {media.title} ({media.url})")
    
    # Extract media_id from media.url
    media_id_match = re.search(r"/[^/]*-(\d+)", media.url) # General regex for ID
    if not media_id_match:
        log_debug(f"Could not extract media ID from URL: {media.url}")
        return None
    media_id = media_id_match.group(1)
    log_debug(f"Extracted media_id: {media_id}")

    episode_data_id_to_fetch = None

    if isinstance(media, Movie):
        # Movie function logic
        try:
            movie_episodes_url = f"{BASE_URL}/ajax/movie/episodes/{media_id}"
            log_debug(f"Fetching movie servers: {movie_episodes_url}")
            response = requests.get(movie_episodes_url, headers=HEADERS)
            response.raise_for_status()
            log_debug(f"Movie servers response status: {response.status_code}")

            server_soup = BeautifulSoup(response.text, 'html.parser')
            server_links = server_soup.find_all('a', class_='link-item')
            selected_server_id = None
            
            for link in server_links:
                if "vidcloud" in link.get('title', '').lower():
                    selected_server_id = link.get('data-linkid')
                    log_debug(f"Found preferred Vidcloud server for movie: {selected_server_id}")
                    break
            
            if not selected_server_id and server_links: # Fallback to first if Vidcloud not found
                selected_server_id = server_links[0].get('data-linkid')
                log_debug(f"Falling back to first server for movie: {selected_server_id}")

            if selected_server_id:
                final_embed_url = _get_embed_link(selected_server_id)
                if final_embed_url:
                    # Pass a list of preferred languages to decrypt_stream_url
                    return decrypt_stream_url(final_embed_url, preferred_subs_languages=["arabic", "english"])
                else:
                    return None, []
            else:
                log_debug("Could not find any server ID for movie.")
                return None, []

        except requests.exceptions.RequestException as e:
            log_debug(f"Request failed in movie get_stream_url: {e}")
            return None, [] # Changed to return tuple
        except Exception as e:
            log_debug(f"Unexpected error in movie get_stream_url: {e}")
            return None, [] # Changed to return tuple

    elif isinstance(media, Episode):
        # The URL for an Episode is already constructed to contain the data_id
        # Example: {tv_show.url}/season/{s_data['id']}/episode/{episode_data_id}
        # In this case, media.url contains the episode_data_id directly at the end.
        # This will be passed to _get_episode_servers
        episode_id_regex = r"/episode/(\d+)$"
        episode_data_id_match = re.search(episode_id_regex, media.url)

        if not episode_data_id_match:
            log_debug(f"Could not extract episode_data_id from Episode URL: {media.url}")
            return None, [] # Changed to return tuple
        episode_data_id_to_fetch = episode_data_id_match.group(1)
        log_debug(f"Extracted episode_data_id for TV Episode: {episode_data_id_to_fetch}")

    if not episode_data_id_to_fetch:
        log_debug("No episode data ID available to fetch servers.")
        return None, []

    # Now get server_id and then embed_link
    server_id = _get_episode_servers(episode_data_id_to_fetch)
    if not server_id:
        log_debug(f"Failed to get server ID for episode_data_id: {episode_data_id_to_fetch}")
        return None, []

    final_embed_url = _get_embed_link(server_id)
    if final_embed_url:
        return decrypt_stream_url(final_embed_url, preferred_subs_languages=["arabic", "english"])
    else:
        return None, []
