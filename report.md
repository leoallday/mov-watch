# mov-watch — repository audit report

**Date:** 2026-11-18
**Version audited:** 2.3.2 (`main`, clean tree at start)
**Scope:** correctness, cross-platform compatibility, packaging/metadata, documentation, dead code
**Method:** read every module (`mov_watch/*`, `main.py`, `scripts/*`, `aur/*`, workflows, README, packaging files), static import analysis, smoke tests with an isolated `$HOME`, wheel build.

19 files changed (+146 / −109). Nothing was committed and no dependencies were added.

---

## 1. Critical bugs fixed

| # | Bug | Impact | Fix |
|---|-----|--------|-----|
| 1 | `deps.py` declared `def _windows_local_deps_root() -> Path \| None` and `player.py` used `list[str]`/`list[dict]`, but `pyproject.toml`/`setup.py` advertise **Python >= 3.8** | Importing `mov_watch.deps` (and therefore the app) raised `TypeError` on 3.8/3.9 — the package was uninstallable there | Replaced with `Optional[Path]`, `List[str]`, `List[dict]` |
| 2 | Episode list "jump to episode" (**G**) compared `float(ep.display_num)`, but `Episode` had no `display_num` attribute | `AttributeError`, silently swallowed by a bare `except Exception` — the jump prompt never worked | Added an `Episode.display_num` property and compared against `episode_number` (tolerant of `5`, `5.0`, and missing values) |
| 3 | Episode menu returned the strings `'batch_mode'` and `'trailer'` for **M**/**T**, while `app.handle_episode_selection` used the return value as a list index | Pressing **M** crashed the whole app with `TypeError: list indices must be integers` | Removed the two unimplemented key bindings (and the footer hint) and added an `isinstance(ep_idx, int)` guard in `app.py` |
| 4 | `player._play_browser`: `browser` was only assigned on success, and the default-browser fallback was conditioned on `not browsers` | If a browser binary existed but could not be launched, nothing opened and no error was shown | Track an `opened` flag and always fall back to `webbrowser.open()` |
| 5 | `player._play_mpv` called `subprocess.run(..., check=True)` while also having a `returncode != 0` error branch | The branch was dead code: mpv failures surfaced as a generic "Error launching player" and the useful stderr was discarded | `check=False`; the failure path now prints the exit code plus the last 3 stderr lines (Rich and plain-console paths) |
| 6 | VLC playback ignored subtitles and `Referer`, although the stream resolver produces both | VLC users never got subtitles/referrer-gated streams; only mpv did | `_play_vlc` now accepts `subtitle_urls`/`referer` and passes `--sub-file`, `--http-referrer` |
| 7 | `MovieWatchApp.cleanup()` ran from both `finally` and `atexit` | The goodbye screen was printed twice, and RPC/player teardown ran twice on exit | Added an idempotency flag |
| 8 | `api.search()` assumed a JSON list; `get_episodes()` indexed `sd['season']` / `ep['episode']` directly | A dict/error payload or one malformed episode raised `KeyError`/`TypeError` and aborted the session | Payload type checks, `.get()` access, malformed episodes skipped and logged |
| 9 | CLI mode called `history.mark_watched(title, title)`, storing `"Show - Episode"` as the media title | "Continue Watching" re-searched for a title that does not exist, and TUI per-show resume returned `None` for anything watched in CLI mode | `play_video(..., show_title=...)`; history now stores show title + episode separately (matching TUI behaviour) |
| 10 | `history.save_history()`/`get_history()` assumed every entry is a dict | A single corrupt entry raised `AttributeError` and made history unusable | Non-dict entries are filtered |
| 11 | `utils.RawTerminal._lock = threading.Lock() if 'threading' in dir() else None` — `dir()` inside a class body returns the class namespace, so `'threading'` is never there | The cross-instance lock was always `None` | `_lock = threading.Lock()` |

---

## 2. Packaging & metadata fixed

- **License inconsistency:** README showed an MIT badge, `scripts/setup.py` said `license="MIT"`, while `LICENSE` is GPL-3.0 and `pyproject.toml` said `GPL-3.0`. All now GPL-3.0 (wheel metadata reports `License-Expression: GPL-3.0` and bundles `LICENSE`).
- **Unused runtime dependencies removed** from `pyproject.toml`, `requirements.txt` and `scripts/setup.py`: `beautifulsoup4`, `cryptography`, `pycryptodome` (no import anywhere in the package). `playwright` — which the stream resolver *does* import — was missing from `scripts/setup.py`; added.
- **`scripts/build.py` (PyInstaller):** `numpy` was listed in `excludes` although `ui.py` needs it for poster rendering, so a frozen build would crash at the first episode list; removed. Stale `cryptography` hidden imports removed with the dependency.
- **`aur/PKGBUILD`:** `pkgver=1`, `source` pinned to `v1`, a literal unimplemented `sha256sums=('${SHA256}')` (makepkg refuses to build), `assets/icon.png` which does not exist, and a missing `python-playwright` runtime dependency. Fixed to 2.3.2, correct icon (`movie-watch.png`), `python-playwright` added, `python-cryptography` dropped, checksum set to `SKIP` with an `updpkgsums` note. `aur/.SRCINFO` regenerated to match.
- **`.gitignore`:** added `__pycache__/`, `*.py[cod]`, `build/`, `dist/`, `*.egg-info/`, `*.spec`, `.venv/`, `venv/`, `.pytest_cache/`, `downloads/`. Running the app or a build no longer leaves noise in `git status`.
- **Dead imports/variables removed:** `app.py` (`check_for_updates`, `get_version_status`, `download_file`, `monitor`), `cli.py` (`time`, `re`, `Panel`, `Align`), `player.py` (`time`), `updater.py` (`tempfile`, `time` + a redundant `if/else` that assigned the same command twice), `ui.py` (`details_cache`).

---

## 3. Enhancements

1. **`MOV_WATCH_API_BASE_URL` environment override** — the metadata host was a single hardcoded domain. It can now be pointed at a compatible mirror without editing source (`API_BASE_URL` is normalised, trailing slash stripped). Documented in the README.
2. **`Episode.display_num` property** — one definition of "how an episode number is displayed", used by the batch menu and no longer duplicated logic in the UI.
3. **Settings menu now only shows settings that do something.** `Analytics`, `Default Quality` and `Auto Next Episode` were written to `config.json` and read by nobody; `Analytics` additionally backed a README claim that anonymous usage data is collected. Removed the three rows and their defaults, leaving **Player / Discord Rich Presence / Theme**, and removed the data-collection notice from the README.
4. **README accuracy:** license badge fixed, subtitle feature described as what it is (embedded/sidecar subtitles, Arabic/English preferred) instead of "automatically fetches", keyboard table completed (**F** favourite, main-menu **S/L/F/C/A** keys that already existed in code), settings list corrected, environment-variable section added, "Anonymous usage statistics are collected" caution removed.

---

## 4. Verification performed

Run in the project root:

| Check | Command | Result |
|-------|---------|--------|
| Syntax/bytecode compile of package, entry point and scripts | `python3 -m compileall -q mov_watch main.py scripts` | passed (exit 0) |
| Import + behaviour smoke test with isolated `$HOME` (models/`display_num`, history incl. corrupt-entry path, favourites, settings defaults, all module imports) | inline `python3` script | passed — `defaults: ['discord_rpc', 'player', 'theme']` |
| CLI entry point | `python3 main.py --version` | `mov-watch v2.3.2` |
| Env override | `MOV_WATCH_API_BASE_URL=https://mirror.example/api/ ...` | `https://mirror.example/api` |
| Distribution build + metadata | `python3 -m pip wheel . --no-deps --no-build-isolation` | wheel built; `License-Expression: GPL-3.0`, `Requires-Python: >=3.8`, 7 runtime deps, `README`/`LICENSE` included |
| Leftover references to removed code (`batch_mode`, `ep_num_float`, …) | `grep -rn` | none |

**Not verified (cannot be verified headlessly here):** an interactive TUI session, live API search / episode listing, Playwright stream extraction and mpv/VLC/browser handoff, the PyInstaller build, and `makepkg`. Those need a terminal, network access to `api.xleo.nl`, Chromium and a player binary. The Discord RPC path was not exercised against a running Discord client.

---

## 5. Findings I did **not** change (recommendations)

1. **Hardcoded API secret** — `mov_watch/api.py` ships `API_SECRET_KEY = "mw_sk_..."` in source. It is public by construction; rotate it and move it to a per-install value or environment variable, or treat it as non-secret server-side.
2. **Subtitle support is effectively absent** — `_resolve_stream_with_playwright` never populates `StreamInfo.subtitle_urls` (vixsrc's player payload does not include them), and `--subs-lang` is plumbed from CLI → `get_stream_url()` where it is ignored. Only mpv's embedded/sidecar handling remains. Implementing a subtitle source, or dropping the flag, is a product decision.
3. **No-op modules and dead UI code left in place:** `mov_watch/monitoring.py` (stub, now imported nowhere), `ui.batch_selection_menu`, `ui.quality_selection_menu`, `ui.post_watch_menu`, `ui.selection_menu`, `utils.download_file`, and the never-used `load_more_callback` parameter of `media_selection_menu`. Safe to delete in a dedicated cleanup commit.
4. **Network errors look like empty results** — `api.search()` returns `[]` on timeout/HTTP failure, so the UI shows "No media matching '<query>' was found." Distinguishing transport errors would need a result type change through `ui.run_with_loading`.
5. **History/favourites resume by title string** — re-entry re-searches and falls back to the first result when the exact title changed, which can resume the wrong item. Storing the `tmdb_id` and re-resolving by ID would be robust.
6. **Discord RPC does blocking network I/O on the main thread** in the `update_*` state helpers (`_update_presence()` is called synchronously). If Discord's pipe stalls, menu transitions can hang. Queue updates to the existing background thread.
7. **No tests and no CI checks** — `.github/workflows/publish-pypi.yml` only publishes on release. A `compileall` + import smoke job on 3.8/3.11/3.12 would have caught findings #1 and #11 immediately.
8. **`scripts/MANIFEST.in` is inert** — `MANIFEST.in` is only read from the project root; the copy in `scripts/` (which also references non-existent `README.ar.md` and `themes.py`) is never used. sdist currently works because setuptools includes packages and README/LICENSE automatically.
9. **"Automatic Updates" only applies to frozen builds** — `main.py` calls `check_for_updates()` only when `is_bundled()`, and `updater.check_executable_update()` says standalone executables are no longer supported. pip/AUR users never see an update check; the README bullet overstates the feature.
10. **Auto-install path uses `sudo`** via `os.system("sudo apt install …")` in `deps.py`, and the Windows mpv URL is a pinned 32-bit (i686) snapshot from 2026-01-05 that will rot. Consider printing the command instead of running it with privileges, and preferably a distro-agnostic instruction.
11. **Stale AUR working copies** — `aur/mov-watch/` and `aur/mov-watch-git/` are separate git checkouts with their own PKGBUILDs; only the top-level `aur/PKGBUILD` and `aur/.SRCINFO` were updated here, so those clones still need the same edits (and a real checksum) before publishing.

---

## 6. Follow-up fix (after the first report)

Selecting a movie started an unexplained ~170 MB download at the bottom of the
terminal. That was Playwright's one-time Chromium fetch, triggered by
`api._ensure_playwright_browser()`, not a media download:

- It went to `~/.cache/ms-playwright`, a directory cache cleaners routinely
  delete, so the whole download would repeat after any cleanup.
- The install was run with `timeout=300`, so a slow connection aborted it
  halfway and left a Chromium that cannot start - which then looks like
  "Failed to extract stream link" on every play.
- The function returned `True` right after `playwright install` without
  verifying the browser actually launches.

Changed in `mov_watch/api.py`:

- Browsers now live in `~/.mov-watch/browsers`, set through
  `PLAYWRIGHT_BROWSERS_PATH` (the old code cleared that variable instead).
- An existing `~/.cache/ms-playwright/chromium-*` install is moved over on
  first use, so nobody pays for a second download.
- The 300 s cap is gone, the message states the size and destination, and the
  browser is launch-tested after installation; a failed install or launch now
  reports the `playwright install` / `install-deps` command to run.

Verified with a fake `$HOME`: migration moves `chromium-*` into
`~/.mov-watch/browsers`, leaves `.links` behind, and the env var is set
consistently. The download itself was not re-run.

---

## 7. Files changed

| File | Change |
|------|--------|
| `mov_watch/models.py` | `Episode.display_num` property |
| `mov_watch/api.py` | env-configurable base URL, payload validation, safe season/episode parsing, persistent Playwright browser path |
| `mov_watch/player.py` | browser fallback, mpv error reporting, VLC subtitles/referrer, 3.8-safe typing |
| `mov_watch/ui.py` | working episode jump, removed unimplemented M/T actions and dead option rows, dead locals |
| `mov_watch/app.py` | episode-index type guard, idempotent cleanup, dead imports removed |
| `mov_watch/cli.py` | correct history recording for episodes, dead imports removed |
| `mov_watch/history.py` | corrupt-entry tolerance |
| `mov_watch/settings.py` | removed no-op defaults |
| `mov_watch/deps.py` | 3.8-safe annotation, bare `except` narrowed |
| `mov_watch/utils.py` | fixed `RawTerminal` lock creation |
| `mov_watch/updater.py` | dead imports/branch removed |
| `pyproject.toml`, `requirements.txt`, `scripts/setup.py` | dependency trim, `playwright` added to setup.py, GPL-3.0 metadata |
| `scripts/build.py` | `numpy` un-excluded, stale hidden imports removed |
| `aur/PKGBUILD`, `aur/.SRCINFO` | version, deps, icon, checksum placeholder |
| `.gitignore` | build/venv/cache/media artefacts |
| `README.md` | license, features, shortcuts, settings, env vars, privacy notice |

---

## 8. AUR release automation

The stable AUR package (`mov-watch`) needed a hand-edited `pkgver`, a hand-computed
`sha256sums`, a tag and a release on every version. Three workflows now do it:

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `aur-publish.yml` | stable release `published`, or manual dispatch with a tag | bumps `pkgver`/`pkgrel` from the tag, computes the sha256 of the tag tarball, regenerates `.SRCINFO` with `makepkg` in an `archlinux:base-devel` container, commits and pushes `PKGBUILD` + `.SRCINFO` to `ssh://aur@aur.archlinux.org/mov-watch.git` |
| `cut-release.yml` | manual dispatch (`version`, `prerelease`) | bumps `mov_watch/version.py`, commits, tags, creates the GitHub release, then dispatches the PyPI and AUR jobs (release events created with `GITHUB_TOKEN` do not start workflows) |
| `beta-release.yml` | push to `main` touching `mov_watch/version.py`, or manual dispatch | publishes `v<version>-beta.<run_number>` as a pre-release; skipped when the commit is already tagged or contains `[skip beta]` |

Supporting changes:

- `aur/PKGBUILD` is now the single source of truth for the AUR package: CI only
  substitutes `pkgver`, `pkgrel` and `sha256sums`. `ffmpeg` was added to
  `depends` because `deps.ensure_dependencies()` treats it as required.
- `publish-pypi.yml` now skips pre-releases (`github.event.release.prerelease == false`).
  Before this, publishing a beta release would have failed the PyPI job, since
  `2.3.3-beta.1` is not a valid PyPI version.
- `aur/mov-watch-git/PKGBUILD`'s `pkgver()` uses
  `git describe --tags --exclude '*beta*'`, so the new beta tags cannot break
  the version string of the VCS package.
- `aur-publish.yml` refuses a tag containing `-` instead of writing an invalid
  `pkgver`, because a pacman `pkgver` may not contain a hyphen.

Required secret: `AUR_SSH_PRIVATE_KEY` (private half of an ed25519 key whose
public half is registered on the AUR account page).

Verified: all four workflow files parse as YAML; the `sed` rendering of the
PKGBUILD (version, reset `pkgrel`, real checksum), the version-regex validation,
the `__version__` extraction and the beta-tag format were simulated locally.
Not verified: an actual Actions run, the AUR push and the PyPI publish, which
need a push to GitHub and the repository secret.

---

## 9. Why stream extraction failed (`Failed to extract stream link`)

Not the network, not the API, not the missing browser: the vixsrc embed page
answers **HTTP 403 "Forbidden"** when it is requested without a `Referer`
header, so `jwplayer` never exists and the playlist lookup returns nothing.
The old code navigated with `page.goto(embed_url)` and no referer at all.

Measured against the same signed embed URL:

| Request | Status | `jwplayer` in body |
|---------|--------|--------------------|
| no Referer (any user agent) | 403 | no |
| `Referer: https://vixsrc.to/` | 200 | yes |

(The metadata API in `~/projects/mov-watch-api` is unrelated - it only proxies
search/TV data and contains no stream logic.)

Fixed in `_resolve_stream_with_playwright` (`mov_watch/api.py`):

- `page.goto(..., referer="https://vixsrc.to/")`.
- Waits for `window.jwplayer` with `wait_for_function` (15 s) instead of sleeping
  a guessed 8 s, and logs the page title when it never appears (a 403 page is
  now visible in `debug.log` as `jwplayer never loaded (page title: 'Forbidden')`).
- Reads sources from every playlist item, then the page's `<video>` element,
  and finally any `.m3u8`/`.mp4` request captured from the page.
- The browser is closed in a `finally`, so a failure cannot leak Chromium
  processes.

Verified end to end on this machine:

- `get_stream_url(The Matrix, tmdb 603)` -> playlist URL; fetching it with the
  stream referer returns `200` and a body starting with `#EXTM3U`.
- `get_stream_url(Breaking Bad S01E01, tmdb 1396)` -> playlist URL as well.
- `mpv --vo=null --ao=null --frames=30` on the resolved URL with the app's
  headers: exit code 0, no warnings - it really decodes.
