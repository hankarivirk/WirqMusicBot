import json
from pathlib import Path
from functools import wraps
from wirq import config, db, logger

lang_codes = {
    "ar": "العربية", "de": "Deutsch", "en": "English", "es": "Español",
    "fr": "Français", "hi": "हिन्दी", "ja": "日本語", "my": "မြန်မာဘာသာ",
    "pa": "ਪੰਜਾਬੀ", "pt": "Português", "ru": "Русский", "tr": "Türkçe", "zh": "中文"
}

class Language:
    def __init__(self):
        self.lang_codes = lang_codes
        self.lang_dir = Path(__file__).resolve().parent.parent / "locales"
        self.languages = self.load_files()

    def load_files(self):
        languages = {}
        for f in self.lang_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as file:
                    languages[f.stem] = json.load(file)
            except Exception as e:
                logger.warning(f"Could not load locale {f}: {e}")
        if not languages:
            languages["en"] = {"play_media": "Streaming: {1}"}
        return languages

    async def get_lang(self, chat_id: int) -> dict:
        code = await db.get_lang(chat_id)
        return self.languages.get(code) or self.languages.get(config.LANG_CODE) or self.languages.get("en", {})

    def language(self):
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                message = next((a for a in args if hasattr(a, "chat") or hasattr(a, "message")), None)
                if message:
                    chat_id = getattr(message, "chat", message).id
                    lang_dict = await self.get_lang(chat_id)
                    setattr(message, "lang", lang_dict)
                return await func(*args, **kwargs)
            return wrapper
        return decorator
