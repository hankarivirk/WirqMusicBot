# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


import html
import json
from functools import wraps
from pathlib import Path
from types import SimpleNamespace

from pyrogram import errors

from anony import config, db, logger

lang_codes = {
    "ar": "العربية",
    "de": "Deutsch",
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "hi": "हिन्दी",
    "ja": "日本語",
    "my": "မြန်မာဘာသာ",
    "pa": "ਪੰਜਾਬੀ",
    "pt": "Português",
    "ru": "Русский",
    "tr": "Türkçe",
    "zh": "中文"
}


class Language:
    """
    Language class for managing multilingual support using JSON language files.
    """

    def __init__(self):
        self.lang_codes = lang_codes
        self.lang_dir = Path("anony/locales")
        self.languages = self.load_files()

    def load_files(self):
        languages = {}
        lang_files = {file.stem: file for file in self.lang_dir.glob("*.json")}
        for lang_code, lang_file in lang_files.items():
            with open(lang_file, "r", encoding="utf-8") as file:
                languages[lang_code] = json.load(file)
        logger.info(f"Loaded languages: {', '.join(languages.keys())}")
        return languages

    async def get_lang(self, chat_id: int) -> dict:
        lang_code = await db.get_lang(chat_id)
        if lang_code not in self.languages:
            logger.warning(
                f"Unknown language code '{lang_code}' for chat {chat_id}, "
                f"falling back to '{config.LANG_CODE}'."
            )
            lang_code = config.LANG_CODE
        return self.languages.get(lang_code) or next(iter(self.languages.values()))

    def get_languages(self) -> dict:
        files = {f.stem for f in self.lang_dir.glob("*.json")}
        return {code: self.lang_codes[code] for code in sorted(files)}

    def language(self):
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                fallen = next(
                    (
                        arg
                        for arg in args
                        if hasattr(arg, "chat") or hasattr(arg, "message")
                    ),
                    None,
                )

                if fallen is None:
                    return

                if not fallen.from_user:
                    sender_chat = getattr(fallen, "sender_chat", None)
                    if not sender_chat:
                        return
                    # Anonymous group admin (or a linked-channel post as the
                    # chat itself): Telegram only lets real admins send this
                    # way, so give downstream code a safe stand-in instead
                    # of crashing on every .from_user.id / .mention access.
                    display_name = sender_chat.title or "Admin"
                    username = getattr(sender_chat, "username", None)
                    # Chats/channels can't be mentioned via tg://user, but we
                    # can still produce a proper clickable link when the
                    # sender chat has a public username instead of just
                    # dumping the raw title as unlinked text. The title is
                    # untrusted (chat-controlled) text going straight into
                    # an HTML anchor, so it must be escaped here.
                    safe_name = html.escape(display_name)
                    mention = (
                        f'<a href="https://t.me/{username}">{safe_name}</a>'
                        if username
                        else safe_name
                    )
                    setattr(
                        fallen,
                        "from_user",
                        SimpleNamespace(
                            id=sender_chat.id,
                            first_name=display_name,
                            username=username,
                            mention=mention,
                            is_bot=False,
                        ),
                    )

                if hasattr(fallen, "chat"):
                    chat = fallen.chat
                elif hasattr(fallen, "message"):
                    chat = fallen.message.chat

                if not chat: return

                if chat.id in db.blacklisted:
                    logger.info(f"Chat {chat.id} is blacklisted, leaving...")
                    return await chat.leave()

                lang_code = await db.get_lang(chat.id)
                if lang_code not in self.languages:
                    logger.warning(
                        f"Unknown language code '{lang_code}' for chat {chat.id}, "
                        f"falling back to '{config.LANG_CODE}'."
                    )
                    lang_code = config.LANG_CODE
                lang_dict = self.languages.get(lang_code) or next(iter(self.languages.values()))

                setattr(fallen, "lang", lang_dict)
                try:
                    return await func(*args, **kwargs)
                except (errors.FloodWait, errors.SlowmodeWait):
                    return
                except (
                    errors.ChannelInvalid, errors.ChannelPrivate,
                    errors.MessageIdInvalid, errors.MessageNotModified,
                ):
                    return
                except (
                    errors.Forbidden, errors.exceptions.Forbidden,
                    errors.ChatWriteForbidden, errors.exceptions.ChatWriteForbidden,
                ):
                    return

            return wrapper

        return decorator
