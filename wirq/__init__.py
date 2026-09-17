import time
import asyncio
import logging
from logging.handlers import RotatingFileHandler

# Install compatibility aliases before any module imports pytgcalls.
try:
    import pyrogram.errors as _pyrogram_errors
    for _legacy_name, _base_name in {
        "GroupcallForbidden": "Forbidden",
        "GroupcallInvalid": "BadRequest",
    }.items():
        if not hasattr(_pyrogram_errors, _legacy_name) and hasattr(_pyrogram_errors, _base_name):
            setattr(
                _pyrogram_errors,
                _legacy_name,
                type(_legacy_name, (getattr(_pyrogram_errors, _base_name),), {}),
            )
except Exception:
    pass

logging.basicConfig(
    format="[%(asctime)s - %(levelname)s] - %(name)s: %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler("log.txt", maxBytes=10485760, backupCount=5),
        logging.StreamHandler(),
    ],
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("ntgcalls").setLevel(logging.CRITICAL)
logging.getLogger("pymongo").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("pytgcalls").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)
__version__ = "3.0.3"

from config import Config
config = Config()

tasks = []
boot = time.time()

from wirq.core.dir import ensure_dirs
ensure_dirs()

from wirq.helpers._queue import Queue
from wirq.helpers._thumbnails import Thumbnail
queue = Queue()
thumb = Thumbnail()
from wirq.helpers._utilities import utils

from wirq.core.bot import Bot
app = Bot()

from wirq.core.userbot import Userbot
userbot = Userbot()

from wirq.core.mongo import MongoDB
db = MongoDB()

from wirq.core.lang import Language
lang = Language()

from wirq.core.telegram import Telegram
from wirq.core.youtube import YouTube
tg = Telegram()
yt = YouTube()

from wirq.core.calls import TgCall
anon = TgCall()
# Backwards-compatible public name used by plugins and __main__.
calls = anon

async def stop() -> None:
    logger.info("Stopping bot services...")
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.exceptions.CancelledError:
            pass
    await app.exit()
    await userbot.exit()
    await db.close()
    await thumb.close()
    logger.info("Bot services stopped cleanly.")
