import os
import sys
import subprocess
import shutil
import time
import re
from mov_watch import api
from mov_watch.player import PlayerManager
from mov_watch.models import Movie, TVShow
from mov_watch.history import HistoryManager
from mov_watch.version import APP_VERSION
from mov_watch.config import MINIMAL_ASCII_ART, GOODBYE_ART, THEMES
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

class CliWrapper:
    def __init__(self, api, player, history, settings, rpc, subtitle_language: str = "english"):
        self.api = api
        self.player = player
        self.history = history
        self.settings_manager = settings
        self.rpc = rpc
        self.fzf_available = shutil.which('fzf') is not None
        self.console = Console()
        self.subtitle_language = subtitle_language

    def get_theme_color(self, key="ascii"):
        t_name = self.settings_manager.get("theme")
        theme = THEMES.get(t_name, THEMES["blue"])
        return theme.get(key, "blue")

    def _get_rpc_status_text(self):
        if not self.settings_manager.get('discord_rpc'):
             return Text("")

        if self.rpc.connected:
             return Text("RPC: Connected", style="green")
        else:
             return Text("")

    def _die(self, msg):
        """Exit with error message."""
        print(f"\033[1;31m{msg}\033[0m", file=sys.stderr)
        sys.exit(1)

    def _launcher(self, items, prompt_text, multi=False):
        if not items:
            return []

        if self.fzf_available:
            args = ['fzf', '--ansi', '--reverse', '--cycle', '--prompt', f"{prompt_text} > ", '--bind', 'esc:abort,left:abort']
            if multi:
                args.append('-m')

            input_str = "\n".join(items)

            try:
                result = subprocess.run(
                    args,
                    input=input_str,
                    text=True,
                    encoding='utf-8',
                    stdout=subprocess.PIPE,
                    stderr=None
                )
                if result.returncode == 0:
                    out = result.stdout.strip()
                    if not out:
                        return []
                    return out.split('\n')
                return None
            except Exception as e:
                self._die(f"Error running fzf: {e}")
        else:
            print(f"\033[1;36m{prompt_text}\033[0m")
            for i, item in enumerate(items, 1):
                print(f"{i}. {item}")

            try:
                print("\nEnter selection (e.g. 1, 1-3) or 'b'/'q' to back: ", end='')
                selection = input().strip()

                if selection.lower() in ['b', 'q', 'back']:
                    return None

                files = []

                parts = selection.split()
                for part in parts:
                    if '-' in part:
                         try:
                             start, end = map(int, part.split('-'))
                             for idx in range(start, end + 1):
                                 if 1 <= idx <= len(items):
                                     files.append(items[idx-1])
                         except (ValueError, IndexError):
                             pass
                    elif part.isdigit():
                        idx = int(part) - 1
                        if 0 <= idx < len(items):
                            files.append(items[idx])
                return files
            except Exception:
                return []

    def play_video(self, media, title):
        video_url = None
        subtitle_urls = []
        with self.console.status(f"[bold blue]Fetching stream for {title}...[/bold blue]", spinner="dots"):
            video_url, subtitle_urls = self.api.get_stream_url(media, self.subtitle_language)

        if not video_url:
            print("\033[1;31mCould not get video stream URL.\030m")
            return False
        
        selected_subtitle_url = None
        if subtitle_urls:
            selected_subtitle_url = subtitle_urls[0] # This line becomes effectively unused for player.play, but useful for debugging if needed.
            self.api.log_debug(f"DEBUG: Selected subtitle URL: {selected_subtitle_url}")

        print(f"\033[1;34mPlaying {title}...\030m")
        self.player.play(video_url, title, subtitle_urls=subtitle_urls)

        self.history.mark_watched(title, title)
        self.history.save_history()
        return True

    def _process_media_list(self, results, title="Select Media"):
        media_map = {}
        display_lines = []

        for res in results:
            line = f"{res.title} ({res.year})"
            display_lines.append(line)
            media_map[line] = res

        while True:
            selection = self._launcher(display_lines, title)
            if selection is None:
                break

            if not selection:
                continue

            sel_text = selection[0]
            selected_media = media_map.get(sel_text)

            if not selected_media:
                print("\033[1;31mSelection error: Item not found in map.\033[0m")
                continue

            if isinstance(selected_media, Movie):
                if self.rpc:
                    self.rpc.update_watching(selected_media.title, "Movie", selected_media.poster)
                self.play_video(selected_media, selected_media.title)
                continue

            elif isinstance(selected_media, TVShow):
                if self.rpc:
                    self.rpc.update_viewing_media(selected_media.title, selected_media.poster)

                with self.console.status("[bold blue]Fetching show details...[/bold blue]", spinner="dots"):
                    show_details = self.api.get_episodes(selected_media)

                if not show_details.seasons:
                    print("\033[1;31mNo seasons found for this show.\033[0m")
                    continue

                season_lines = [s.title for s in show_details.seasons]
                selected_season_line_list = self._launcher(season_lines, f"Select Season ({selected_media.title})")

                if not selected_season_line_list:
                    continue

                selected_season_line = selected_season_line_list[0]
                selected_season = next((s for s in show_details.seasons if s.title == selected_season_line), None)

                if not selected_season or not selected_season.episodes:
                    print("\033[1;31mNo episodes found for this season.\033[0m")
                    continue

                ep_map = {ep.title: ep for ep in selected_season.episodes}
                ep_lines = list(ep_map.keys())

                while True:
                    selected_ep_lines = self._launcher(ep_lines, f"Select Episode ({selected_media.title} - {selected_season.title})", multi=True)
                    if selected_ep_lines is None:
                        break

                    if not selected_ep_lines:
                        continue

                    for ep_title in selected_ep_lines:
                        episode = ep_map.get(ep_title)
                        if episode:
                            full_title = f"{selected_media.title} - {episode.title}"
                            if self.rpc:
                                self.rpc.update_watching(selected_media.title, episode.title, selected_media.poster)
                            self.play_video(episode, full_title)
                    break
                continue

    def _print_header(self):
        ascii_color = self.get_theme_color("ascii")
        self.console.print(MINIMAL_ASCII_ART.strip(), style=ascii_color)
        self.console.print(f"  {APP_VERSION} | gh:leoallday/mov-watch", style="dim")

    def run(self, query=None, subtitle_language: str = "english"):
        ascii_color = self.get_theme_color("ascii")
        border_color = self.get_theme_color("border")

        os.system('cls' if os.name == 'nt' else 'clear')
        self._print_header()

        while True:
            if '-i' not in sys.argv:
                cols = shutil.get_terminal_size().columns
                if cols >= 80:
                    return "SWITCH_TO_TUI"

            if not query:
                status_text = self._get_rpc_status_text()
                if status_text.plain:
                    self.console.print(Text("            ") + status_text)
                    self.console.print()
                else:
                    self.console.print()

                try:
                    self.console.print(f"  [{border_color}]╭─   Search for a movie or TV show...[/{border_color}]")
                    self.console.print(f"  [{border_color}]╰─>[/{border_color}] ", end="")
                    query = input().strip()
                except (KeyboardInterrupt, EOFError):
                    print()
                    return

                if query.lower() in ['q', 'quit', 'exit']:
                    return

            if not query:
                continue

            search_q = query
            query = None

            results = []
            with self.console.status(f"[bold green]Searching for: {search_q}...[/bold green]", spinner="earth"):
                if self.rpc: self.rpc.update_searching()
                results = self.api.search(search_q)

            if not results:
                print(f"\033[1;31mNo results found for '{search_q}'\033[0m")
                continue

            self._process_media_list(results, f"Search: {search_q}")

            os.system('cls' if os.name == 'nt' else 'clear')
            self._print_header()

