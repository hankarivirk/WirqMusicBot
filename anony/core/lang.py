import json
import os
import logging

LOGGER = logging.getLogger("MusicFlow.Lang")

_languages = {}

ALL_LOCALES = [
    "ar", "de", "en", "es", "fr", "hi", "ja", "my", "pa", "pt", "ru", "tr", "zh"
]

def load_languages():
    locales_dir = os.path.join(os.path.dirname(__file__), "..", "locales")
    for lang in ALL_LOCALES:
        f_path = os.path.join(locales_dir, f"{lang}.json")
        if os.path.exists(f_path):
            try:
                with open(f_path, "r", encoding="utf-8") as fp:
                    _languages[lang] = json.load(fp)
            except Exception as e:
                LOGGER.error(f"Error loading locale {lang}: {e}")

    # Fallback to English if not loaded
    if "en" not in _languages:
        LOGGER.warning("English locale not loaded.")

def get_string(lang: str, key: str) -> str:
    """Returns translated string for given language code with safe English fallback."""
    if lang in _languages and key in _languages[lang]:
        return _languages[lang][key]
    if "en" in _languages and key in _languages["en"]:
        return _languages["en"][key]
    return key
