import logging
from typing import Dict, List, Union, Set, Optional, Any
try:
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError:
    AsyncIOMotorClient = None
import config

LOGGER = logging.getLogger("MusicFlow.MongoDB")

# Primary Async MongoDB connection
mongodb = None
if config.MONGO_DB_URI and AsyncIOMotorClient is not None:
    try:
        _client = AsyncIOMotorClient(config.MONGO_DB_URI)
        mongodb = _client.MusicFlow
        LOGGER.info("[MUSIC FLOW] Connected to MongoDB database.")
    except Exception as e:
        LOGGER.error(f"[MUSIC FLOW] MongoDB connection failed: {e}")
        mongodb = None

# Resilient in-memory fallback cache
_db_cache = {
    "served_users": set(),
    "served_chats": set(),
    "blacklist_chats": set(),
    "blacklist_users": set(),
    "sudoers": set(config.SUDO_USERS),
    "auth": {},                # chat_id: set(user_ids)
    "language": {},            # chat_id: str
    "loop": {},                # chat_id: int
    "playmode": {},            # chat_id: str
    "cleanmode": {},           # chat_id: bool
    "active_chats": set(),
    "active_video_chats": set(),
    "assistant": {},           # chat_id: int
    "maintenance": False,
    "thumbnail": {},           # chat_id: bool (Default False)
    "global_thumbnail": False, # Global master override (Default False)
    "autoplay": {},            # chat_id: bool (Default False)
}

# -------------------------------------------------------------
# 1. SERVED USERS & CHATS (STATISTICS)
# -------------------------------------------------------------

async def is_served_user(user_id: int) -> bool:
    if mongodb is not None:
        try:
            doc = await mongodb.users.find_one({"user_id": user_id})
            return bool(doc)
        except Exception:
            pass
    return user_id in _db_cache["served_users"]

async def get_served_users() -> List[int]:
    users = set(_db_cache["served_users"])
    if mongodb is not None:
        try:
            async for doc in mongodb.users.find():
                if "user_id" in doc:
                    users.add(doc["user_id"])
        except Exception:
            pass
    return list(users)

async def add_served_user(user_id: int):
    _db_cache["served_users"].add(user_id)
    if mongodb is not None:
        try:
            await mongodb.users.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id}},
                upsert=True
            )
        except Exception:
            pass

async def is_served_chat(chat_id: int) -> bool:
    if mongodb is not None:
        try:
            doc = await mongodb.chats.find_one({"chat_id": chat_id})
            return bool(doc)
        except Exception:
            pass
    return chat_id in _db_cache["served_chats"]

async def get_served_chats() -> List[int]:
    chats = set(_db_cache["served_chats"])
    if mongodb is not None:
        try:
            async for doc in mongodb.chats.find():
                if "chat_id" in doc:
                    chats.add(doc["chat_id"])
        except Exception:
            pass
    return list(chats)

async def add_served_chat(chat_id: int):
    _db_cache["served_chats"].add(chat_id)
    if mongodb is not None:
        try:
            await mongodb.chats.update_one(
                {"chat_id": chat_id},
                {"$set": {"chat_id": chat_id}},
                upsert=True
            )
        except Exception:
            pass

# -------------------------------------------------------------
# 2. BLACKLIST SYSTEM
# -------------------------------------------------------------

async def blacklisted_chats() -> List[int]:
    chats = set(_db_cache["blacklist_chats"])
    if mongodb is not None:
        try:
            async for doc in mongodb.blacklist_chats.find():
                if "chat_id" in doc:
                    chats.add(doc["chat_id"])
        except Exception:
            pass
    return list(chats)

async def blacklist_chat(chat_id: int):
    _db_cache["blacklist_chats"].add(chat_id)
    if mongodb is not None:
        try:
            await mongodb.blacklist_chats.update_one(
                {"chat_id": chat_id},
                {"$set": {"chat_id": chat_id}},
                upsert=True
            )
        except Exception:
            pass

async def whitelist_chat(chat_id: int):
    _db_cache["blacklist_chats"].discard(chat_id)
    if mongodb is not None:
        try:
            await mongodb.blacklist_chats.delete_one({"chat_id": chat_id})
        except Exception:
            pass

async def is_blacklisted_chat(chat_id: int) -> bool:
    if mongodb is not None:
        try:
            doc = await mongodb.blacklist_chats.find_one({"chat_id": chat_id})
            return bool(doc)
        except Exception:
            pass
    return chat_id in _db_cache["blacklist_chats"]

