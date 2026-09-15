# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot

"""Single-loop launcher for Wirq Music Bot.

IMPORTANT:
PyroTGFork/Pyrogram imports a synchronous compatibility layer that may capture
an event loop during import.  Therefore this module MUST NOT import pyrogram
at module scope and MUST NOT use asyncio.run() after importing pyrogram.
The application loop is created and installed first; Pyrogram is imported only
from inside that running loop.
"""

import asyncio
import importlib
import os
import signal

# Install uvloop policy before the first asyncio loop is created.  Do NOT import
# pyrogram here: pyrogram's sync layer can capture the current loop at import.
try:
    import uvloop
except ImportError:
    uvloop = None

if uvloop is not None:
    uvloop.install()

import anony


async def idle():
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)
    except (NotImplementedError, RuntimeError):
        def handler(sig, frame):
            loop.call_soon_threadsafe(stop_event.set)

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    await stop_event.wait()


async def main():
    # This is the FIRST point at which Pyrogram is imported.  We are already
    # inside the real application loop, so Pyrogram's loop-sensitive globals
    # and all Client instances resolve to this exact loop.
    await anony.init_runtime()

    # Import Pyrogram types only after init_runtime() has entered the running
    # loop.  Importing them at module scope is enough to trigger Pyrogram's
    # sync compatibility layer and recreate the original loop mismatch.
    from pyrogram import types

    from anony.plugins import all_modules
    from anony.plugins.misc import start_background_tasks

    started = False
    try:
        await anony.db.connect()
        await anony.app.boot()
        await anony.userbot.boot()
        await anony.anon.boot()
        await anony.thumb.start()

        for module in all_modules:
            importlib.import_module(f"anony.plugins.{module}")
        await start_background_tasks()
        anony.logger.info("Loaded %s modules.", len(all_modules))

        if anony.config.COOKIES_URL:
            await anony.yt.save_cookies(anony.config.COOKIES_URL)

        for name, value in (("PING_IMG", anony.config.PING_IMG), ("START_IMG", anony.config.START_IMG)):
            if value.startswith("http"):
                anony.logger.info("%s is set to a URL: %s", name, value)
            elif "/" not in value and len(value) > 40:
                anony.logger.info("%s is set to a Telegram file_id.", name)
            else:
                exists = os.path.isfile(value)
                level = anony.logger.info if exists else anony.logger.warning
                level("%s -> %s (exists: %s)", name, value, exists)

        await anony.app.set_bot_commands([
            types.BotCommand("play", "Play a song by name, link, or reply to audio"),
            types.BotCommand("playmusic", "Play the YouTube Music version of a song"),
            types.BotCommand("vplay", "Play a video by name, link, or reply to video"),
            types.BotCommand("queue", "See what's lined up"),
            types.BotCommand("remove", "Remove a track from the queue by position"),
            types.BotCommand("move", "Reorder a track in the queue"),
            types.BotCommand("skip", "Skip to the next track"),
            types.BotCommand("pause", "Pause playback"),
            types.BotCommand("resume", "Resume playback"),
            types.BotCommand("stop", "Stop playback and clear the queue"),
            types.BotCommand("seek", "Jump to a specific point in the track"),
            types.BotCommand("loop", "Repeat the current track"),
            types.BotCommand("autoplay", "Toggle autoplay on/off"),
            types.BotCommand("bass", "Set bass boost level (0-20 dB)"),
            types.BotCommand("language", "Change the bot's language for this chat"),
            types.BotCommand("ping", "Check the bot's status"),
            types.BotCommand("start", "See a welcome message"),
            types.BotCommand("help", "See all commands and how to use them"),
            types.BotCommand("thumbnail", "Enable/disable generated player thumbnails"),
        ])

        anony.app.sudoers.update(await anony.db.get_sudoers())
        anony.app.bl_users.update(await anony.db.get_blacklisted())
        anony.logger.info("Loaded %s sudo users.", len(anony.app.sudoers))

        started = True
        await idle()
    finally:
        if started or anony.app is not None:
            await anony.stop()


def run():
    """Run one and only one asyncio event loop for the entire application.

    A manual loop is intentional here instead of asyncio.run().  It makes the
    loop explicit/current before Pyrogram's compatibility layer is imported and
    gives Pyrogram, PyTgCalls and MongoDB one stable loop for their whole life.
    """
    if uvloop is not None:
        loop = uvloop.new_event_loop()
    else:
        loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            asyncio.set_event_loop(None)
            loop.close()


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        pass
