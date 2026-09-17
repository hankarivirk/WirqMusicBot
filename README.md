# 🎵 Wirq Music Bot

<p align="center">
  <img src="https://telegra.ph/file/0c32988168bbd4e78f99e.jpg" alt="WirqMusic Banner" width="750" style="border-radius: 12px;" />
</p>

<p align="center">
  <b>A modern, ultra-resilient Telegram voice-chat music streaming bot powered by Pyrogram, pytgcalls, and yt-dlp.</b>
</p>

<p align="center">
  <a href="https://t.me/wirq4"><img src="https://img.shields.io/badge/Owner-%40wirq4-blue.svg?style=flat-square" /></a>
  <a href="https://t.me/wirqbots"><img src="https://img.shields.io/badge/Channel-%40wirqbots-orange.svg?style=flat-square" /></a>
  <a href="https://github.com/Hankarivirk/WirqMusicbot"><img src="https://img.shields.io/badge/GitHub-Hankarivirk%2FWirqMusicbot-green.svg?style=flat-square" /></a>
  <img src="https://img.shields.io/badge/License-MIT-purple.svg?style=flat-square" />
</p>

---

## ✨ Flagship Features

- 🎧 **Audio & Video Streaming:** High-fidelity Opus lossless audio (`/play`) and HD 720p video streaming (`/vplay`).
- 🎨 **Apple Music-Inspired Player Card:** Custom visual now-playing card with real album art, ambient blurred backdrop, codec/bitrate badges, dynamic progress tracking, and channel branding.
- 🔁 **3-State Loop System:** Cycle seamlessly between **Loop OFF**, **Loop Current Song**, and **Loop Entire Queue**.
- ⚡ **Smart Autoplay & Recommendations:**
  - **Autoplay ON:** Automatically detects track ending and queues real YouTube related songs.
  - **Autoplay OFF:** Displays 3 genuine YouTube recommendations with a **🔄 More** button for fresh picks.
- 🔎 **Interactive Search:** `/search <query>` displays interactive buttons to stream or queue tracks on tap without copying links.
- 📋 **Independent Per-Group Queues:** Isolated queue management with Replay, Pause, Resume, Skip, Stop, Clear, Volume, Seek, and Shuffle.
- 🌐 **Proper Localization (EN / HI / PA):** Complete multi-language support for English, Hindi, and Punjabi with automatic English fallback.
- 🛡️ **Role-Based Admin Protection:** All sensitive controls are validated against Telegram's active group administrator list.
- 💾 **Hybrid Persistence Engine:** High-performance MongoDB storage with automatic local JSON/memory fallback.
- 🧹 **Background Auto-Cleanup Daemon:** Automatically reclaims storage, purges expired caches, and terminates orphaned FFmpeg processes.

---

## 📋 Available Commands

### 🎵 Playback Controls
| Command | Description |
| :--- | :--- |
| `/play <query/link>` | Streams audio in the group's voice chat. Accepts song names, YouTube links, playlists, and mixes. |
| `/vplay <query/link>` | Streams video + audio in HD 720p. |
| `/search <query>` | Searches YouTube and provides interactive inline buttons to play tracks. |
| `/pause` | Pauses active voice chat streaming. |
| `/resume` | Resumes paused stream. |
| `/skip` | Skips to the next track in the queue. |
| `/stop` | Stops playback and clears the voice chat session. |
| `/clear` | Clears upcoming queue tracks while keeping current playback active. |
| `/queue` | Displays the current playlist queue and upcoming tracks. |
| `/replay` | Replays the current track from the beginning. |
| `/seek <seconds>` | Jumps playback to the specified timestamp. |
| `/shuffle` | Randomizes the order of queued tracks. |
| `/leave` | Forces the assistant client to leave the voice chat. |

### ⚙️ Settings & Configuration
| Command | Description |
| :--- | :--- |
| `/loop [off\|song\|queue]` | Cycles or sets the 3-state loop mode. |
| `/autoplay [on\|off]` | Toggles continuous intelligent related song streaming. |
| `/volume <1-100>` | Adjusts the voice chat playback volume. |
| `/thumbnail [on\|off]` | Toggles custom Apple Music player cards for the group. |
| `/setthumbnail [on\|off]` | *(Owner-only)* Configures global default player card status. |
| `/lang` or `/language` | Opens the interactive language selector (English, Hindi, Punjabi). |
| `/ping` | Measures round-trip latency, voice-chat stream latency, uptime, and player status. |
| `/stats` | Shows system analytics and usage metrics (with detailed owner audit). |

---

## 🚀 Deployment Guide

### 1. Requirements
- Python 3.10 or 3.11
- FFmpeg installed and accessible in system PATH
- Telegram `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org)
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- Pyrogram Assistant String Session (`SESSION`)
- MongoDB connection string (optional, has local fallback)

---

### 🐧 Deploy on Linux VPS (Ubuntu / Debian)

```bash
# 1. Update system & install FFmpeg, Python, and Git
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip ffmpeg git

# 2. Clone the repository
git clone https://github.com/Hankarivirk/WirqMusicbot.git
cd WirqMusicbot

# 3. Create virtual environment & install requirements
python3 -m venv venv
source venv/bin/activate
pip install -U -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
nano .env   # Fill in API_ID, API_HASH, BOT_TOKEN, OWNER_ID, SESSION

# 5. Start the bot
python3 -m wirq
```

To run continuously in the background using `systemd`:
```bash
sudo nano /etc/systemd/system/wirqmusic.service
```
Paste the following:
```ini
[Unit]
Description=Wirq Music Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/WirqMusicbot
ExecStart=/root/WirqMusicbot/venv/bin/python3 -m wirq
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable wirqmusic
sudo systemctl start wirqmusic
```

---

### 🐳 Deploy with Docker & Docker Compose

```bash
# 1. Clone repository
git clone https://github.com/Hankarivirk/WirqMusicbot.git
cd WirqMusicbot

# 2. Setup environment file
cp .env.example .env
nano .env

# 3. Build and launch container
docker compose up -d --build

# View logs
docker compose logs -f
```

---

### 📱 Deploy on Android (Termux)

```bash
# 1. Update Termux packages
pkg update && pkg upgrade -y

# 2. Install Python, FFmpeg, Git, and build tools
pkg install -y python ffmpeg git clang libffi openssl

# 3. Clone repository
git clone https://github.com/Hankarivirk/WirqMusicbot.git
cd WirqMusicbot

# 4. Install dependencies
pip install -U pip setuptools wheel
pip install -r requirements.txt

# 5. Configure .env
cp .env.example .env
nano .env

# 6. Run the bot
python3 -m wirq
```

---

## 🛡️ Security & Privacy
- **Zero Token Leakage:** All secrets, sessions, and database URLs live strictly in `.env`.
- **Session Protection:** Pyrogram session files and strings are strictly excluded in `.gitignore`.
- **Safe YouTube Extraction:** Supports optional authentication cookies via `COOKIES_URL` without committing or logging cookie contents.

---

## 👨‍💻 Community & Credits
- **Bot Name:** Wirq Music Bot
- **Developer / Owner:** [@wirq4](https://t.me/wirq4)
- **Support Channel:** [@wirqbots](https://t.me/wirqbots)
- **Source Repository:** [Hankarivirk/WirqMusicbot](https://github.com/Hankarivirk/WirqMusicbot)
