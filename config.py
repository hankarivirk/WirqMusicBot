from os import getenv
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Absolute path to the repo root, resolved from this file's own location
# rather than the process's current working directory. A path like
# "anony/helpers/assets/start.jpg" only resolves if the bot happens to
# be launched from the repo root; some process managers/hosts start it
# from a different cwd, which made the bundled images silently fail to
# send (falling back to text) even though the files were right there.
_BASE_DIR = Path(__file__).resolve().parent

class Config:
    def __init__(self):
        self.API_ID = int(getenv("API_ID", 0))
        self.API_HASH = getenv("API_HASH")

        self.BOT_TOKEN = getenv("BOT_TOKEN")
        self.MONGO_URL = getenv("MONGO_URL")

        self.LOGGER_ID = int(getenv("LOGGER_ID", 0))
        self.OWNER_ID = int(getenv("OWNER_ID", 0))

        self.DURATION_LIMIT = int(getenv("DURATION_LIMIT", 60)) * 60
        # In MB. The bot streams through a userbot/assistant account
        # (MTProto, not the Bot API), so this can go well past the Bot
        # API's old 20/50MB ceiling — Telegram's own server-side cap is
        # 2000MB (4000MB for Premium accounts). Defaults to 2000; raise
        # it if your assistant account has Premium and you want to
        # allow bigger uploads, but remember disk space and download
        # time both scale with this.
        self.MAX_FILE_SIZE = int(getenv("MAX_FILE_SIZE", 2000)) * 1024 * 1024
        self.QUEUE_LIMIT = int(getenv("QUEUE_LIMIT", 20))
        # How many tracks to pull in from a playlist link. Raised from the
        # old default of 20 so /play <playlist url> actually queues the
        # whole playlist for typical playlist sizes; long results are
        # shown as a Telegra.ph page instead of a giant chat message
        # (see PLAYLIST_WEB_THRESHOLD in anony/plugins/play.py).
        self.PLAYLIST_LIMIT = int(getenv("PLAYLIST_LIMIT", 200))

        self.SESSION1 = getenv("SESSION", None)
        self.SESSION2 = getenv("SESSION2", None)
        self.SESSION3 = getenv("SESSION3", None)

        self.SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/fallenx")
        self.SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/DevilsHeavenMF")
        self.OWNER_URL = getenv("OWNER_URL", "https://t.me/fallenx")

        self.AUTO_LEAVE: bool = getenv("AUTO_LEAVE", "False").lower() == "true"
        self.AUTO_END: bool = getenv("AUTO_END", "False").lower() == "true"
    
        self.THUMB_GEN: bool = getenv("THUMB_GEN", "True").lower() == "true"
        self.VIDEO_PLAY: bool = getenv("VIDEO_PLAY", "True").lower() == "true"

        self.LANG_CODE = getenv("LANG_CODE", "en")

        self.COOKIES_URL = [
            url for url in getenv("COOKIES_URL", "").split(" ")
            if url and "batbin.me" in url
        ]
        self.DEFAULT_THUMB = getenv("DEFAULT_THUMB", "https://te.legra.ph/file/3e40a408286d4eda24191.jpg")
        # Bundled locally (anony/helpers/assets/) instead of an external
        # image host — a dead/expired catbox.moe-style link is exactly
        # what silently broke /ping and /start before. Resolved to an
        # absolute path so it works no matter what directory the bot
        # process is actually launched from. Still overridable via env
        # if you want a custom URL or local path — EXCEPT the specific
        # old dead catbox.moe links this bot used to default to, which
        # are ignored on purpose: if your .env/host config still has one
        # of those left over from before, it would otherwise silently
        # keep winning over this fix forever.
        _dead_defaults = {
            "https://files.catbox.moe/haagg2.png",
            "https://files.catbox.moe/zvziwk.jpg",
        }
        _ping_env = getenv("PING_IMG")
        _start_env = getenv("START_IMG")
        self.PING_IMG = (
            _ping_env if _ping_env and _ping_env not in _dead_defaults
            else str(_BASE_DIR / "anony/helpers/assets/ping.jpg")
        )
        self.START_IMG = (
            _start_env if _start_env and _start_env not in _dead_defaults
            else str(_BASE_DIR / "anony/helpers/assets/start.jpg")
        )

        # Watermark shown on generated song thumbnails.
        # Leave BRAND_NAME unset to auto-use the bot's own Telegram name.
        self.BRAND_NAME = getenv("BRAND_NAME") or None
        self.BRAND_TAG = getenv("BRAND_TAG", "Lossless")

    def check(self):
        missing = [
            var
            for var in ["API_ID", "API_HASH", "BOT_TOKEN", "MONGO_URL", "LOGGER_ID", "OWNER_ID", "SESSION1"]
            if not getattr(self, var)
        ]
        if missing:
            raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")
