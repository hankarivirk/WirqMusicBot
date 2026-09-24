import asyncio
import os
import time
import logging
from typing import Optional

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

LOGGER = logging.getLogger("MusicFlow.Stream")

# Memory stream URL cache (2 hour TTL)
_stream_cache = {}
CACHE_TTL = 7200

async def get_stream_url(link: str) -> Optional[str]:
    """
    Extracts high-quality direct audio stream URL via yt-dlp asynchronously.
    Uses mobile/embedded client configurations to bypass web bot-verification challenges.
    Caches stream URLs to prevent duplicate network hits on replay/loop.
    """
    if not link:
        return None

    now = time.time()
    if link in _stream_cache:
        ts, url = _stream_cache[link]
        if now - ts < CACHE_TTL:
            return url

    cookie_file = os.getenv("COOKIE_FILE")
    if not cookie_file or not os.path.exists(cookie_file):
        cookies_dir = "anony/cookies"
        if os.path.exists(cookies_dir):
            for f in os.listdir(cookies_dir):
                if f.endswith(".txt"):
                    cookie_file = os.path.join(cookies_dir, f)
                    break

    def _extract():
        if yt_dlp is None:
            return None

        # Robust client extractor args to bypass "Sign in to confirm you're not a bot"
        base_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "source_address": "0.0.0.0",
            "nocheckcertificate": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["ios", "android", "mweb", "web_embedded"]
                }
            },
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
                "Accept-Language": "en-US,en;q=0.9",
            },
        }

        if cookie_file and os.path.exists(cookie_file):
            base_opts["cookiefile"] = cookie_file

        try:
            with yt_dlp.YoutubeDL(base_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                if info and info.get("url"):
                    return info.get("url")
        except Exception as e:
            LOGGER.warning(f"Primary stream extraction with mobile client failed for {link}: {e}")

        # Fallback extraction without extractor_args
        fallback_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "source_address": "0.0.0.0",
        }
        if cookie_file and os.path.exists(cookie_file):
            fallback_opts["cookiefile"] = cookie_file

        try:
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                if info and info.get("url"):
                    return info.get("url")
        except Exception as e:
            LOGGER.error(f"Fallback stream extraction failed for {link}: {e}")
            return None

        return None

    url = await asyncio.to_thread(_extract)
    if url:
        _stream_cache[link] = (now, url)
    return url