async def blacklisted_users() -> List[int]:
    users = set(_db_cache["blacklist_users"])
    if mongodb is not None:
        try:
            async for doc in mongodb.blacklist_users.find():
                if "user_id" in doc:
                    users.add(doc["user_id"])
        except Exception:
            pass
    return list(users)

async def blacklist_user(user_id: int):
    _db_cache["blacklist_users"].add(user_id)
    if mongodb is not None:
        try:
            await mongodb.blacklist_users.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id}},
                upsert=True
            )
        except Exception:
            pass

async def whitelist_user(user_id: int):
    _db_cache["blacklist_users"].discard(user_id)
    if mongodb is not None:
        try:
            await mongodb.blacklist_users.delete_one({"user_id": user_id})
        except Exception:
            pass

async def is_blacklisted_user(user_id: int) -> bool:
    if mongodb is not None:
        try:
            doc = await mongodb.blacklist_users.find_one({"user_id": user_id})
            return bool(doc)
        except Exception:
            pass
    return user_id in _db_cache["blacklist_users"]

async def is_blacklisted(target_id: int) -> bool:
    """Universal check for chat_id or user_id."""
    return await is_blacklisted_chat(target_id) or await is_blacklisted_user(target_id)

# -------------------------------------------------------------
# 3. SUDOERS SYSTEM
# -------------------------------------------------------------

async def get_sudoers() -> List[int]:
    sudoers = set(config.SUDO_USERS)
    if config.OWNER_ID:
        sudoers.add(config.OWNER_ID)
    if mongodb is not None:
        try:
            async for doc in mongodb.sudoers.find():
                if "user_id" in doc:
                    sudoers.add(doc["user_id"])
        except Exception:
            pass
    sudoers.update(_db_cache["sudoers"])
    return list(sudoers)

async def is_sudo(user_id: int) -> bool:
    if user_id == config.OWNER_ID or user_id in config.SUDO_USERS:
        return True
    if mongodb is not None:
        try:
            doc = await mongodb.sudoers.find_one({"user_id": user_id})
            if doc:
                return True
        except Exception:
            pass
    return user_id in _db_cache["sudoers"]

async def add_sudo(user_id: int):
    _db_cache["sudoers"].add(user_id)
    if mongodb is not None:
        try:
            await mongodb.sudoers.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id}},
                upsert=True
            )
        except Exception:
            pass

async def remove_sudo(user_id: int):
    _db_cache["sudoers"].discard(user_id)
    if mongodb is not None:
        try:
            await mongodb.sudoers.delete_one({"user_id": user_id})
        except Exception:
            pass

# -------------------------------------------------------------
# 4. AUTHORIZED USERS
# -------------------------------------------------------------

async def get_authusers(chat_id: int) -> List[int]:
    users = set(_db_cache["auth"].get(chat_id, set()))
    if mongodb is not None:
        try:
            async for doc in mongodb.auth.find({"chat_id": chat_id}):
                if "user_id" in doc:
                    users.add(doc["user_id"])
        except Exception:
            pass
    return list(users)

async def is_authuser(chat_id: int, user_id: int) -> bool:
    if mongodb is not None:
        try:
            doc = await mongodb.auth.find_one({"chat_id": chat_id, "user_id": user_id})
            if doc:
                return True
        except Exception:
            pass
    return user_id in _db_cache["auth"].get(chat_id, set())

async def add_authuser(chat_id: int, user_id: int):
    _db_cache["auth"].setdefault(chat_id, set()).add(user_id)
    if mongodb is not None:
        try:
            await mongodb.auth.update_one(
                {"chat_id": chat_id, "user_id": user_id},
                {"$set": {"chat_id": chat_id, "user_id": user_id}},
                upsert=True
            )
        except Exception:
            pass

async def remove_authuser(chat_id: int, user_id: int):
    if chat_id in _db_cache["auth"]:
        _db_cache["auth"][chat_id].discard(user_id)
    if mongodb is not None:
        try:
            await mongodb.auth.delete_one({"chat_id": chat_id, "user_id": user_id})
        except Exception:
            pass

# -------------------------------------------------------------
# 5. LANGUAGE SETTINGS
# -------------------------------------------------------------

