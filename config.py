# Wirq Music Bot - Production Configuration
# Bot Name: Wirq Music Bot
# Owner: @wirq4 | Support: @wirqbots | GitHub: Hankarivirk/WirqMusicbot

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_BASE_DIR = Path(__file__).resolve().parent

class Config:
    def __init__(self):
        # Core Telegram API credentials
        self.API_ID = int(os.getenv("API_ID", 0))
        self.API_HASH = os.getenv("API_HASH", "")
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "")
        self.OWNER_ID = int(os.getenv("OWNER_ID", 0))
        self.LOGGER_ID = int(os.getenv("LOGGER_ID", 0))

        # Database
        self.MONGO_URL = os.getenv("MONGO_URL", "")

        # Telegram Userbot assistant sessions
        self.SESSION1 = os.getenv("SESSION", None) or os.getenv("STRING_SESSION", None)
        self.SESSION2 = os.getenv("SESSION2", None)
        self.SESSION3 = os.getenv("SESSION3", None)

        # Limits
        self.DURATION_LIMIT = int(os.getenv("DURATION_LIMIT", 60)) * 60
        self.MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 2000)) * 1024 * 1024
        self.QUEUE_LIMIT = int(os.getenv("QUEUE_LIMIT", 50))
        self.PLAYLIST_LIMIT = int(os.getenv("PLAYLIST_LIMIT", 200))

        # Identity & Community Links
        self.BOT_NAME = "Wirq Music Bot"
        self.OWNER_USERNAME = "@wirq4"
        self.OWNER_URL = os.getenv("OWNER_URL", "https://t.me/wirq4")
        self.SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "https://t.me/wirqbots")
        self.SUPPORT_CHAT = os.getenv("SUPPORT_CHAT", "https://t.me/wirqbots")
        self.GITHUB_REPO = os.getenv("GITHUB_REPO", "https://github.com/Hankarivirk/WirqMusicbot")

        # Automation & Auto Cleanup
        self.AUTO_LEAVE = os.getenv("AUTO_LEAVE", "True").lower() == "true"
        self.AUTO_LEAVE_GRACE = int(os.getenv("AUTO_LEAVE_GRACE", 15))
        self.AUTO_LEAVE_EXCLUDE = [
            int(cid) for cid in os.getenv("AUTO_LEAVE_EXCLUDE", "").split(",") if cid.strip()
        ]
        self.CLEANUP_INTERVAL = int(os.getenv("CLEANUP_INTERVAL", 1800))  # 30 mins
        self.CLEANUP_MAX_AGE = int(os.getenv("CLEANUP_MAX_AGE", 7200))    # 2 hours

        # Feature flags
        self.AUTO_END = os.getenv("AUTO_END", "True").lower() == "true"
        self.THUMB_GEN = os.getenv("THUMB_GEN", "True").lower() == "true"
        self.VIDEO_PLAY = os.getenv("VIDEO_PLAY", "True").lower() == "true"
        self.LANG_CODE = os.getenv("LANG_CODE", "en")

        # Thumbnail configuration (Section 6)
        self.START_THUMBNAIL_URL = os.getenv(
            "START_THUMBNAIL_URL",
            "https://telegra.ph/file/0c32988168bbd4e78f99e.jpg"
        )
        self.PING_THUMBNAIL_URL = os.getenv(
            "PING_THUMBNAIL_URL",
            "https://telegra.ph/file/0c32988168bbd4e78f99e.jpg"
        )
        self.SONG_THUMBNAIL_DEFAULT = os.getenv(
            "SONG_THUMBNAIL_DEFAULT",
            "https://telegra.ph/file/0c32988168bbd4e78f99e.jpg"
        )
        # Compatibility aliases
        self.DEFAULT_THUMB = self.SONG_THUMBNAIL_DEFAULT
        self.START_IMG = self.START_THUMBNAIL_URL
        self.PING_IMG = self.PING_THUMBNAIL_URL

        # Cookies for YouTube authentication (optional)
        self.COOKIES_URL = [
            url.strip() for url in os.getenv("COOKIES_URL", "").split() if url.strip()
        ]

        self.BRAND_NAME = "Wirq Music Bot"
        self.BRAND_TAG = "@wirqbots"

    def check(self):
        missing = [
            var for var in ["API_ID", "API_HASH", "BOT_TOKEN", "OWNER_ID", "SESSION1"]
            if not getattr(self, var)
        ]
        if missing:
            raise SystemExit(
                f"Missing required environment variables in .env: {', '.join(missing)}"
            )

config = Config()
