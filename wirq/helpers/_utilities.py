import html
from typing import Optional

class Utilities:
    @staticmethod
    def esc(text: Optional[str]) -> str:
        return html.escape(text or "")

    @staticmethod
    def to_seconds(time_str: Optional[str]) -> int:
        if not time_str:
            return 0
        parts = str(time_str).split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            return int(parts[0])
        except Exception:
            return 0

    @staticmethod
    async def play_log(message, link, title, duration):
        pass

    @staticmethod
    async def extract_user(m):
        if m.reply_to_message:
            return m.reply_to_message.from_user
        return None

utils = Utilities()
