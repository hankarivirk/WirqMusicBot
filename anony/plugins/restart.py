# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


import os
import sys
import shutil

from pyrogram import filters, types

from anony import app, db, lang, spawn_task, stop


@app.on_message(filters.command(["logs"]) & app.sudoers)
@lang.language()
async def _logs(_, m: types.Message):
    sent = await m.reply_text(m.lang["log_fetch"])
    if not os.path.exists("log.txt"):
        return await sent.edit_text(m.lang["log_not_found"])
    # sent is a plain text message; it can't be turned into a document via
    # edit_media(). Delete the placeholder and send the document instead.
    try:
        await sent.delete()
    except Exception:
        pass
    await m.reply_document(
        document="log.txt",
        caption=m.lang["log_sent"].format(app.name),
    )


@app.on_message(filters.command(["logger"]) & app.sudoers)
@lang.language()
async def _logger(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text(m.lang["logger_usage"].format(m.command[0]))
    if m.command[1] not in ("on", "off"):
        return await m.reply_text(m.lang["logger_usage"].format(m.command[0]))

    if m.command[1] == "on":
        await db.set_logger(True)
        await m.reply_text(m.lang["logger_on"])
    else:
        await db.set_logger(False)
        await m.reply_text(m.lang["logger_off"])


@app.on_message(filters.command(["restart"]) & app.sudoers)
@lang.language()
async def _restart(_, m: types.Message):
    sent = await m.reply_text(m.lang["restarting"])

    # Confirm the restart via the bot connection FIRST, while it's
    # still alive — stop() below disconnects the bot client itself, so
    # editing this message after that would fail.
    await sent.edit_text(m.lang["restarted"])

    # stop() cancels background tasks and disconnects the bot/userbot
    # sessions, which halts any active playback — only THEN is it safe
    # to clean up cache/downloads. The old order (wipe the directories
    # first, then stop) could yank a file out from under an actively-
    # streaming track or an in-progress download/thumbnail write.
    task = spawn_task(stop(), name="restart-stop")
    await task

    for directory in ["cache", "downloads"]:
        shutil.rmtree(directory, ignore_errors=True)

    try: os.remove("log.txt")
    except Exception: pass

    os.execl(sys.executable, sys.executable, "-m", "anony")
