# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


from functools import wraps

from pyrogram import StopPropagation, enums, types

from anony import app, db, logger


def admin_check(func):
    @wraps(func)
    async def wrapper(_, update: types.Message | types.CallbackQuery, *args, **kwargs):
        async def reply(text):
            if isinstance(update, types.Message):
                return await update.reply_text(text)
            else:
                return await update.answer(text, show_alert=True)

        chat = (
            update.chat
            if isinstance(update, types.Message)
            else update.message.chat
        )
        if chat.type == enums.ChatType.PRIVATE:
            return await func(_, update, *args, **kwargs)

        if isinstance(update, types.Message) and update.sender_chat and update.sender_chat.id == chat.id:
            return await func(_, update, *args, **kwargs)

        user_id = update.from_user.id
        admins = await db.get_admins(chat.id)

        if user_id in app.sudoers:
            return await func(_, update, *args, **kwargs)

        if user_id not in admins:
            return await reply(update.lang["user_no_perms"])

        return await func(_, update, *args, **kwargs)

    return wrapper


def can_manage_vc(func):
    @wraps(func)
    async def wrapper(_, update: types.Message | types.CallbackQuery, *args, **kwargs):
        chat_id = (
            update.chat.id
            if isinstance(update, types.Message)
            else update.message.chat.id
        )
        if isinstance(update, types.Message) and update.sender_chat and update.sender_chat.id == chat_id:
            return await func(_, update, *args, **kwargs)

        user_id = update.from_user.id

        if user_id in app.sudoers:
            return await func(_, update, *args, **kwargs)

        if await db.is_auth(chat_id, user_id):
            return await func(_, update, *args, **kwargs)

        admins = await db.get_admins(chat_id)
        if user_id in admins:
            return await func(_, update, *args, **kwargs)

        if isinstance(update, types.Message):
            return await update.reply_text(update.lang["user_no_perms"])
        else:
            return await update.answer(update.lang["user_no_perms"], show_alert=True)

    return wrapper


async def is_admin(chat_id: int, user_id: int) -> bool:
    if user_id in await db.get_admins(chat_id):
        return True
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in [
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER,
        ]
    except Exception:
        raise StopPropagation


async def reload_admins(chat_id: int) -> list[int] | None:
    """Fetch the current admin list for a chat.

    Returns None on a transient failure (e.g. a Telegram API error) instead
    of an empty list, so callers can distinguish "no admins" from
    "couldn't fetch admins" and avoid caching a bad result.
    """
    try:
        admins = [
            admin
            async for admin in app.get_chat_members(
                chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS
            )
            if not admin.user.is_bot
        ]
        return [admin.user.id for admin in admins]
    except Exception as e:
        logger.warning(f"Failed to reload admins for chat {chat_id}: {e}")
        return None
