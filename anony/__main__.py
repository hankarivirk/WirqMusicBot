# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


import os
import asyncio
import signal
import importlib

from pyrogram import types

from anony import (anon, app, config, db, logger,
                   stop, thumb, userbot, yt)
from anony.plugins import all_modules


async def idle():
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)
    except NotImplementedError:
        def handler(sig, frame):
            loop.call_soon_threadsafe(stop_event.set)

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    await stop_event.wait()

async def main():
    await db.connect()
    await app.boot()
    await userbot.boot()
    await anon.boot()
    await thumb.start()

    for module in all_modules:
        importlib.import_module(f"anony.plugins.{module}")
    logger.info(f"Loaded {len(all_modules)} modules.")

    if config.COOKIES_URL:
        await yt.save_cookies(config.COOKIES_URL)

    # Diagnostic: prints how PING_IMG/START_IMG will actually be sent,
    # every startup — so a genuinely broken local path is visible
    # immediately instead of only showing up as a silent fallback-to-
    # text the next time someone runs /ping or /start. A Telegram
    # file_id (a photo already uploaded to Telegram, reused by
    # reference) is a valid third option alongside a URL or a local
    # path — it's neither, so it needs its own check rather than being
    # wrongly flagged as a missing file.
    for name, value in (("PING_IMG", config.PING_IMG), ("START_IMG", config.START_IMG)):
        if value.startswith("http"):
            logger.info(f"{name} is set to a URL: {value}")
        elif "/" not in value and len(value) > 40:
            # Telegram file_ids are long, path-separator-free strings —
            # local paths and URLs always contain at least one "/".
            logger.info(f"{name} is set to a Telegram file_id (previously uploaded photo).")
        else:
            exists = os.path.isfile(value)
            level = logger.info if exists else logger.warning
            level(f"{name} -> {value} (exists: {exists})")

    await app.set_bot_commands([
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
    ])

    sudoers = await db.get_sudoers()
    app.sudoers.update(sudoers)
    app.bl_users.update(await db.get_blacklisted())
    logger.info(f"Loaded {len(app.sudoers)} sudo users.")

    await idle()
    await stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as ex:
        raise SystemExit(ex)
