from os import getenv
from pathlib import Path
from dotenv import load_dotenv

_BASE_DIR = Path(__file__).resolve().parent
load_dotenv(_BASE_DIR / ".env")


def _bool(name: str, default: bool = False) -> bool:
    return getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on", "t"}


def _int(name: str, default: int = 0) -> int:
    try:
        return int(getenv(name, str(default)).strip())
    except (TypeError, ValueError):
        return default


class Config:
    def __init__(self):
        self.API_ID = _int("API_ID", 0)
        self.API_HASH = getenv("API_HASH", "").strip()
        self.BOT_TOKEN = getenv("BOT_TOKEN", "").strip()
        self.MONGO_URL = getenv("MONGO_URL", getenv("MONGO_DB_URI", "")).strip()

        self.LOGGER_ID = _int("LOGGER_ID", 0)
        self.OWNER_ID = _int("OWNER_ID", 0)

        self.DURATION_LIMIT = _int("DURATION_LIMIT", 60) * 60
        self.MAX_FILE_SIZE = _int("MAX_FILE_SIZE", 2000) * 1024 * 1024
        self.QUEUE_LIMIT = _int("QUEUE_LIMIT", 25)
        self.PLAYLIST_LIMIT = _int("PLAYLIST_LIMIT", 200)
        self.MAX_CONCURRENT_DOWNLOADS = max(1, min(4, _int("MAX_CONCURRENT_DOWNLOADS", 2)))
        self.MAX_ASSISTANTS = max(1, min(5, _int("MAX_ASSISTANTS", 3)))

        self.SESSION1 = getenv("SESSION1", getenv("STRING_SESSION", "")).strip()
        self.SESSION2 = getenv("SESSION2", getenv("STRING2", "")).strip()
        self.SESSION3 = getenv("SESSION3", getenv("STRING3", "")).strip()
        self.SESSION4 = getenv("SESSION4", getenv("STRING4", "")).strip()
        self.SESSION5 = getenv("SESSION5", getenv("STRING5", "")).strip()

        self.SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/fallenx")
        self.SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/DevilsHeavenMF")
        self.OWNER_URL = getenv("OWNER_URL", "https://t.me/fallenx")

        self.AUTO_LEAVE = _bool("AUTO_LEAVE", False)
        self.AUTO_LEAVE_GRACE = max(1, _int("AUTO_LEAVE_GRACE", 6))
        self.AUTO_LEAVE_EXCLUDE = [
            _int_value for _int_value in (
                _int(x, 0) for x in getenv("AUTO_LEAVE_EXCLUDE", "").split(",") if x.strip()
            ) if _int_value
        ]
        self.AUTO_END = _bool("AUTO_END", False)

        self.CLEANUP_INTERVAL = max(300, _int("CLEANUP_INTERVAL", 3600))
        self.CLEANUP_MAX_AGE = max(1800, _int("CLEANUP_MAX_AGE", 21600))

        # Global capability switch. Per-group thumbnail generation is OFF
        # by default and is controlled independently in MongoDB.
        self.THUMB_GEN = _bool("THUMB_GEN", True)
        self.THUMB_QUALITY = max(50, min(95, _int("THUMB_QUALITY", 82)))
        self.VIDEO_PLAY = _bool("VIDEO_PLAY", True)

        self.LANG_CODE = getenv("LANG_CODE", "en").strip() or "en"

        self.COOKIES_URL = [
            url for url in getenv("COOKIES_URL", "").split()
            if url
        ]

        self.DEFAULT_THUMB = getenv(
            "DEFAULT_THUMB",
            str(_BASE_DIR / "anony/helpers/assets/start.jpg"),
        )

        _dead_defaults = {
            "https://files.catbox.moe/haagg2.png",
            "https://files.catbox.moe/zvziwk.jpg",
        }
        ping_env = getenv("PING_IMG")
        start_env = getenv("START_IMG")
        self.PING_IMG = (
            ping_env if ping_env and ping_env not in _dead_defaults
            else str(_BASE_DIR / "anony/helpers/assets/ping.jpg")
        )
        self.START_IMG = (
            start_env if start_env and start_env not in _dead_defaults
            else str(_BASE_DIR / "anony/helpers/assets/start.jpg")
        )

        self.BRAND_NAME = getenv("BRAND_NAME") or None
        self.BRAND_TAG = getenv("BRAND_TAG", "Lossless")
        self.BOT_NAME = getenv("BOT_NAME", "Wirq Music")

        # Kept OFF by default because direct CDN streams are less predictable
        # than a local FFmpeg-readable file on Railway.
        self.EXPERIMENTAL_DIRECT_STREAM = _bool(
            "EXPERIMENTAL_DIRECT_STREAM", True
        )

    def check(self):
        missing = [
            var for var in (
                "API_ID", "API_HASH", "BOT_TOKEN",
                "MONGO_URL", "LOGGER_ID", "OWNER_ID", "SESSION1"
            ) if not getattr(self, var)
        ]
        if missing:
            raise SystemExit(
                "Missing required environment variables: " + ", ".join(missing)
            )


config = None
