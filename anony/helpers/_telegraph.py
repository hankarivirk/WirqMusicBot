try:
    import aiohttp
except ImportError:
    aiohttp = None
import json
import logging
from typing import List, Dict, Any, Optional
import config

LOGGER = logging.getLogger("MusicFlow.Telegraph")
_telegraph_token = None

async def get_telegraph_token() -> Optional[str]:
    global _telegraph_token
    if _telegraph_token:
        return _telegraph_token
    try:
        if not aiohttp:
            return None
        async with aiohttp.ClientSession() as session:
            url = "https://api.telegra.ph/createAccount"
            data = {"short_name": "MusicFlow", "author_name": config.BOT_NAME}
            async with session.post(url, data=data) as resp:
                res = await resp.json()
                if res.get("ok"):
                    _telegraph_token = res["result"]["access_token"]
                    return _telegraph_token
    except Exception as e:
        LOGGER.error(f"Telegraph token creation failed: {e}")
    return None

async def create_telegraph_queue_page(title: str, tracks: List[Dict[str, Any]]) -> Optional[str]:
    """
    Publishes long queue or full playlist tracks to a clean Telegraph web page.
    Returns the public Telegraph URL.
    """
    token = await get_telegraph_token()
    if not token:
        return None

    content = [
        {"tag": "h3", "children": [f"{title} — MUSIC FLOW Queue"]},
        {"tag": "p", "children": [f"Total Tracks: {len(tracks)}"]},
        {"tag": "hr"},
    ]

    for i, t in enumerate(tracks, 1):
        line = f"{i:02d}. {t.get('title', 'Unknown')} ({t.get('duration') or 'Unknown'}) — requested by {t.get('requester', 'Anonymous')}"
        content.append({"tag": "p", "children": [line]})

    try:
        if not aiohttp:
            return None
        async with aiohttp.ClientSession() as session:
            url = "https://api.telegra.ph/createPage"
            payload = {
                "access_token": token,
                "title": f"Queue ({len(tracks)} Tracks) — {config.BOT_NAME}",
                "author_name": config.BOT_NAME,
                "author_url": config.OWNER_URL or "",
                "content": json.dumps(content),
                "return_content": False,
            }
            async with session.post(url, json=payload) as resp:
                res = await resp.json()
                if res.get("ok"):
                    return res["result"]["url"]
    except Exception as e:
        LOGGER.error(f"Telegraph page creation failed: {e}")
    return None
