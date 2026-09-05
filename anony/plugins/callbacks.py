# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


import re

from pyrogram import errors, filters, types

from anony import anon, app, db, lang, logger, queue, tg, yt
from anony.helpers import admin_check, buttons, can_manage_vc


@app.on_callback_query(filters.regex("cancel_dl") & ~app.bl_users)
@lang.language()
async def cancel_dl(_, query: types.CallbackQuery):
    await query.answer()
    await tg.cancel(query)


@app.on_callback_query(filters.regex(r"^controls(?:\s|$)") & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _controls(_, query: types.CallbackQuery):
    args = query.data.split()
    try:
        action, chat_id = args[1], int(args[2])
    except (IndexError, ValueError):
        try:
            await query.answer(query.lang["play_expired"], show_alert=True)
        except Exception:
            pass
        return
    qaction = len(args) == 4
    user = query.from_user.mention

    if action not in ("status", "pause", "resume", "skip", "force", "replay", "stop"):
        try:
            await query.answer(query.lang["play_expired"], show_alert=True)
        except Exception:
            pass
        return

    if not await db.get_call(chat_id):
        try:
            return await query.answer(query.lang["not_playing"], show_alert=True)
        except errors.QueryIdInvalid:
            try:
                await query.message.delete()
            except Exception:
                pass
            return

    if action == "status":
        return await query.answer()

    try:
        await query.answer(query.lang["processing"], show_alert=True)
    except errors.QueryIdInvalid:
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    if action == "pause":
        if not await db.playing(chat_id):
            return await query.answer(
                query.lang["play_already_paused"], show_alert=True
            )
        await anon.pause(chat_id)
        if qaction:
            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(chat_id, query.lang["paused"], False)
            )
        status = query.lang["paused"]
        reply = query.lang["play_paused"].format(user)

    elif action == "resume":
        if await db.playing(chat_id):
            return await query.answer(query.lang["play_not_paused"], show_alert=True)
        await anon.resume(chat_id)
        if qaction:
            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(chat_id, query.lang["playing"], True)
            )
        reply = query.lang["play_resumed"].format(user)

    elif action == "skip":
        await anon.play_next(chat_id)
        status = query.lang["skipped"]
        reply = query.lang["play_skipped"].format(user)

    elif action == "force":
        if len(args) < 4:
            return await query.edit_message_text(query.lang["play_expired"])

        pos, media = queue.check_item(chat_id, args[3])
        if not media or pos == -1:
            return await query.edit_message_text(query.lang["play_expired"])

        m_id = queue.get_current(chat_id).message_id
        queue.force_add(chat_id, media, remove=pos)
        try:
            await app.delete_messages(
                chat_id=chat_id, message_ids=[m_id, media.message_id], revoke=True
            )
            # Use the same "no message" sentinel (0) as the rest of the
            # codebase (calls.py), instead of None, to avoid type
            # inconsistencies where callers check `if media.message_id`.
            media.message_id = 0
        except Exception:
            pass

        msg = await app.send_message(chat_id=chat_id, text=query.lang["play_next"])
        if not media.file_path:
            media.file_path = await yt.download(media.id, video=media.video)
        media.message_id = msg.id
        return await anon.play_media(chat_id, msg, media)

    elif action == "replay":
        media = queue.get_current(chat_id)
        media.user = user
        await anon.replay(chat_id)
        status = query.lang["replayed"]
        reply = query.lang["play_replayed"].format(user)

    elif action == "stop":
        await anon.stop(chat_id)
        status = query.lang["stopped"]
        reply = query.lang["play_stopped"].format(user)

    if action in ["skip", "replay", "stop"]:
        try:
            await query.message.reply_text(reply, quote=False)
            await query.message.delete()
        except Exception:
            pass
        return

    try:
        caption_or_text = query.message.caption.html if query.message.caption else query.message.text.html
        mtext = re.sub(
            r"\n\n<blockquote>.*?</blockquote>",
            "",
            caption_or_text,
            flags=re.DOTALL,
        )
        keyboard = buttons.controls(
            chat_id, status=status if action != "resume" else None
        )
        await query.edit_message_text(
            f"{mtext}\n\n<blockquote>{reply}</blockquote>", reply_markup=keyboard
        )
    except errors.MessageNotModified:
        pass
    except Exception as e:
        logger.warning(f"Failed to update controls message for chat {chat_id}: {e}")


@app.on_callback_query(filters.regex(r"^help(?:\s|$)") & ~app.bl_users)
@lang.language()
async def _help(_, query: types.CallbackQuery):
    data = query.data.split()
    if len(data) == 1:
        return await query.answer(url=f"https://t.me/{app.username}?start=help")

    if data[1] == "back":
        return await query.edit_message_text(
            text=query.lang["help_menu"], reply_markup=buttons.help_markup(query.lang)
        )
    elif data[1] == "close":
        try:
            await query.message.delete()
            return await query.message.reply_to_message.delete()
        except Exception:
            return

    await query.edit_message_text(
        text=query.lang[f"help_{data[1]}"],
        reply_markup=buttons.help_markup(query.lang, True),
    )


@app.on_callback_query(filters.regex(r"^settings(?:\s|$)") & ~app.bl_users)
@lang.language()
@admin_check
async def _settings_cb(_, query: types.CallbackQuery):
    cmd = query.data.split()
    if len(cmd) == 1:
        return await query.answer()
    await query.answer(query.lang["processing"], show_alert=True)

    chat_id = query.message.chat.id
    _admin = await db.get_play_mode(chat_id)
    _delete = await db.get_cmd_delete(chat_id)
    _language = await db.get_lang(chat_id)
    _autoplay = await db.get_autoplay(chat_id)

    if cmd[1] == "delete":
        _delete = not _delete
        await db.set_cmd_delete(chat_id, _delete)
    elif cmd[1] == "play":
        await db.set_play_mode(chat_id, _admin)
        _admin = not _admin
    elif cmd[1] == "auto":
        _autoplay = not _autoplay
        await db.set_autoplay(chat_id, _autoplay)
    await query.edit_message_reply_markup(
        reply_markup=buttons.settings_markup(
            query.lang,
            _admin,
            _delete,
            _language,
            chat_id,
            _autoplay,
        )
    )