async def get_lang(chat_id: int) -> str:
    if mongodb is not None:
        try:
            doc = await mongodb.language.find_one({"chat_id": chat_id})
            if doc and "lang" in doc:
                return doc["lang"]
        except Exception:
            pass
    return _db_cache["language"].get(chat_id, "en")

async def set_lang(chat_id: int, lang: str):
    _db_cache["language"][chat_id] = lang
    if mongodb is not None:
        try:
            await mongodb.language.update_one(
                {"chat_id": chat_id},
                {"$set": {"lang": lang}},
                upsert=True
            )
        except Exception:
            pass

# -------------------------------------------------------------
# 6. ACTIVE VOICE CHATS & VIDEO CHATS
# -------------------------------------------------------------

async def get_active_chats() -> List[int]:
    chats = set(_db_cache["active_chats"])
    if mongodb is not None:
        try:
            async for doc in mongodb.active_chats.find():
                if "chat_id" in doc:
                    chats.add(doc["chat_id"])
        except Exception:
            pass
    return list(chats)

async def is_active_chat(chat_id: int) -> bool:
    if mongodb is not None:
        try:
            doc = await mongodb.active_chats.find_one({"chat_id": chat_id})
            return bool(doc)
        except Exception:
            pass
    return chat_id in _db_cache["active_chats"]

async def add_active_chat(chat_id: int):
    _db_cache["active_chats"].add(chat_id)
    if mongodb is not None:
        try:
            await mongodb.active_chats.update_one(
                {"chat_id": chat_id},
                {"$set": {"chat_id": chat_id}},
                upsert=True
            )
        except Exception:
            pass

async def remove_active_chat(chat_id: int):
    _db_cache["active_chats"].discard(chat_id)
    if mongodb is not None:
        try:
            await mongodb.active_chats.delete_one({"chat_id": chat_id})
        except Exception:
            pass

async def get_active_video_chats() -> List[int]:
    chats = set(_db_cache["active_video_chats"])
    if mongodb is not None:
        try:
            async for doc in mongodb.active_video_chats.find():
                if "chat_id" in doc:
                    chats.add(doc["chat_id"])
        except Exception:
            pass
    return list(chats)

async def is_active_video_chat(chat_id: int) -> bool:
    if mongodb is not None:
        try:
            doc = await mongodb.active_video_chats.find_one({"chat_id": chat_id})
            return bool(doc)
        except Exception:
            pass
    return chat_id in _db_cache["active_video_chats"]

async def add_active_video_chat(chat_id: int):
    _db_cache["active_video_chats"].add(chat_id)
    if mongodb is not None:
        try:
            await mongodb.active_video_chats.update_one(
                {"chat_id": chat_id},
                {"$set": {"chat_id": chat_id}},
                upsert=True
            )
        except Exception:
            pass

async def remove_active_video_chat(chat_id: int):
    _db_cache["active_video_chats"].discard(chat_id)
    if mongodb is not None:
        try:
            await mongodb.active_video_chats.delete_one({"chat_id": chat_id})
        except Exception:
            pass

# -------------------------------------------------------------
# 7. PLAYMODE, CLEANMODE & LOOP
# -------------------------------------------------------------

async def get_playmode(chat_id: int) -> str:
    """Returns 'Everyone' or 'Admin'."""
    if mongodb is not None:
        try:
            doc = await mongodb.playmode.find_one({"chat_id": chat_id})
            if doc and "mode" in doc:
                return doc["mode"]
        except Exception:
            pass
    return _db_cache["playmode"].get(chat_id, "Everyone")

async def set_playmode(chat_id: int, mode: str):
    _db_cache["playmode"][chat_id] = mode
    if mongodb is not None:
        try:
            await mongodb.playmode.update_one(
                {"chat_id": chat_id},
                {"$set": {"mode": mode}},
                upsert=True
            )
        except Exception:
            pass

async def is_playmode_admin(chat_id: int) -> bool:
    return (await get_playmode(chat_id)) == "Admin"

async def set_playmode_admin(chat_id: int, is_admin_only: bool):
    await set_playmode(chat_id, "Admin" if is_admin_only else "Everyone")

async def is_cleanmode(chat_id: int) -> bool:
    if mongodb is not None:
        try:
            doc = await mongodb.cleanmode.find_one({"chat_id": chat_id})
            if doc and "status" in doc:
                return doc["status"]
        except Exception:
            pass
    return _db_cache["cleanmode"].get(chat_id, False)

