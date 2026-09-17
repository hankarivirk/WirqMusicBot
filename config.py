# Wirq Music Bot - Production Configuration
# Bot Name: Wirq Music Bot
# Owner: @wirq4 | Support: @wirqbots | GitHub: Hankarivirk/WirqMusicbot

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_BASE_DIR = Path(__file__).resolve().parent


def _int_env(name: str, default: int = 0) -> int:
    """Read an integer environment variable, treating blank values as default."""
    value = os.getenv(name, "")
    if not value or not value.strip():
        return default
    try:
        return int(value.strip())
    except ValueError:
        raise ValueError(f"{name} must be a valid integer, got: {value!r}")


class Config:
    def __init__(self):
        # Core Telegram API credentials
        self.API_ID = _int_env("API_ID")
        self.API_HASH = os.getenv("API_HASH", "")
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "")
        self.OWNER_ID = _int_env("OWNER_ID")
        # LOGGER_ID is optional. Blank/invalid logger configuration must not
        # prevent the bot from starting.
        self.LOGGER_ID = _int_env("LOGGER_ID")

        # Database
        self.MONGO_URL = os.getenv("MONGO_URL", "")

        # Telegram Userbot assistant sessions
        self.SESSION1 = os.getenv("SESSION", None) or os.getenv("STRING_SESSION", None)
        self.SESSION2 = os.getenv("SESSION2", None)
        self.SESSION3 = os.getenv("SESSION3", None)

        # Limits
        self.DURATION_LIMIT = _int_env("DURATION_LIMIT", 60) * 60
        self.MAX_FILE_SIZE = _int_env("MAX_FILE_SIZE", 2000) * 1024 * 1024
        self.QUEUE_LIMIT = _int_env("QUEUE_LIMIT", 50)
        self.PLAYLIST_LIMIT = _int_env("PLAYLIST_LIMIT", 200)

        # Identity & Community Links
        self.BOT_NAME = "Wirq Music Bot"
        self.OWNER_USERNAME = "@wirq4"
        self.OWNER_URL = os.getenv("OWNER_URL", "https://t.me/wirq4")
        self.SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "https://t.me/wirqbots")
        self.SUPPORT_CHAT = os.getenv("SUPPORT_CHAT", "https://t.me/wirqbots")
        self.GITHUB_REPO = os.getenv("GITHUB_REPO", "https://github.com/Hankarivirk/WirqMusicbot")

        # Automation & Auto Cleanup
        self.AUTO_LEAVE = os.getenv("AUTO_LEAVE", "True").lower() == "true"
        self.AUTO_LEAVE_GRACE = _int_env("AUTO_LEAVE_GRACE", 15)
        self.AUTO_LEAVE_EXCLUDE = [
            int(cid) for cid in os.getenv("AUTO_LEAVE_EXCLUDE", "").split(",") if cid.strip()
        ]
        self.CLEANUP_INTERVAL = _int_env("CLEANUP_INTERVAL", 1800)
        self.CLEANUP_MAX_AGE = _int_env("CLEANUP_MAX_AGE", 7200)

        # Feature flags
        self.AUTO_END = os.getenv("AUTO_END", "True").lower() == "true"
        self.THUMB_GEN = os.getenv("THUMB_GEN", "True").lower() == "true"
        self.VIDEO_PLAY = os.getenv("VIDEO_PLAY", "True").lower() == "true"
        self.LANG_CODE = os.getenv("LANG_CODE", "en")

        # Thumbnail configuration
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
