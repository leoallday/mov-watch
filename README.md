<div align="center">

## 📑 Navigation

[Installation](#-installation) • [Features](#-what-can-you-do) • [How to Use](#-how-to-use) • [Keyboard Shortcuts](#️-keyboard-shortcuts) • [Configuration](#%EF%B8%8F-configuration) • [Credits](#-credits) • [License](#-license)

---

Terminal-based movie and TV show streaming with Arabic subtitles

<p align="center">
  <a href="https://github.com/leoallday/mov-watch/stargazers">
    <img src="https://img.shields.io/github/stars/leoallday/mov-watch?style=for-the-badge" />
  </a>
  <a href="https://github.com/leoallday/mov-watch/network">
    <img src="https://img.shields.io/github/forks/leoallday/mov-watch?style=for-the-badge" />
  </a>
  <br>
  <a href="https://github.com/leoallday/mov-watch/releases">
    <img src="https://img.shields.io/github/v/release/leoallday/mov-watch?style=for-the-badge" />
  </a>
  <a href="https://pypi.org/project/mov-watch">
    <img src="https://img.shields.io/pypi/v/mov-watch?style=for-the-badge" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" />
</p>

<br>
<br>

</div>

---

## 📦 Installation

### Requirements

Before installing, make sure you have:

- **Python 3.8 or newer** (Python 3.12 recommended)
- **MPV media player** (for streaming)
- **ffmpeg** (for video processing)
- **fzf** (for fuzzing results, optional)
- **yt-dlp** (for video processing)
- **aria2** (for video downloading)
- **beautfullsoup** (for web scraping)

> **⚠️ Important Note:** If you are using macOS, build from source.

### Method 1: Install via pip (Recommended)

The easiest way to get started:

```bash
pip install mov-watch
```

Launch the app:

```bash
mov-watch
# or use the shorter command
mw
```

To update to the latest version:

```bash
pip install --upgrade mov-watch
```

### Method 2: Arch Linux (AUR)

```bash
yay -S mov-watch
```

### Method 3: From Source

Want to run the development version?

**On Windows:**

```powershell
# Install MPV first (if not already installed or bundled by mov-watch)
# scoop install mpv

# Clone the repo and install dependencies
git clone https://github.com/leoallday/mov-watch.git
cd mov-watch
pip install -r requirements.txt
python main.py
```

**On Linux (Debian/Ubuntu):**

```bash
# Get the dependencies (mov-watch will attempt to auto-install these)
# sudo apt update && sudo apt install mpv git python3-pip ffmpeg fzf

# Clone and run
git clone https://github.com/leoallday/mov-watch.git
cd mov-watch
pip install -r requirements.txt
python3 main.py
```

**On macOS:**

```bash
# Get the dependencies (mov-watch will guide you to install these via Homebrew)
# brew install mpv ffmpeg fzf

# Clone and run
git clone https://github.com/leoallday/mov-watch.git
cd mov-watch
pip install -r requirements.txt
python3 main.py
```

---

## 🎯 What Can You Do?

Here's everything this tool offers:

### Streaming & Playback

- **Multiple Quality Options**: Watch in 1080p, 720p, or 480p depending on your internet speed
- **Subtitle Support**: Automatically fetches and prioritizes Arabic and English subtitles, making both available for selection in your media player.
- **Resume from History**: Pick up exactly where you left off (buggy - acknowledged)

### Personal Library

- **Favorites System**: Bookmark your favorite movies and TV shows for quick access
- **Episode Tracking**: The app remembers which episode you're on

### Interface & Experience

- **Rich TUI (Terminal User Interface)**: Beautiful terminal interface built with Rich library
- **Color Themes**: Choose from various color themes.
- **Discord Rich Presence**: Show off what you're watching on Discord with media posters

- **Smooth Navigation**: Intuitive keyboard controls

### Technical Features

- **Zero Ads**: Clean streaming experience
- **Automatic Updates**: Built-in version checker notifies you of new releases, and yes this can be turned off.
- **MPV/VLC Support**: Choose your preferred media player
- **Dependency Auto-installer**: Automatically checks and installs missing dependencies.
- **Cross-platform**: Works on Windows, Linux, and macOS

---

## 🎮 How to Use

1.  **Launch the app**: Run `mov-watch` or `mw`
2.  **Browse or Search**: Use the main menu to search, view trending, or browse genres
3.  **Select Media**: Navigate with arrow keys and press Enter
4.  **Pick an Episode/Movie**: Choose which episode or movie to watch
5.  **Enjoy**: MPV/VLC will launch and start streaming

You can also use interactive mode for quick searches:

```bash
mw -i "The Matrix"
```

---

## ⌨️ Keyboard Shortcuts

| Key         | What it Does                       |
| ----------- | ---------------------------------- |
| **↑ / ↓**   | Navigate through lists             |
| **Enter**   | Select/Confirm choice              |
| **G**       | Jump directly to an episode number |
| **B**       | Go back to previous screen         |
| **Q / Esc** | Quit the application               |
| **Space**   | Pause/Resume video (in player)     |
| **← / →**   | Rewind/Forward 5 seconds           |
| **F**       | Toggle fullscreen                  |

---

## ⚙️ Configuration

Settings are stored locally in `~/.mov-watch/database/config.json`

### Available Settings

Access the settings menu from the main screen to customize:

- **Default Quality**: Set your preferred quality (1080p, 720p, or 480p)
- **Player**: Choose between MPV or VLC
- **Auto-next Episode**: Toggle automatic episode continuation
- **Discord Rich Presence**: Show or hide Discord activity
- **Theme Color**: Pick from various color schemes.
- **Analytics**: Opt-in/out of anonymous usage stats - this is auto enabled by default.
- **Update Checking**: Toggle automatic update notifications

You can also manually edit the config file if you prefer.

---

## 🙏 Credits

`mov-watch` is created and maintained by:

- **leoallday**
  - GitHub: [https://github.com/leoallday/mov-watch](https://github.com/leoallday/mov-watch)

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0**.

You're free to use, modify, and distribute this software under the terms of the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for the full legal text.

**In simple terms:**

- ✅ Use it for personal or commercial purposes
- ✅ Modify the source code
- ✅ Distribute it to others
- ✅ Sub-license it
- ⚠️ Provide attribution
- ⚠️ Include the original copyright notice and license text

---

<div align="center">

### ⚠️ Important Notice

</div>

> [! CAUTION]
> **By using this software you understand:**
>
> - Anonymous usage statistics are collected for the GitHub page stats banner (can be disabled in settings) - (Note: mov-watch analytics are explicitly mentioned as opt-in/out, but the banner part is from ani-cli-arabic, needs clarification if mov-watch uses it.)
> - The project is licensed under GNU General Public License v3.0 - see [LICENSE](LICENSE) for details
> - We do not host any content; all streams are from third-party sources
> - This tool is for personal use and educational purposes only

---

<br>

Made with ❤️ by leoallday

[⭐ Star this repo](https://github.com/leoallday/mov-watch) | [🐛 Report bugs](https://github.com/leoallday/mov-watch/issues) | [💬 Discussions](https://github.com/leoallday/mov-watch/discussions)

</div>
