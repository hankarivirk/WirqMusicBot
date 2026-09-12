# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


import html
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from pyrogram import enums, types

from anony import app


class Utilities:
    def __init__(self):
        pass

    def esc(self, value) -> str:
        """HTML-escape a value that may end up interpolated into a
        Telegram HTML-parsed message (YouTube titles/channel names, chat
        titles, etc.), so a stray <, >, or & can't break message parsing.
        """
        if value is None:
            return ""
        return html.escape(str(value))

    def format_eta(self, seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}:{seconds % 60:02d} min"
        else:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            s = seconds % 60
            return f"{h}:{m:02d}:{s:02d} h"

    def format_size(self, bytes: int) -> str:
        if bytes >= 1024**3:
            return f"{bytes / 1024 ** 3:.2f} GB"
        elif bytes >= 1024**2:
            return f"{bytes / 1024 ** 2:.2f} MB"
        elif bytes >= 1024:
            return f"{bytes / 1024:.2f} KB"
        else:
            return f"{bytes} B"

    def to_seconds(self, time: str) -> int:
        if not time:
            return 0
        try:
            parts = [int(p) for p in time.strip().split(":")]
            return sum(value * 60**i for i, value in enumerate(reversed(parts)))
        except ValueError:
            return 0


    def get_url(self, message_1: types.Message) -> str | None:
        link = None
        messages = [message_1]

        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)

        for message in messages:
            # Combine both fields independently instead of a plain `or`,
            # since falling back only when one is entirely falsy can still
            # miss entities if a message legitimately carries both.
            entities = list(message.entities or []) + list(message.caption_entities or [])

            for entity in entities:
                if entity.type == enums.MessageEntityType.TEXT_LINK:
                    link = entity.url
                    break
                elif entity.type == enums.MessageEntityType.URL:
                    text = message.text or message.caption
                    if not text:
                        continue
                    # Telegram entity offsets/lengths are in UTF-16 code
                    # units, not Python string indices, so slicing the raw
                    # str breaks as soon as an emoji or other non-BMP
                    # character appears before the link.
                    utf16 = text.encode("utf-16-le")
                    start = entity.offset * 2
                    end = start + entity.length * 2
                    link = utf16[start:end].decode("utf-16-le", errors="ignore")
                    break
            if link:
                break

        if link:
            return self._strip_si_param(link)
        return None

    @staticmethod
    def _strip_si_param(url: str) -> str:
        """Remove the tracking `si` query parameter, without truncating
        the URL if "si" happens to appear elsewhere (e.g. inside another
        parameter's value)."""
        try:
            parts = urlsplit(url)
            query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "si"]
            return urlunsplit(parts._replace(query=urlencode(query)))
        except Exception:
            return url


    async def extract_user(self, msg: types.Message) -> types.User | None:
        if msg.reply_to_message:
            return msg.reply_to_message.from_user

        if msg.entities:
            for e in msg.entities:
                if e.type == enums.MessageEntityType.TEXT_MENTION:
                    return e.user

        if msg.text:
            try:
                if m := re.search(r"@(\w{5,32})", msg.text):
                    return await app.get_users(m.group(0))
                if m := re.search(r"\b\d{6,15}\b", msg.text):
                    return await app.get_users(int(m.group(0)))
            except Exception:
                pass

        return None


    async def play_log(
        self,
        m: types.Message,
        link: str,
        title: str,
        duration: str,
    ) -> None:
        if m.chat.id == app.logger:
            return
        _text = m.lang["play_log"].format(
            app.name,
            m.chat.id,
            self.esc(m.chat.title),
            m.from_user.id,
            m.from_user.mention,
            link,
            self.esc(title),
            duration,
        )
        await app.send_message(chat_id=app.logger, text=_text)

    async def send_log(self, m: types.Message, chat: bool = False) -> None:
        if chat:
            user = m.from_user
            return await app.send_message(
                chat_id=app.logger,
                text=m.lang["log_chat"].format(
                    m.chat.id,
                    self.esc(m.chat.title),
                    user.id if user else 0,
                    user.mention if user else "Anonymous",
                ),
            )

        await app.send_message(
            chat_id=app.logger,
            text=m.lang["log_user"].format(
                m.from_user.id,
                f"@{m.from_user.username}",
                m.from_user.mention,
            ),
        )
