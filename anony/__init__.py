# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot

import time
import asyncio
import logging
from logging.handlers import RotatingFileHandler

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

__version__ = "2.7.8"

from config import Config

config = Config()
config.check()
tasks: list[asyncio.Task] = []
boot = time.time()

# IMPORTANT: Pyrogram 2.2.x creates asyncio.Event/Lock/Semaphore objects in
# Client.__init__.  Those clients MUST be constructed while the real
# application loop is already running.  Keep these globals empty at module
# import time and populate them from init_runtime(), called from main().
app = None
userbot = None
db = None
lang = None
tg = None
yt = None
queue = None
thumb = None
anon = None


def spawn_task(coro, *, name: str | None = None):
    """Create a tracked background task on the application's running loop."""
    task = asyncio.create_task(coro, name=name)
    tasks.append(task)

    def _discard(done):
        try:
            tasks.remove(done)
        except ValueError:
            pass

    task.add_done_callback(_discard)
    return task


async def init_runtime() -> None:
    """Construct every async-bound service on the current running loop.

    Do not move these constructors back to module scope.  In particular,
    Pyrogram Client, AsyncMongoClient, asyncio locks/semaphores and PyTgCalls
    state are loop-sensitive.
    """
    global app, userbot, db, lang, tg, yt, queue, thumb, anon

    loop = asyncio.get_running_loop()
    logger.info("Async runtime initializing on loop=%s", type(loop).__name__)

    from anony.core.bot import Bot
    from anony.core.dir import ensure_dirs
    from anony.core.userbot import Userbot
    from anony.core.mongo import MongoDB
    from anony.core.lang import Language

    ensure_dirs()

    # Order matters: several helper/core modules import these globals.
    app = Bot()
    userbot = Userbot()
    db = MongoDB()
    lang = Language()

    from anony.core.telegram import Telegram
    from anony.core.youtube import YouTube
    from anony.helpers import Queue, Thumbnail
    from anony.core.calls import TgCall

    queue = Queue()
    thumb = Thumbnail()
    tg = Telegram()
    yt = YouTube()
    anon = TgCall()

    required = {
        "app": app, "userbot": userbot, "db": db, "lang": lang,
        "queue": queue, "thumb": thumb, "tg": tg, "yt": yt, "anon": anon,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise RuntimeError("Runtime initialization left globals unset: " + ", ".join(missing))

    # Hard assertion against accidental future regressions.  The useful
    # comparison is done immediately after construction, while the running
    # loop is unquestionably the current loop.
    clients = [app]
    clients.extend(client for _, client, _ in userbot._all)
    mismatched = [c.name for c in clients if getattr(c, "loop", loop) is not loop]
    if mismatched:
        raise RuntimeError(
            "Pyrogram loop initialization failed for: " + ", ".join(mismatched)
        )

    logger.info("Async runtime ready: %s clients on one event loop", len(clients))


async def stop() -> None:
    """Gracefully stop background workers and all async services."""
    logger.info("Stopping...")

    pending = [task for task in list(tasks) if not task.done()]
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    tasks.clear()

    if anon is not None:
        try:
            await anon.shutdown()
        except Exception:
            logger.debug("Voice engine shutdown failed", exc_info=True)

    if app is not None:
        try:
            await app.exit()
        except Exception:
            logger.debug("Bot stop failed", exc_info=True)

    if userbot is not None:
        try:
            await userbot.exit()
        except Exception:
            logger.debug("Assistant stop failed", exc_info=True)

    if db is not None:
        try:
            await db.close()
        except Exception:
            logger.debug("Mongo stop failed", exc_info=True)

    if thumb is not None:
        try:
            await thumb.close()
        except Exception:
            logger.debug("Thumbnail stop failed", exc_info=True)

    if yt is not None:
        try:
            await yt.close()
        except Exception:
            logger.debug("YouTube HTTP session shutdown failed", exc_info=True)

    logger.info("Stopped.\n")
