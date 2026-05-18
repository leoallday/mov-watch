import os
import sys
import time
import shutil
import subprocess
import tempfile
from typing import Optional
from .utils import is_bundled
from mov_watch import api


class PlayerManager:
    def __init__(self, rpc_manager=None, console=None):
        self.temp_mpv_path = None
        self.rpc_manager = rpc_manager
        self.console = console

    def get_mpv_path(self) -> Optional[str]:
        if is_bundled():
            exe_name = 'mpv.exe' if os.name == 'nt' else 'mpv'
            bundled_mpv = os.path.join(sys._MEIPASS, 'mpv', exe_name)
            if os.path.exists(bundled_mpv):
                if not self.temp_mpv_path or not os.path.exists(self.temp_mpv_path):
                    temp_dir = tempfile.mkdtemp(prefix='mov-watch_mpv_')
                    self.temp_mpv_path = os.path.join(temp_dir, exe_name)
                    shutil.copy2(bundled_mpv, self.temp_mpv_path)
                    if os.name != 'nt':
                        st = os.stat(self.temp_mpv_path)
                        os.chmod(self.temp_mpv_path, st.st_mode | 0o111)
                return self.temp_mpv_path
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            exe_name = 'mpv.exe' if os.name == 'nt' else 'mpv'
            dev_mpv = os.path.join(base_dir, 'mpv', exe_name)
            if os.path.exists(dev_mpv):
                return dev_mpv
            local_mpv = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mpv', exe_name)
            if os.path.exists(local_mpv):
                return local_mpv
            if shutil.which('mpv'):
                return 'mpv'
            return 'mpv'
        return 'mpv'

    def cleanup_temp_mpv(self):
        if self.temp_mpv_path and os.path.exists(self.temp_mpv_path):
            try:
                temp_dir = os.path.dirname(self.temp_mpv_path)
                shutil.rmtree(temp_dir, ignore_errors=True)
            except (OSError, PermissionError):
                pass

    def play(self, url: str, title: str, player_type: str = 'mpv',
             subtitle_urls: Optional[list[str]] = None,
             cookies: Optional[list[dict]] = None,
             referer: Optional[str] = None):
        api.log_debug(f"DEBUG: PlayerManager.play - Received URL: {url}, player: {player_type}")
        try:
            if player_type == 'vlc':
                self._play_vlc(url, title)
            elif player_type == 'browser':
                self._play_browser(url, title)
            else:
                self._play_mpv(url, title, subtitle_urls, cookies, referer)
        except FileNotFoundError:
            if self.console:
                from rich.text import Text
                self.console.print(Text(f"{player_type.upper()} executable not found. Please install it or check path.", style="bold red"))
                input("Press Enter to continue...")
            else:
                print(f"{player_type.upper()} executable not found. Please install it or check path.", file=sys.stderr)
                input("Press Enter to continue...")
        except Exception as e:
            if self.console:
                from rich.text import Text
                self.console.print(Text(f"Error launching player: {str(e)}", style="bold red"))
                input("Press Enter to continue...")
            else:
                print(f"Error launching player: {str(e)}", file=sys.stderr)
                input("Press Enter to continue...")

    def _play_vlc(self, url: str, title: str):
        vlc_path = shutil.which('vlc')
        if not vlc_path:
            if os.name == 'nt':
                paths = [
                    r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                    r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
                ]
                for p in paths:
                    if os.path.exists(p):
                        vlc_path = p
                        break
            elif sys.platform == 'darwin':
                paths = [
                    "/Applications/VLC.app/Contents/MacOS/VLC",
                    os.path.expanduser("~/Applications/VLC.app/Contents/MacOS/VLC")
                ]
                for p in paths:
                    if os.path.exists(p):
                        vlc_path = p
                        break
        if not vlc_path:
            raise FileNotFoundError("VLC not found")
        vlc_args = [
            vlc_path, '--fullscreen', '--play-and-exit',
            '--meta-title', title, url
        ]
        subprocess.run(vlc_args, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _play_browser(self, url: str, title: str):
        api.log_debug(f"DEBUG: _play_browser - Opening: {url}")
        browsers = []
        if os.name != 'nt':
            possible_browsers = ['brave-browser', 'firefox', 'google-chrome', 'chromium', 'midori', 'lynx']
            for b in possible_browsers:
                if shutil.which(b):
                    browsers.append(b)
        if os.name == 'nt':
            windows_browsers = [
                r"C:\Program Files\Brave\Brave-Browser\Application\brave.exe",
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files\Mozilla Firefox\firefox.exe",
            ]
            for p in windows_browsers:
                if os.path.exists(p):
                    browsers.append(p)
        import webbrowser
        browser = None
        if browsers:
            for b in browsers:
                try:
                    if os.name == 'nt':
                        browser = subprocess.Popen([b, url])
                    else:
                        subprocess.Popen([b, url],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
                    api.log_debug(f"DEBUG: Opened in browser: {b}")
                    break
                except Exception as e:
                    api.log_debug(f"DEBUG: Failed to open in {b}: {e}")
        if browser is None and not browsers:
            webbrowser.open(url)
            api.log_debug(f"DEBUG: Opened in default browser")

    def _get_mpv_config_options(self) -> set[str]:
        options = set()
        config_paths = []
        if os.name == 'nt':
            appdata = os.getenv('APPDATA')
            if appdata:
                config_paths.append(os.path.join(appdata, 'mpv', 'mpv.conf'))
        else:
            config_paths.append(os.path.expanduser('~/.config/mpv/mpv.conf'))
            config_paths.append('/etc/mpv/mpv.conf')
            config_paths.append(os.path.expanduser('~/.mpv/config'))
        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                if '=' in line:
                                    key = line.split('=')[0].strip()
                                else:
                                    key = line.split()[0].strip()
                                options.add(key)
                except (IOError, OSError) as e:
                    api.log_debug(f"DEBUG: Failed to read mpv config at {path}: {e}")
        return options

    def _write_cookies_file(self, cookies: list[dict]) -> Optional[str]:
        if not cookies:
            return None
        try:
            fd, path = tempfile.mkstemp(prefix='mov-watch-cookies-', suffix='.txt')
            with os.fdopen(fd, 'w') as f:
                f.write("# Netscape HTTP Cookie File\n")
                for c in cookies:
                    domain = c.get('domain', '')
                    if domain.startswith('.'):
                        domain = domain[1:]
                    flag = 'TRUE'
                    path_val = c.get('path', '/')
                    secure = 'TRUE' if c.get('secure', False) else 'FALSE'
                    expiry = str(int(c.get('expires', 0))) if c.get('expires') else '0'
                    name = c.get('name', '')
                    value = c.get('value', '')
                    f.write(f"{domain}\t{flag}\t{path_val}\t{secure}\t{expiry}\t{name}\t{value}\n")
            api.log_debug(f"Wrote {len(cookies)} cookies to {path}")
            return path
        except Exception as e:
            api.log_debug(f"Failed to write cookies file: {e}")
            return None

    def _play_mpv(self, url: str, title: str,
                  subtitle_urls: Optional[list[str]] = None,
                  cookies: Optional[list[dict]] = None,
                  referer: Optional[str] = None):
        api.log_debug(f"DEBUG: _play_mpv - Received URL for playback: {url}")
        mpv_path = self.get_mpv_path()
        if mpv_path != 'mpv' and not os.path.exists(mpv_path):
            raise FileNotFoundError(f"MPV not found at: {mpv_path}")

        config_options = self._get_mpv_config_options()
        api.log_debug(f"DEBUG: _play_mpv - Options found in mpv.conf: {config_options}")

        mpv_args = [
            mpv_path,
            '--fullscreen',
            '--fs-screen=0',
            '--keep-open=yes',
            '--ontop',
            '--cache=yes',
            '--cache-pause=yes',
            '--cache-pause-initial=yes',
            '--cache-pause-wait=3',
            '--demuxer-max-bytes=256M',
            '--demuxer-max-back-bytes=128M',
            '--cache-secs=30',
        ]

        if 'hwdec' not in config_options:
            mpv_args.append('--hwdec=auto-safe')
        else:
            api.log_debug("DEBUG: _play_mpv - hwdec already in mpv.conf, skipping default")
        if 'vo' not in config_options:
            mpv_args.append('--vo=gpu')
        else:
            api.log_debug("DEBUG: _play_mpv - vo already in mpv.conf, skipping default")
        if 'profile' not in config_options:
            mpv_args.append('--profile=gpu-hq')

        mpv_args.append('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        cookies_file = None
        if cookies:
            cookies_file = self._write_cookies_file(cookies)
        if cookies_file:
            mpv_args.append('--cookies=yes')
            mpv_args.append(f'--cookies-file={cookies_file}')

        if referer:
            mpv_args.append(f'--http-header-fields=Referer: {referer}')

        mpv_args.extend([
            '--sub-auto=fuzzy',
            '--sub-file-paths=subs',
            '--slang=ara,ar,eng,en',
            '--alang=jpn,ja,eng,en',
            '--title=' + title,
            '--force-window=yes',
            url
        ])

        if subtitle_urls:
            for sub_url in subtitle_urls:
                mpv_args.append(f'--sub-file={sub_url}')

        result = subprocess.run(
            mpv_args,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL
        )

        if cookies_file and os.path.exists(cookies_file):
            try:
                os.remove(cookies_file)
            except OSError:
                pass

        api.log_debug(f"DEBUG: _play_mpv - MPV stdout: {result.stdout.decode(errors='ignore')}")
        api.log_debug(f"DEBUG: _play_mpv - MPV stderr: {result.stderr.decode(errors='ignore')}")

        if result.returncode != 0:
            if self.console:
                from rich.text import Text
                self.console.print(Text(f"MPV exited with error code {result.returncode}", style="bold red"))
                input("Press Enter to continue...")
