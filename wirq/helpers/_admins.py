from functools import wraps
from pyrogram import enums
from pyrogram.types import CallbackQuery, Message

async def is_admin(chat_id: int, user_id: int) -> bool:
    from wirq import app, db
    if user_id in app.sudoers:
        return True
    admins = await db.get_admins(chat_id)
    return user_id in admins

async def reload_admins(chat_id: int):
    from wirq import app
    try:
        admins = []
        async for m in app.get_chat_members(chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
            admins.append(m.user.id)
        return admins
    except Exception:
        return []

def can_manage_vc(func):
    @wraps(func)
    async def wrapper(_, m: Message, *args, **kwargs):
        from wirq import app
        if m.from_user and (m.from_user.id in app.sudoers or await is_admin(m.chat.id, m.from_user.id)):
            return await func(_, m, *args, **kwargs)
        return await m.reply_text("You must be an administrator with voice chat management rights.")
    return wrapper

def admin_check(func):
    @wraps(func)
    async def wrapper(_, q: CallbackQuery, *args, **kwargs):
        from wirq import app
        if q.from_user and (q.from_user.id in app.sudoers or await is_admin(q.message.chat.id, q.from_user.id)):
            return await func(_, q, *args, **kwargs)
        return await q.answer("Administrator permissions required to perform this action.", show_alert=True)
    return wrapper
