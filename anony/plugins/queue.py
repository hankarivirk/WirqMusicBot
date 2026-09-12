# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


from pyrogram import filters, types

from anony import app, config, db, lang, queue, thumb
from anony.helpers import Track, buttons, can_manage_vc, utils


@app.on_message(filters.command(["queue", "playing"]) & filters.group & ~app.bl_users)
@lang.language()
async def _queue_func(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    _reply = await m.reply_text(m.lang["queue_fetching"])
    _queue = queue.get_queue(m.chat.id)
    _media = _queue[0]
    _thumb = (
        await thumb.generate(_media)
        if isinstance(_media, Track)
        else config.DEFAULT_THUMB
    ) if config.THUMB_GEN else None
    _text = m.lang["queue_curr"].format(
        utils.esc(_media.url),
        utils.esc(_media.title[:50]),
        _media.duration,
        _media.user,
    )
    _queue.pop(0)

    if _queue:
        _text += "<blockquote expandable>"
        for i, media in enumerate(_queue, start=1):
            if i == 15:
                break
            _text += m.lang["queue_item"].format(
                i + 1, utils.esc(media.title), media.duration
            )
        _text += "</blockquote>"

    _playing = await db.playing(m.chat.id)
    _buttons = buttons.queue_markup(
            m.chat.id,
            m.lang["playing"] if _playing else m.lang["paused"],
            _playing,
        )
    if _thumb:
        # A plain text message can't be turned into a photo via
        # edit_media() — Telegram doesn't support converting message types
        # in place. Delete the text placeholder and send a fresh photo
        # message instead.
        try:
            await _reply.delete()
        except Exception:
            pass
        await app.send_photo(
            chat_id=m.chat.id,
            photo=_thumb,
            caption=_text,
            reply_markup=_buttons,
        )
    else:
        await _reply.edit_text(
            text=_text,
            reply_markup=_buttons,
        )


@app.on_message(filters.command(["remove", "rm"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _remove(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    if len(m.command) < 2 or not m.command[1].isdigit():
        return await m.reply_text(m.lang["queue_remove_usage"])

    position = int(m.command[1])
    if position == 1:
        return await m.reply_text(m.lang["queue_remove_current"])

    removed = queue.remove_at(m.chat.id, position)
    if not removed:
        return await m.reply_text(m.lang["queue_position_invalid"])

    await m.reply_text(
        m.lang["queue_removed"].format(utils.esc(removed.title), position)
    )


@app.on_message(filters.command(["move", "mv"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _move(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    if (
        len(m.command) < 3
        or not m.command[1].isdigit()
        or not m.command[2].isdigit()
    ):
        return await m.reply_text(m.lang["queue_move_usage"])

    from_pos, to_pos = int(m.command[1]), int(m.command[2])
    if from_pos == 1 or to_pos == 1:
        return await m.reply_text(m.lang["queue_move_current"])

    moved = queue.move(m.chat.id, from_pos, to_pos)
    if not moved:
        return await m.reply_text(m.lang["queue_position_invalid"])

    await m.reply_text(
        m.lang["queue_moved"].format(utils.esc(moved.title), from_pos, to_pos)
    )
