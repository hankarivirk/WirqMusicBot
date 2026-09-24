from typing import Union
from pyrogram.types import Message, CallbackQuery
from pyrogram.enums import ChatMemberStatus
import config
from anony.utils.database import is_sudo, is_authuser

async def is_admin(event: Union[Message, CallbackQuery]) -> bool:
    """
    Validates whether the user who triggered the event has playback/admin privileges.
    Checks OWNER_ID, SUDO_USERS, Group Creator, Administrators, and Authorized Users.
    """
    user = event.from_user
    if not user:
        return False
    user_id = user.id

    # 1. Owner & Sudo override
    if user_id == config.OWNER_ID or await is_sudo(user_id):
        return True

    chat = event.message.chat if isinstance(event, CallbackQuery) else event.chat
    if not chat:
        return False

    # 2. Private chats
    if chat.type.value in ["private", "bot"]:
        return True

    # 3. Check Authorized Users
    if await is_authuser(chat.id, user_id):
        return True

    # 4. Check Telegram Group Admin permissions
    try:
        client = event._client
        member = await client.get_chat_member(chat.id, user_id)
        if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return True
    except Exception:
        pass

    return False
