# Wirq Music Bot - Persistent Database Layer
# Bot Name: Wirq Music Bot
# Owner: @wirq4 | Support: @wirqbots | GitHub: Hankarivirk/WirqMusicbot

import json
import time
from pathlib import Path
from typing import List, Optional, Set, Dict, Any

from config import Config
from wirq import logger

config = Config()

class MongoDB:
    def __init__(self):
        # Runtime in-memory caches
        self.active_calls: Dict[int, int] = {}
        self.admin_list: Dict[int, List[int]] = {}
        self.blacklisted: List[int] = []
        self.chats: List[int] = []
        self.users: List[int] = []
        self.auth: Dict[int, Set[int]] = {}
        self.user_lang: Dict[int, str] = {}
        self.group_lang: Dict[int, str] = {}
        self.loop: Dict[int, int] = {}       # 0: OFF, 1: TRACK, 2: QUEUE
        self.bass: Dict[int, int] = {}
        self.volume: Dict[int, int] = {}     # 1-100%
        self.autoplay: Set[int] = set()
        self.group_thumb: Dict[int, bool] = {}
        self.global_thumb: Optional[bool] = None
        self.assistant: Dict[int, int] = {}
        self.logger_enabled: bool = True
        self.notified: List[int] = []
        
        # Usage stats
        self.tracks_played: int = 0
        self.start_time: float = time.time()

        # Database connections
        self._motor_client = None
        self._db = None
        self._json_store = Path("cache/db_store.json")
        self._load_local_store()

    def _load_local_store(self):
        try:
            if self._json_store.exists():
                with open(self._json_store, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.chats = [int(x) for x in data.get("chats", [])]
                self.users = [int(x) for x in data.get("users", [])]
                self.user_lang = {int(k): v for k, v in data.get("user_lang", {}).items()}
                self.group_lang = {int(k): v for k, v in data.get("group_lang", {}).items()}
                self.loop = {int(k): int(v) for k, v in data.get("loop", {}).items()}
                self.volume = {int(k): int(v) for k, v in data.get("volume", {}).items()}
                self.autoplay = {int(x) for x in data.get("autoplay", [])}
                self.group_thumb = {int(k): bool(v) for k, v in data.get("group_thumb", {}).items()}
                self.global_thumb = data.get("global_thumb", None)
                self.tracks_played = int(data.get("tracks_played", 0))
        except Exception as e:
            logger.warning(f"Failed to load local DB cache: {e}")

    def _save_local_store(self):
        try:
            self._json_store.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "chats": self.chats,
                "users": self.users,
                "user_lang": self.user_lang,
                "group_lang": self.group_lang,
                "loop": self.loop,
                "volume": self.volume,
                "autoplay": list(self.autoplay),
                "group_thumb": self.group_thumb,
                "global_thumb": self.global_thumb,
                "tracks_played": self.tracks_played,
            }
            with open(self._json_store, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save local DB cache: {e}")

    async def connect(self):
        if config.MONGO_URL:
            try:
                import motor.motor_asyncio
                self._motor_client = motor.motor_asyncio.AsyncIOMotorClient(
                    config.MONGO_URL, serverSelectionTimeoutMS=5000
                )
                self._db = self._motor_client.get_default_database("wirq_music")
                await self._motor_client.admin.command('ping')
                logger.info("Connected to MongoDB cluster successfully.")
                
                async for doc in self._db.chats.find():
                    cid = doc.get("chat_id")
                    if cid:
                        self.chats.append(cid)
                        if "lang" in doc: self.group_lang[cid] = doc["lang"]
                        if "loop" in doc: self.loop[cid] = doc["loop"]
                        if "volume" in doc: self.volume[cid] = doc["volume"]
                        if doc.get("autoplay"): self.autoplay.add(cid)
                        if "thumbnail" in doc: self.group_thumb[cid] = doc["thumbnail"]

                async for doc in self._db.users.find():
                    uid = doc.get("user_id")
                    if uid:
                        self.users.append(uid)
                        if "lang" in doc: self.user_lang[uid] = doc["lang"]

                settings_doc = await self._db.settings.find_one({"_id": "global"})
                if settings_doc:
                    self.global_thumb = settings_doc.get("thumbnail", None)

                stats_doc = await self._db.stats.find_one({"_id": "global"})
                if stats_doc:
                    self.tracks_played = stats_doc.get("tracks_played", 0)

            except Exception as e:
                logger.warning(f"MongoDB connection failed ({e}). Operating in persistent local mode.")
                self._motor_client = None
                self._db = None
        else:
            logger.info("Operating in persistent local storage mode.")

    async def close(self):
        self._save_local_store()
        if self._motor_client:
            self._motor_client.close()

    async def get_call(self, chat_id: int) -> bool:
        return chat_id in self.active_calls

    async def add_call(self, chat_id: int) -> None:
        self.active_calls[chat_id] = 1

    async def remove_call(self, chat_id: int) -> None:
        self.active_calls.pop(chat_id, None)

    async def playing(self, chat_id: int, paused: Optional[bool] = None) -> bool:
        if paused is not None:
            self.active_calls[chat_id] = int(not paused)
        return bool(self.active_calls.get(chat_id, 0))

    async def get_admins(self, chat_id: int, reload: bool = False) -> List[int]:
        from wirq.helpers._admins import reload_admins
        if chat_id not in self.admin_list or reload:
            admins = await reload_admins(chat_id)
            if admins:
                self.admin_list[chat_id] = admins
        return self.admin_list.get(chat_id, [])

    async def get_loop(self, chat_id: int) -> int:
        return self.loop.get(chat_id, 0)

    async def set_loop(self, chat_id: int, mode: int) -> None:
        self.loop[chat_id] = mode
        self._save_local_store()
        if self._db:
            try:
                await self._db.chats.update_one(
                    {"chat_id": chat_id}, {"$set": {"loop": mode}}, upsert=True
                )
            except Exception:
                pass

    async def get_volume(self, chat_id: int) -> int:
        return self.volume.get(chat_id, 100)

    async def set_volume(self, chat_id: int, vol: int) -> None:
        self.volume[chat_id] = vol
        self._save_local_store()
        if self._db:
            try:
                await self._db.chats.update_one(
                    {"chat_id": chat_id}, {"$set": {"volume": vol}}, upsert=True
                )
            except Exception:
                pass

    async def get_autoplay(self, chat_id: int) -> bool:
        return chat_id in self.autoplay

    async def set_autoplay(self, chat_id: int, state: bool) -> None:
        if state:
            self.autoplay.add(chat_id)
        else:
            self.autoplay.discard(chat_id)
        self._save_local_store()
        if self._db:
            try:
                await self._db.chats.update_one(
                    {"chat_id": chat_id}, {"$set": {"autoplay": state}}, upsert=True
                )
            except Exception:
                pass

    async def get_thumbnail_pref(self, chat_id: int) -> Optional[bool]:
        return self.group_thumb.get(chat_id, None)

    async def set_thumbnail_pref(self, chat_id: int, state: Optional[bool]) -> None:
        if state is None:
            self.group_thumb.pop(chat_id, None)
        else:
            self.group_thumb[chat_id] = state
        self._save_local_store()
        if self._db:
            try:
                await self._db.chats.update_one(
                    {"chat_id": chat_id}, {"$set": {"thumbnail": state}}, upsert=True
                )
            except Exception:
                pass

    async def get_global_thumbnail(self) -> Optional[bool]:
        return self.global_thumb

    async def set_global_thumbnail(self, state: bool) -> None:
        self.global_thumb = state
        self._save_local_store()
        if self._db:
            try:
                await self._db.settings.update_one(
                    {"_id": "global"}, {"$set": {"thumbnail": state}}, upsert=True
                )
            except Exception:
                pass

    async def is_thumb_enabled(self, chat_id: int) -> bool:
        grp = await self.get_thumbnail_pref(chat_id)
        if grp is not None:
            return grp
        glob = await self.get_global_thumbnail()
        if glob is not None:
            return glob
        return config.THUMB_GEN

    async def get_lang(self, chat_id: int) -> str:
        return self.group_lang.get(chat_id, config.LANG_CODE)

    async def set_lang(self, chat_id: int, lang_code: str) -> None:
        self.group_lang[chat_id] = lang_code
        self._save_local_store()
        if self._db:
            try:
                await self._db.chats.update_one(
                    {"chat_id": chat_id}, {"$set": {"lang": lang_code}}, upsert=True
                )
            except Exception:
                pass

    async def get_user_lang(self, user_id: int) -> str:
        return self.user_lang.get(user_id, config.LANG_CODE)

    async def set_user_lang(self, user_id: int, lang_code: str) -> None:
        self.user_lang[user_id] = lang_code
        self._save_local_store()
        if self._db:
            try:
                await self._db.users.update_one(
                    {"user_id": user_id}, {"$set": {"lang": lang_code}}, upsert=True
                )
            except Exception:
                pass

    async def get_bass(self, chat_id: int) -> int:
        return self.bass.get(chat_id, 0)

    async def set_bass(self, chat_id: int, level: int) -> None:
        self.bass[chat_id] = level

    async def is_chat(self, chat_id: int) -> bool:
        return chat_id in self.chats

    async def add_chat(self, chat_id: int) -> None:
        if chat_id not in self.chats:
            self.chats.append(chat_id)
            self._save_local_store()

    async def rm_chat(self, chat_id: int) -> None:
        if chat_id in self.chats:
            self.chats.remove(chat_id)
            self._save_local_store()

    async def get_chats(self) -> List[int]:
        return list(self.chats)

    async def track_played(self) -> None:
        self.tracks_played += 1
        self._save_local_store()

    async def get_stats(self) -> Dict[str, Any]:
        return {
            "tracks_played": self.tracks_played,
            "chats_count": len(self.chats),
            "active_calls": len(self.active_calls),
            "uptime": int(time.time() - self.start_time),
        }

    async def get_assistant(self, chat_id: int):
        from wirq import anon
        if not anon.clients:
            return None
        return anon.clients[0]

    async def is_auth(self, chat_id: int, user_id: int) -> bool:
        return user_id in self.auth.get(chat_id, set())

    async def add_auth(self, chat_id: int, user_id: int) -> None:
        self.auth.setdefault(chat_id, set()).add(user_id)

    async def rm_auth(self, chat_id: int, user_id: int) -> None:
        if chat_id in self.auth:
            self.auth[chat_id].discard(user_id)

    async def add_blacklist(self, chat_id: int) -> None:
        if chat_id not in self.blacklisted:
            self.blacklisted.append(chat_id)

    async def del_blacklist(self, chat_id: int) -> None:
        if chat_id in self.blacklisted:
            self.blacklisted.remove(chat_id)

    async def get_blacklisted(self) -> List[int]:
        return list(self.blacklisted)

    async def is_logger(self) -> bool:
        return self.logger_enabled

    async def set_logger(self, state: bool) -> None:
        self.logger_enabled = state