def run_simple_cli(query=None, deps=None, subtitle_language: str = "english"):
    if deps:
        cli = CliWrapper(deps['api'], deps['player'], deps['history'], deps['settings'], deps['rpc'], subtitle_language=subtitle_language)
    else:
        from mov_watch import api
        from mov_watch.player import PlayerManager
        from mov_watch.history import HistoryManager
        from mov_watch.settings import SettingsManager
        from mov_watch.discord_rpc import DiscordRPCManager
        cli = CliWrapper(api, PlayerManager(console=Console()), HistoryManager(), SettingsManager(), DiscordRPCManager(), subtitle_language=subtitle_language)

    exit_code = 0
    result = None
    try:
        result = cli.run(query, subtitle_language=subtitle_language)
        if result == "SWITCH_TO_TUI":
            return "SWITCH_TO_TUI"
    except SystemExit as e:
        if isinstance(e.code, int):
            exit_code = e.code
    except KeyboardInterrupt:
        exit_code = 130
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n\033[1;31mCritical Error: {e}\033[0m")
        input("Press Enter to continue...")
        exit_code = 1
    finally:
        is_switching = result == "SWITCH_TO_TUI"

        if not is_switching:
            print(f"\033[1;36m{GOODBYE_ART.strip()}\033[0m")
            sys.exit(exit_code)