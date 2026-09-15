# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


import os

from pyrogram import filters, types

from anony import app, db, lang, queue
from anony.helpers import utils


@app.on_message(filters.command(["ac", "activevc"]) & app.sudoers)
@lang.language()
async def _activevc(_, m: types.Message):
    if not db.active_calls:
        return await m.reply_text(m.lang["vc_empty"])

    if m.command[0] == "ac":
        return await m.reply_text(m.lang["vc_count"].format(len(db.active_calls)))

    sent = await m.reply_text(m.lang["vc_fetching"])
    text = ""

    for i, chat in enumerate(db.active_calls):
        playing = queue.get_current(chat)
        title = utils.esc(playing.title[:25]) if playing else "N/A"
        text += f"\n{i+1}. <code>{chat}</code>\n    ➜ {title}"

    if len(text) < 4000:
        return await sent.edit_text(m.lang["vc_list"] + text)

    with open("activevc.txt", "w") as f:
        f.write(text)
    f.close()
    # sent is a plain text message; it can't be turned into a document via
    # edit_media(). Delete the placeholder and send the document instead.
    try:
        await sent.delete()
    except Exception:
        pass
    await m.reply_document(
        document="activevc.txt",
        caption=m.lang["vc_list"],
    )
    os.remove("activevc.txt")
