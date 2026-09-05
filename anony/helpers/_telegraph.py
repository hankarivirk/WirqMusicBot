# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


import aiohttp

from anony import logger

API = "https://api.telegra.ph"


class Telegraph:
    """Publishes long playlists to a Telegra.ph page instead of dumping a
    huge (and Telegram-message-length-limited) track list into the chat.
    """

    def __init__(self):
        self.token: str | None = None

    async def _ensure_account(self) -> str | None:
        if self.token:
            return self.token

        from anony import db

        doc = await db.cache.find_one({"_id": "telegraph"})
        if doc and doc.get("token"):
            self.token = doc["token"]
            return self.token

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{API}/createAccount",
                    data={
                        "short_name": "Wirq Music Bot",
                        "author_name": "Wirq Music Bot",
                    },
                ) as resp:
                    data = await resp.json()
        except Exception as ex:
            logger.warning("Telegraph account creation failed: %s", ex)
            return None

        if not data.get("ok"):
            logger.warning("Telegraph account creation failed: %s", data)
            return None

        self.token = data["result"]["access_token"]
        await db.cache.update_one(
            {"_id": "telegraph"}, {"$set": {"token": self.token}}, upsert=True
        )
        return self.token

    async def create_playlist_page(self, title: str, tracks: list) -> str | None:
        """Create a Telegra.ph page listing every track in a playlist.

        Returns the page URL, or None if the page couldn't be created
        (caller should fall back to an in-chat message in that case).
        """
        token = await self._ensure_account()
        if not token:
            return None

        items = []
        for i, track in enumerate(tracks, start=1):
            name = track.title or track.id
            suffix = f" — {track.duration}" if track.duration else ""
            children = [f"{i}. "]
            if track.url:
                children.append({"tag": "a", "attrs": {"href": track.url}, "children": [name]})
            else:
                children.append(name)
            if suffix:
                children.append(suffix)
            items.append({"tag": "p", "children": children})

        payload = {
            "access_token": token,
            "title": (title or "Playlist")[:256],
            "author_name": "Wirq Music Bot",
            "content": items,
            "return_content": False,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{API}/createPage",
                    json=payload,
                ) as resp:
                    data = await resp.json()
        except Exception as ex:
            logger.warning("Telegraph page creation failed: %s", ex)
            return None

        if not data.get("ok"):
            logger.warning("Telegraph page creation failed: %s", data)
            return None

        return data["result"]["url"]
