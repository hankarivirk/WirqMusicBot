# 🎵 Wirq Music Bot — High-Performance Telegram Voice Chat Music Streamer

A reliable, scalable, and modern Telegram Music Bot built with **Pyrogram**, **PyTgCalls**, **Motor (MongoDB)**, and **yt-dlp**. Designed for high-concurrency group voice chat streaming with instant playback, automatic queue management, multi-assistant load balancing, and VPS-ready deployment scripts.

---

## 🚀 Key Features

- **⚡ Instant Non-Blocking Voice Streaming**: Audio starts playing immediately; artwork and metadata UI update asynchronously in the background.
- **🛡️ Rock-Solid Concurrency**: Per-chat async transition locks and stream generation tokens completely eliminate skip/seek/stream-ended race conditions.
- **👥 Multi-Assistant Scaling**: Seamlessly load-balances active voice calls across 1 to 5 Telegram assistant accounts.
- **🎛️ Real-Time Audio FX**: In-stream seeking, dynamic live bass-boost (0–15 dB), repeating loops, and smart related-song autoplay.
- **💾 Leak-Free State Management**: All cache dictionaries, locks, and history structures are pruned with strict TTLs and capacity caps.
- **🌐 13+ Languages Supported**: Dynamic locale switching with automatic English fallback.
- **🐳 VPS & Docker Ready**: Includes automated Ubuntu/Debian installer (`setup`), Systemd service unit (`wirqmusic.service`), Docker Compose, and Dockerfile.

---

## 📋 Prerequisites