async def set_cleanmode(chat_id: int, status: bool):
    _db_cache["cleanmode"][chat_id] = status
    if mongodb is not None:
        try:
            await mongodb.cleanmode.update_one(
                {"chat_id": chat_id},
                {"$set": {"status": status}},
                upsert=True
            )
        except Exception:
            pass

async def get_loop(chat_id: int) -> int:
    if mongodb is not None:
        try:
            doc = await mongodb.loop.find_one({"chat_id": chat_id})
            if doc and "count" in doc:
                return doc["count"]
        except Exception as e:
            LOGGER.error(f"Error fetching loop setting for {chat_id}: {e}")
    return _db_cache["loop"].get(chat_id, 0)

async def set_loop(chat_id: int, count: int):
    _db_cache["loop"][chat_id] = count
    if mongodb is not None:
        try:
            if count <= 0:
                await mongodb.loop.delete_one({"chat_id": chat_id})
            else:
                await mongodb.loop.update_one(
                    {"chat_id": chat_id},
                    {"$set": {"count": count}},
                    upsert=True
                )
        except Exception as e:
            LOGGER.error(f"Error persisting loop setting for {chat_id}: {e}")
async def get_assistant(chat_id: int) -> int:
    if mongodb is not None:
        try:
            doc = await mongodb.assistants.find_one({"chat_id": chat_id})
            if doc and "assistant" in doc:
                return doc["assistant"]
        except Exception:
            pass
    return _db_cache["assistant"].get(chat_id, 1)

async def set_assistant(chat_id: int, assistant: int):
    _db_cache["assistant"][chat_id] = assistant
    if mongodb is not None:
        try:
            await mongodb.assistants.update_one(
                {"chat_id": chat_id},
                {"$set": {"assistant": assistant}},
                upsert=True
            )
        except Exception:
            pass

async def is_maintenance() -> bool:
    if mongodb is not None:
        try:
            doc = await mongodb.settings.find_one({"setting": "maintenance"})
            if doc and "status" in doc:
                return doc["status"]
        except Exception:
            pass
    return _db_cache["maintenance"]

async def set_maintenance(status: bool):
    _db_cache["maintenance"] = status
    if mongodb is not None:
        try:
            await mongodb.settings.update_one(
                {"setting": "maintenance"},
                {"$set": {"status": status}},
                upsert=True
            )
        except Exception:
            pass

# -------------------------------------------------------------
# 9. MUSIC FLOW NEW SETTINGS: THUMBNAILS & AUTOPLAY
# -------------------------------------------------------------

async def get_thumbnail_setting(chat_id: int) -> bool:
    """Group-specific thumbnail setting. Default is False (OFF)."""
    if mongodb is not None:
        try:
            doc = await mongodb.thumbnail.find_one({"chat_id": chat_id})
            if doc is not None:
                return doc.get("status", False)
        except Exception:
            pass
    return _db_cache["thumbnail"].get(chat_id, False)

async def set_thumbnail_setting(chat_id: int, enabled: bool):
    _db_cache["thumbnail"][chat_id] = enabled
    if mongodb is not None:
        try:
            await mongodb.thumbnail.update_one(
                {"chat_id": chat_id},
                {"$set": {"status": enabled}},
                upsert=True
            )
        except Exception:
            pass

async def get_global_thumbnail_setting() -> bool:
    """Owner master global thumbnail switch. Default is False (OFF)."""
    if mongodb is not None:
        try:
            doc = await mongodb.settings.find_one({"setting": "global_thumbnail"})
            if doc is not None:
                return doc.get("status", False)
        except Exception:
            pass
    return _db_cache["global_thumbnail"]

async def set_global_thumbnail_setting(enabled: bool):
    _db_cache["global_thumbnail"] = enabled
    if mongodb is not None:
        try:
            await mongodb.settings.update_one(
                {"setting": "global_thumbnail"},
                {"$set": {"status": enabled}},
                upsert=True
            )
        except Exception:
            pass

async def should_show_youtube_thumbnail(chat_id: int) -> bool:
    """
    Centralized thumbnail display policy:
    GLOBAL OFF -> No YouTube thumbnails anywhere.
    GLOBAL ON  -> Respects group-specific ON/OFF setting.
    GROUP default -> OFF.
    """
    global_master = await get_global_thumbnail_setting()
    if not global_master:
        return False
    return await get_thumbnail_setting(chat_id)

