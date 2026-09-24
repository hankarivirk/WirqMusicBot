# MUSIC FLOW

A clean Telegram music player built for fast search, quick streaming, and simple queue control.

## Features

- **Fast Search**: Asynchronous YouTube search migration powered by `yt-search-python` 2.2.1.
- **Minimalist Aesthetic**: Clean, dark Telegram-native UI with zero emoji spam and locked player controls (`▷`, `II`, `⥁`, `‣‣I`, `▢`).
- **Autoplay & Recommendations**: Automatic continuation when queue ends, or dynamic 3-button recommendations + MORE.
- **Controlled Thumbnail System**: URL-based YouTube thumbnails, default OFF globally and per-group, with owner override control.
- **Telegraph Integration**: Seamless web queue & playlist viewing for long tracklists.
- **Reliable Voice Engine**: Low-latency voice streaming via PyTgCalls.

## Deployment

### Prerequisites
1. Python 3.10+
2. FFmpeg installed on host
3. MongoDB instance

### Installation
```bash
git clone <repository_url>
cd music-flow
pip install -r requirements.txt
cp sample.env .env
# Fill in your variables in .env
bash start
```

### Environment Variables
- `API_ID`: Your Telegram API ID.
- `API_HASH`: Your Telegram API Hash.
- `BOT_TOKEN`: Your Telegram Bot Token from @BotFather.
- `OWNER_ID`: Telegram user ID of the owner.
- `LOGGER_ID`: Telegram chat ID for log events.
- `MONGO_URL`: MongoDB connection string.
- `SESSION`: Pyrogram String Session for the assistant.
- `OWNER_URL`: (Optional) Contact URL for the Owner button.
- `START_IMG_URL`: (Optional) Image URL for `/start`.
- `DEFAULT_THUMB_URL`: (Optional) Fallback image URL.
- `PING_IMG_URL`: (Optional) Image URL for `/ping`.

### Railway Deployment
1. Connect your GitHub repository to Railway.
2. Railway will automatically detect `railway.json` and `Dockerfile`.
3. Configure the required environment variables in your Railway project settings:
   - `API_ID`
   - `API_HASH`
   - `BOT_TOKEN`
   - `OWNER_ID`
   - `LOGGER_ID`
   - `MONGO_URL`
   - `SESSION`
4. Deploy the worker service.