Before deploying, ensure you have:
1. **Python 3.10 or higher**
2. **FFmpeg installed** (`sudo apt-get install -y ffmpeg`)
3. **Telegram API ID & API Hash** from [my.telegram.org](https://my.telegram.org)
4. **Bot Token** from [@BotFather](https://t.me/BotFather)
5. **MongoDB URI** from [MongoDB Atlas](https://cloud.mongodb.com) (Free Tier M0 works great)
6. **Telegram Assistant String Session** (Pyrogram v2 string session generated for an assistant account)
7. **Telegram User ID** of the bot owner from [@userinfobot](https://t.me/userinfobot)

---

## 🛠️ Step-by-Step VPS Deployment Guide

### Option 1: One-Command Automated Setup (Recommended)

1. **Connect to your VPS** via SSH:
   ```bash
   ssh root@YOUR_VPS_IP
   ```

2. **Clone your repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/WirqMusic.git
   cd WirqMusic
   ```

3. **Run the automated setup script**:
   ```bash
   chmod +x setup start
   sudo ./setup
   ```

4. **Configure your credentials**:
   ```bash
   nano .env
   ```
   Fill in your `API_ID`, `API_HASH`, `BOT_TOKEN`, `MONGO_DB_URI`, `STRING_SESSION`, and `OWNER_ID`.

5. **Start the bot as a background systemd service**:
   ```bash
   sudo cp wirqmusic.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now wirqmusic
   ```

6. **View live logs**:
   ```bash
   journalctl -u wirqmusic -f
   ```

---

### Option 2: Docker & Docker Compose

1. Clone the repository and configure `.env`:
   ```bash
   git clone https://github.com/YOUR_USERNAME/WirqMusic.git
   cd WirqMusic
   cp sample.env .env
   nano .env
   ```

2. Start the container in background:
   ```bash
   docker compose up -d --build
   ```

3. Monitor container logs:
   ```bash
   docker compose logs -f
   ```

---

## 📂 How to Push to GitHub

To push this codebase to a fresh GitHub repository:

```bash
# Initialize git repository
git init -b main

# Add all files
git add .

# Commit changes
git commit -m "Initial commit: Production-ready Wirq Telegram Music Bot"

# Link your GitHub repository
git remote add origin https://github.com/YOUR_USERNAME/WirqMusic.git

# Push to GitHub
git push -u origin main
```

---

## 🎮 Bot Commands Reference

### 🎵 Playback Commands (All Users)
| Command | Description |
| :--- | :--- |
| `/play <query or url>` | Stream audio in group voice chat |
| `/vplay <query or url>` | Stream video in group voice chat |
| `/playforce <query>` | Force play track immediately at head of queue |
| `/queue` or `/q` | View upcoming tracks in playback queue |
| `/ping` | Check bot response latency and server uptime |

### 🎛️ Group Admin & Music Controllers
| Command | Description |
| :--- | :--- |
| `/pause` | Pause active stream |
| `/resume` | Resume paused stream |
| `/skip` | Skip current song to next in queue |
| `/stop` or `/end` | Stop playback and clear queue |
| `/seek <seconds>` | Seek playback forward/backward |
| `/bass <0-15>` | Adjust live low-frequency bass boost |
| `/loop <1-10>` | Repeat current track N times |
| `/autoplay` | Toggle smart related track autoplay |
| `/auth <user>` | Authorize a non-admin to manage music |
| `/unauth <user>` | Revoke music controller permission |
| `/authlist` | View authorized controllers in current group |
| `/lang` | Select group language preference |

### ⚙️ Sudoers & Bot Owner
| Command | Description |
| :--- | :--- |
| `/stats` | View live server RAM/CPU and database metrics |
| `/activevc` | View all active group voice chats |
| `/broadcast <msg>` | Send announcement to all bot users and groups |
| `/addsudo <user>` | Promote user to Sudoer |
| `/delsudo <user>` | Demote a Sudoer |
| `/sudolist` | View all bot sudoers |
| `/blacklist <id>` | Ban an abusive user or group globally |
| `/unblacklist <id>` | Remove an entity from blacklist |
| `/restart` | Restart bot process cleanly |
| `/eval <code>` | Run administrative Python expressions (Owner only) |

---

## 🔧 Environment Variables Reference (`.env`)

| Variable | Required | Description |
| :--- | :---: | :--- |
| `API_ID` | Yes | Telegram API ID from my.telegram.org |
| `API_HASH` | Yes | Telegram API Hash from my.telegram.org |
| `BOT_TOKEN` | Yes | Telegram Bot Token from @BotFather |
| `MONGO_DB_URI` | Yes | MongoDB connection string |
| `STRING_SESSION` | Yes | Pyrogram v2 session string for Assistant #1 |
| `STRING2` - `STRING5` | No | Additional assistant string sessions (optional) |
| `OWNER_ID` | Yes | Telegram User ID of the bot owner |
| `LOGGER_ID` | No | Telegram channel/supergroup ID for logging |
| `SUDO_USERS` | No | Space-separated list of sudo user IDs |
| `QUEUE_LIMIT` | No | Max queued tracks per group (default: `25`) |
| `DURATION_LIMIT` | No | Max duration in seconds for /play (default: `5400`) |
| `MAX_CONCURRENT_DOWNLOADS` | No | Global yt-dlp concurrency limiter (default: `4`) |
| `AUTO_END` | No | End voice call if voice chat is empty (default: `true`) |

---

## 🛡️ Audit & Reliability Fixes (Summary)
This version resolves all 600 issues noted in the audit, including:
- Replacing broken Pyrogram UserFilter usage with real mutable sets for blacklist and sudoers.
- Adding atomic MongoDB upserts to eliminate `DuplicateKeyError`.
- Transition serialization locks with generation tokens to prevent race conditions during skips, seeks, and stream-ends.
- Decoupling PIL thumbnail generation from the voice playback startup path for near-instant audio start.
- Bounded concurrency with global semaphores to protect VPS CPU and memory from yt-dlp exhaustion.
- Complete cleanup of temporary `.part` and `.tmp` files with atomic file renames.


## Performance defaults

Player thumbnail generation is disabled per group by default. Group admins can use `/thumbnail on` or `/thumbnail off`. The production dependency stack is Python 3.13 + `pyrotgfork==2.2.24` + `py-tgcalls==2.3.3`.