async def is_autoplay(chat_id: int) -> bool:
    """Group autoplay setting. Default is False (OFF)."""
    if mongodb is not None:
        try:
            doc = await mongodb.autoplay.find_one({"chat_id": chat_id})
            if doc is not None:
                return doc.get("status", False)
        except Exception:
            pass
    return _db_cache["autoplay"].get(chat_id, False)

async def set_autoplay(chat_id: int, status: bool):
    _db_cache["autoplay"][chat_id] = status
    if mongodb is not None:
        try:
            await mongodb.autoplay.update_one(
                {"chat_id": chat_id},
                {"$set": {"status": status}},
                upsert=True
            )
        except Exception:
            pass

# Compatibility aliases
is_thumb_enabled = should_show_youtube_thumbnail
set_thumb = set_thumbnail_setting
set_global_thumb = set_global_thumbnail_setting

# -------------------------------------------------------------
# 10. COMPATIBILITY ALIASES & REPAIR HELPERS (SECTIONS 7, 8)
# -------------------------------------------------------------

get_users = get_served_users
get_chats = get_served_chats
get_blacklisted = blacklisted_chats
get_cmd_delete = is_cleanmode
set_cmd_delete = set_cleanmode
get_play_mode = get_playmode
set_play_mode = set_playmode

async def get_logger(chat_id: int) -> bool:
    if mongodb is not None:
        try:
            doc = await mongodb.logger.find_one({"chat_id": chat_id})
            if doc:
                return doc.get("status", True)
        except Exception:
            pass
    return True

async def set_logger(chat_id: int, status: bool):
    if mongodb is not None:
        try:
            await mongodb.logger.update_one(
                {"chat_id": chat_id},
                {"$set": {"status": status}},
                upsert=True
            )
        except Exception:
            pass

async def load_cache():
    """Pre-loads critical database caches during startup for zero-latency lookups."""
    if mongodb is None:
        return
    try:
        async for doc in mongodb.settings.find():
            setting = doc.get("setting")
            if setting == "global_thumbnail":
                _db_cache["global_thumbnail"] = doc.get("status", False)
            elif setting == "maintenance":
                _db_cache["maintenance"] = doc.get("status", False)
        async for doc in mongodb.sudoers.find():
            if "user_id" in doc:
                _db_cache["sudoers"].add(doc["user_id"])
        async for doc in mongodb.blacklist_chats.find():
            if "chat_id" in doc:
                _db_cache["blacklist_chats"].add(doc["chat_id"])
        async for doc in mongodb.blacklist_users.find():
            if "user_id" in doc:
                _db_cache["blacklist_users"].add(doc["user_id"])
        async for doc in mongodb.autoplay.find():
            if "chat_id" in doc and "status" in doc:
                _db_cache["autoplay"][doc["chat_id"]] = doc["status"]
        async for doc in mongodb.thumbnail.find():
            if "chat_id" in doc and "status" in doc:
                _db_cache["thumbnail"][doc["chat_id"]] = doc["status"]
        async for doc in mongodb.language.find():
            if "chat_id" in doc and "lang" in doc:
                _db_cache["language"][doc["chat_id"]] = doc["lang"]
        async for doc in mongodb.loop.find():
            if "chat_id" in doc and "count" in doc:
                _db_cache["loop"][doc["chat_id"]] = doc["count"]
        async for doc in mongodb.cleanmode.find():
            if "chat_id" in doc and "status" in doc:
                _db_cache["cleanmode"][doc["chat_id"]] = doc["status"]
        async for doc in mongodb.playmode.find():
            if "chat_id" in doc and "mode" in doc:
                _db_cache["playmode"][doc["chat_id"]] = doc["mode"]
        LOGGER.info("[MUSIC FLOW] MongoDB cache pre-loaded successfully.")
    except Exception as e:
        LOGGER.error(f"Error pre-loading MongoDB cache: {e}")

async def migrate_coll():
    if mongodb is None:
        return
    try:
        await mongodb.users.create_index("user_id", unique=True)
        await mongodb.chats.create_index("chat_id", unique=True)
        await mongodb.blacklist_chats.create_index("chat_id", unique=True)
        await mongodb.sudoers.create_index("user_id", unique=True)
    except Exception:
        pass

unblacklist_chat = whitelist_chat
unblacklist_user = whitelist_user
