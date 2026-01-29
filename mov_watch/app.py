import sys
import atexit
from pathlib import Path
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.box import HEAVY

from .config import COLOR_PROMPT, COLOR_BORDER, COLOR_TITLE
from .ui import UIManager
from . import api
from .monitoring import monitor
from .player import PlayerManager
from .discord_rpc import DiscordRPCManager
from .models import Movie, TVShow
from .utils import download_file, flush_stdin
from .history import HistoryManager
from .settings import SettingsManager
from .favorites import FavoritesManager
from .updater import check_for_updates, get_version_status
from .deps import ensure_dependencies
from .cli import run_simple_cli
from .config import GOODBYE_ART
import shutil
import argparse

class MovieWatchApp:
    def __init__(self):
        self.ui = UIManager()
        self.api = api
        self.rpc = DiscordRPCManager()
        self.settings = SettingsManager()
        self.player = PlayerManager(rpc_manager=self.rpc, console=self.ui.console)
        self.history = HistoryManager()
        self.favorites = FavoritesManager()
        self.version_info = None
        self.current_mode = "tui"
        self.force_cli = False

    def run(self):
        parser = argparse.ArgumentParser(
            description="mov-watch: A CLI tool to browse and watch movies and TV shows.",
            formatter_class=argparse.RawTextHelpFormatter
        )
        parser.add_argument('-i', '--interactive', action='store_true', help="Force minimal interactive CLI mode")
        parser.add_argument('-v', '--version', action='store_true', help="Show version information")
        parser.add_argument('query', nargs='*', help="Media name to search for")
        parser.add_argument('--subs-lang', '-l', default='english', help="Specify subtitle language (e.g., 'english', 'arabic'). Default is 'english'.")
        
        args = parser.parse_args()
        
        if args.version:
            from .version import __version__
            print(f"mov-watch v{__version__}")
            sys.exit(0)
            
        self.force_cli = args.interactive
        self.subtitle_language = args.subs_lang # Store subtitle language
        initial_query = " ".join(args.query) if args.query else None

        if not ensure_dependencies():
            print("\n[!] Cannot start without required dependencies.")
            input("Press ENTER to exit...")
            sys.exit(1)
        
        atexit.register(self.cleanup)
        
        import threading
        rpc_connected = {'status': None}
        
        if self.settings.get('discord_rpc'):
            def connect_rpc():
                rpc_connected['status'] = self.rpc.connect()
            threading.Thread(target=connect_rpc, daemon=True).start()
        
        threading.Thread(target=lambda: monitor.track_app_start(), daemon=True).start()
        
        self.rpc_status = rpc_connected

        try:
            self.unified_loop(initial_query)
        except KeyboardInterrupt:
            self.handle_exit()
        except Exception as e:
            self.handle_error(e)
        finally:
            self.cleanup()

    def unified_loop(self, query=None):
        while True:
            is_narrow = shutil.get_terminal_size().columns < 80
            
            if self.force_cli or is_narrow:
                self.current_mode = "cli"
                result = self.run_cli_mode(query)
                query = None 
                if result == "SWITCH_TO_TUI":
                    if self.force_cli:
                         pass
                    continue
                break
            else:
                self.current_mode = "tui"
                result = self.run_tui_mode(query)
                query = None
                if result == "SWITCH_TO_CLI":
                    continue
                break

    def run_cli_mode(self, query=None):
        deps = {
            'api': self.api,
            'player': self.player,
            'history': self.history,
            'settings': self.settings,
            'rpc': self.rpc
        }
        return run_simple_cli(query, deps=deps, subtitle_language=self.subtitle_language)

    def run_tui_mode(self, query=None):
        while True:
            if '-i' not in sys.argv and shutil.get_terminal_size().columns < 80:
                return "SWITCH_TO_CLI"

            self.ui.clear() 
            
            vertical_space = self.ui.console.height - 14
            top_padding = (vertical_space // 2) - 2
            
            if top_padding > 0:
                self.ui.print(Text("\n" * top_padding))

            self.ui.print(Align.center(self.ui.get_header_renderable()))
            self.ui.print()
            
            if self.settings.get('discord_rpc'):
                if hasattr(self, 'rpc_status'):
                    if self.rpc_status['status'] is True:
                        self.ui.print(Align.center(Text.from_markup("Discord Rich Presence ✅", style="secondary")))
                    elif self.rpc_status['status'] is None:
                        self.ui.print(Align.center(Text.from_markup("Discord Rich Presence [dim](connecting...)[/dim]", style="dim")))
                    else:
                        self.ui.print(Align.center(Text.from_markup("Discord Rich Presence [dim](disabled)[/dim]", style="dim")))
            else:
                self.ui.print(Align.center(Text.from_markup("Discord Rich Presence [dim](disabled)[/dim]", style="dim")))
            self.ui.print()
            
            keybinds_panel = Panel(
                Text("S: Search | L: History | F: Favorites | C: Settings | Q: Quit", style="info", justify="center"),
                box=HEAVY,
                border_style=COLOR_BORDER
            )
            self.ui.print(Align.center(keybinds_panel))
            self.ui.print()
            
            prompt_string = f" {Text('›', style=COLOR_PROMPT)} "
            pad_width = (self.ui.console.width - 30) // 2
            padding = " " * max(0, pad_width)
            
            flush_stdin()
            
            query = Prompt.ask(f"{padding}{prompt_string}", console=self.ui.console).strip().lower()
            
            if query in ['q', 'quit', 'exit']:
                break
            
            results = []
            
            if query == 's':
                 term = Prompt.ask(f"{padding} Enter Search Term: ", console=self.ui.console).strip()
                 if term:
                    self.rpc.update_searching()
                    results = self.ui.run_with_loading("Searching...", self.api.search, term)
            elif query == 'l':
                self.rpc.update_history()
                self.handle_history()
                continue
            elif query == 'f':
                self.rpc.update_favorites()
                self.handle_favorites()
                continue
            elif query == 'c':
                self.rpc.update_settings()
                self.ui.settings_menu(self.settings)
                continue
            elif query == 'a':
                self.ui.show_credits()
                continue
            elif query:
                self.rpc.update_searching()
                results = self.ui.run_with_loading("Searching...", self.api.search, query)
            else:
                continue
            
            if not results:
                self.ui.render_message(
                    "✗ No Media Found", 
                    f"No media matching '{query}' was found.", 
                    "error"
                )
                continue
            
            self.handle_media_selection(results)

    def handle_media_selection(self, results):
        while True:
            media_idx = self.ui.media_selection_menu(results)
            
            if media_idx == -1:
                sys.exit(0)
            if media_idx is None:
                return

            selected_media = results[media_idx]
            
            if isinstance(selected_media, Movie):
                self.handle_movie_selection(selected_media)
            elif isinstance(selected_media, TVShow):
                self.handle_tvshow_selection(selected_media)

    def handle_movie_selection(self, movie):
        self.play_media(movie)

    def handle_tvshow_selection(self, show):
        self.rpc.update_viewing_media(show.title, show.poster)
        
        details = self.ui.run_with_loading(
            "Loading episodes...",
            self.api.get_episodes,
            show
        )
        
        if not details.seasons:
            self.ui.render_message(
                "✗ No Seasons",
                f"No seasons found for '{show.title}'.",
                "error"
            )
            return

        selected_season = self.ui.season_selection_menu(details.seasons)
        if not selected_season:
            return

        self.handle_episode_selection(show, selected_season)

    def handle_episode_selection(self, show, season):
        while True:
            last_watched = self.history.get_last_watched(show.title)
            is_fav = self.favorites.is_favorite(show.title)

            ep_idx = self.ui.episode_selection_menu(
                show.title, 
                season.episodes, 
                self.rpc, 
                show.poster,
                last_watched_ep=last_watched,
                is_favorite=is_fav,
                media_details=None
            )
            
            if ep_idx == -1:
                sys.exit(0)
            elif ep_idx is None:
                self.rpc.update_browsing()
                return True
            elif ep_idx == 'toggle_fav':
                if is_fav:
                    self.favorites.remove(show.title)
                else:
                    self.favorites.add(show.title, show.poster)
                continue
            
            selected_episode = season.episodes[ep_idx]
            self.play_media(selected_episode, show.title)

    def play_media(self, media, show_title=None):
        title = show_title if show_title else media.title
        episode_title = media.title if show_title else "Movie"

        self.rpc.update_watching(title, episode_title, media.poster)
        
        
        video_url, subtitle_urls = self.ui.run_with_loading(
            "Extracting stream link...",
            self.api.get_stream_url,
            media,
            self.subtitle_language
        )
        
        if not video_url:
            self.ui.render_message("✗ Error", "Failed to extract stream link.", "error")
            return
        
        # Pass all found subtitle URLs to the player
        if subtitle_urls:
            self.api.log_debug(f"DEBUG: Found subtitle URLs (TUI): {subtitle_urls}")

        player_type = self.settings.get('player')
        
        watching_text = Text()
        watching_text.append("▶ ", style=COLOR_TITLE + " blink")
        watching_text.append(title, style="bold")
        if show_title:
            watching_text.append("\nEpisode ", style="secondary")
            watching_text.append(str(episode_title), style=COLOR_TITLE + " bold")
        watching_text.append(" ◀", style=COLOR_TITLE + " blink")

        watching_panel = Panel(
            Align.center(watching_text, vertical="middle"),
            title=Text("NOW PLAYING", style=COLOR_TITLE + " bold"),
            box=HEAVY,
            border_style=COLOR_BORDER,
            padding=(2, 4),
            width=60
        )
        
        self.ui.clear()
        self.ui.console.print(Align.center(watching_panel, vertical="middle", height=self.ui.console.height))
        
        self.player.play(video_url, f"{title} - {episode_title}", player_type=player_type, subtitle_urls=subtitle_urls)
        self.ui.clear()
        self.history.mark_watched(title, episode_title)
        self.rpc.update_viewing_media(title, media.poster)

    def handle_history(self):
        while True:
            history_items = self.history.get_history()
            if not history_items:
                self.ui.render_message("History", "No watch history found.", "info")
                return

            selected_idx = self.ui.history_menu(history_items)
            if selected_idx is None:
                return

            selected_item = history_items[selected_idx]
            
            # Since history only stores metadata, we need to fetch the full media object
            results = self.ui.run_with_loading(
                f"Loading '{selected_item['title']}'...", 
                self.api.search, 
                selected_item['title']
            )

            if not results:
                 self.ui.render_message("Error", f"Could not find media '{selected_item['title']}'", "error")
                 continue

            # Find exact match if possible, otherwise use first result
            media = results[0]
            for res in results:
                if res.title == selected_item['title']:
                    media = res
                    break
            
            if isinstance(media, Movie):
                self.handle_movie_selection(media)
            elif isinstance(media, TVShow):
                self.handle_tvshow_selection(media)

    def handle_favorites(self):
        while True:
            fav_items = self.favorites.get_all()
            if not fav_items:
                 self.ui.render_message("Favorites", "No favorites found.", "info")
                 return

            result = self.ui.favorites_menu(fav_items)
            if result is None:
                return
            
            selected_idx, action = result
            selected_item = fav_items[selected_idx]

            if action == 'remove':
                self.favorites.remove(selected_item['title'])
                continue
            
            elif action == 'watch':
                 # Same logic as history retrieval
                results = self.ui.run_with_loading(
                    f"Loading '{selected_item['title']}'...", 
                    self.api.search, 
                    selected_item['title']
                )

                if not results:
                     self.ui.render_message("Error", f"Could not find media '{selected_item['title']}'", "error")
                     continue

                media = results[0]
                for res in results:
                    if res.title == selected_item['title']:
                        media = res
                        break
                
                if isinstance(media, Movie):
                    self.handle_movie_selection(media)
                elif isinstance(media, TVShow):
                    self.handle_tvshow_selection(media)

    def handle_exit(self):
        self.ui.clear()
        
        panel = Panel(
            Text("👋 Interrupted - Goodbye!", justify="center", style="info"),
            title=Text("EXIT", style="title"),
            box=HEAVY,
            padding=1,
            border_style=COLOR_BORDER
        )
        
        self.ui.print(Align.center(panel, vertical="middle", height=self.ui.console.height))

    def handle_error(self, e):
        self.ui.clear()
        self.ui.console.print_exception()
        
        panel = Panel(
            Text(f"✗ Unexpected error: {e}", justify="center", style="error"),
            title=Text("CRITICAL ERROR", style="title"),
            box=HEAVY,
            padding=1,
            border_style=COLOR_BORDER
        )
        
        self.ui.print(Align.center(panel, vertical="middle", height=self.ui.console.height))
        input("\nPress ENTER to exit...")

    def cleanup(self):
        try:
            self.rpc.disconnect()
        except Exception:
            pass
        
        try:
            self.player.cleanup_temp_mpv()
        except Exception:
            pass
        
        if self.current_mode != "cli":
            self.ui.clear()
            from .config import COLOR_ASCII
            
            self.ui.print("\n" * 2)
            self.ui.print(Align.center(Text(GOODBYE_ART, style=COLOR_ASCII)))
            self.ui.print("\n")

def main():
    home_dir = Path.home()
    db_dir = home_dir / ".mov-watch" / "database"
    db_dir.mkdir(parents=True, exist_ok=True)
    
    app = MovieWatchApp()
    app.run()

if __name__ == "__main__":
    main()