<div align="center">

## 📑 Navigation

[Installation](#-installation) • [Features](#-what-can-you-do) • [How to Use](#-how-to-use) • [Keyboard Shortcuts](#️-keyboard-shortcuts) • [Configuration](#%EF%B8%8F-configuration) • [Credits](#-credits) • [License](#-license)

---

Terminal-based movie and TV show streaming with Arabic/English subtitles

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
  <a href="https://pypi.org/project/mov-watch/">
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

- **Python 3.8+**
- **MPV** (media player)
- **ffmpeg**

### Method 1: pip

```bash
pip install mov-watch
playwright install chromium    # one-time browser download for stream extraction
```

Launch:

```bash
mov-watch
# or
mw
```

### Method 2: Arch Linux (AUR)

Stable release:
```bash
yay -S mov-watch
```

Git version (always latest commit):
```bash
yay -S mov-watch-git
```

### Method 3: From Source

```bash
git clone https://github.com/leoallday/mov-watch.git
cd mov-watch
pip install -r requirements.txt
playwright install chromium
python main.py
```

---

## 🎯 What Can You Do?

### Streaming & Playback

- **Subtitle Support**: Automatically fetches Arabic and English subtitles
- **Resume from History**: Pick up where you left off

### Personal Library

- **Favorites System**: Bookmark movies and TV shows
- **Episode Tracking**: Remembers your progress

### Interface & Experience

- **Rich TUI**: Beautiful terminal interface built with Rich library
- **Color Themes**: Choose from various color schemes
- **Discord Rich Presence**: Show what you're watching on Discord
- **Smooth Navigation**: Intuitive keyboard controls

### Technical Features

- **Zero Ads**: Clean streaming experience
- **Automatic Updates**: Built-in version checker
- **MPV/VLC Support**: Choose your preferred player
- **Cross-platform**: Works on Linux, macOS, and Windows

---

## 🎮 How to Use

1.  **Launch**: Run `mov-watch` or `mw`
2.  **Search**: Type a movie or show name
3.  **Select**: Pick from search results
4.  **Watch**: MPV launches and starts streaming

Quick mode:
```bash
mw -i "The Matrix"
```

---

## ⌨️ Keyboard Shortcuts

| Key         | What it Does                       |
| ----------- | ---------------------------------- |
| **↑ / ↓**   | Navigate through lists             |
| **Enter**   | Select/Confirm choice              |
| **G**       | Jump to an episode number          |
| **B**       | Go back                            |
| **Q / Esc** | Quit                               |

---

## ⚙️ Configuration

Settings stored in `~/.mov-watch/database/config.json`.

Access the settings menu from the main screen to customize:
- **Player**: MPV or VLC
- **Auto-next Episode**: Toggle automatic continuation
- **Discord Rich Presence**: Toggle Discord integration
- **Theme**: Pick from various color schemes
- **Analytics**: Opt-in/out of anonymous usage stats

---

## 🙏 Credits

Created and maintained by **leoallday**
- GitHub: [leoallday/mov-watch](https://github.com/leoallday/mov-watch)

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0**.
See the [LICENSE](LICENSE) file for the full legal text.

---

<div align="center">

### ⚠️ Important Notice

</div>

> [!CAUTION]
> **By using this software you understand:**
>
> - Anonymous usage statistics are collected (can be disabled in settings)
> - The project is licensed under GNU General Public License v3.0
> - We do not host any content; all streams are from third-party sources

---

<br>

Made with ❤️ by leoallday

[⭐ Star this repo](https://github.com/leoallday/mov-watch) | [🐛 Report bugs](https://github.com/leoallday/mov-watch/issues) | [💬 Discussions](https://github.com/leoallday/mov-watch/discussions)

</div>
