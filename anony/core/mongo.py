# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


from random import randint
from time import time

from pymongo import AsyncMongoClient

from anony import config, logger


class MongoDB:
    def __init__(self):
        """
        Initialize the MongoDB connection.
        """
        # Do not create AsyncMongoClient during module import.  The bot is
        # started with asyncio.run(), which creates the real application
        # event loop only after imports have completed.  Creating the async
        # Mongo client here can bind internal futures to a different loop
        # and later produce: "Future ... attached to a different loop".
        self.mongo = None
        self.db = None

        self.admin_list = {}
        self.active_calls = {}
        self.admin_play = []
        self.autoplay = []
        self.bass: dict[int, int] = {}
        self.thumbnail_gen: dict[int, bool] = {}
        self.blacklisted = []
        self.cmd_delete = []
        self.loop = {}
        self.notified = []
        self.cache = None
        self.logger = False

        self.assistant = {}
        self.assistantdb = None

        self.auth = {}
        self.authdb = None

        self.chats = []
        self.chatsdb = None

        self.lang = {}
        self.langdb = None

        self.users = []
        self.usersdb = None

    async def connect(self) -> None:
        """Check if we can connect to the database.

        The async client and collection handles are created here, while
        ``asyncio.run(main())`` is already executing on the application's
        event loop.  This prevents cross-event-loop futures.

        Raises:
            SystemExit: If the connection to the database fails.
        """
        try:
            # AsyncMongoClient must be created inside the running loop.
            if self.mongo is None:
                self.mongo = AsyncMongoClient(
                    config.MONGO_URL,
                    serverSelectionTimeoutMS=10000,
                    connectTimeoutMS=5000,
                    socketTimeoutMS=10000,
                    maxPoolSize=20,
                    minPoolSize=0,
                    maxConnecting=2,
                    retryWrites=True,
                )
                self.db = self.mongo.Anon
                self.cache = self.db.cache
                self.assistantdb = self.db.assistant
                self.authdb = self.db.auth
                self.chatsdb = self.db.chats
                self.langdb = self.db.lang
                self.usersdb = self.db.users

            start = time()
            await self.mongo.admin.command("ping")
            logger.info(f"Database connection successful. ({time() - start:.2f}s)")
            await self.load_cache()
        except Exception as e:
            raise SystemExit(f"Database connection failed: {type(e).__name__}") from e

    async def close(self) -> None:
        """Close the connection to the database."""
        if self.mongo is not None:
            await self.mongo.close()
            self.mongo = None
        logger.info("Database connection closed.")

    # CACHE
    async def get_call(self, chat_id: int) -> bool:
        return chat_id in self.active_calls

    async def add_call(self, chat_id: int) -> None:
        self.active_calls[chat_id] = 1

    async def remove_call(self, chat_id: int) -> None:
        self.active_calls.pop(chat_id, None)

    async def playing(self, chat_id: int, paused: bool = None) -> bool | None:
        if paused is not None:
            self.active_calls[chat_id] = int(not paused)
        return bool(self.active_calls.get(chat_id, 0))

    async def get_admins(self, chat_id: int, reload: bool = False) -> list[int]:
        from anony.helpers._admins import reload_admins

        if chat_id not in self.admin_list or reload:
            admins = await reload_admins(chat_id)
            if admins is None:
                # Transient fetch failure: keep the previous cached value
                # (if any) instead of caching an empty "zero admins" result.
                return self.admin_list.get(chat_id, [])
            self.admin_list[chat_id] = admins
        return self.admin_list[chat_id]

    async def get_loop(self, chat_id: int) -> int:
        return self.loop.get(chat_id, 0)

    async def set_loop(self, chat_id: int, count: int) -> None:
        self.loop[chat_id] = count

    # AUTH METHODS
    async def _get_auth(self, chat_id: int) -> set[int]:
        if chat_id not in self.auth:
            doc = await self.authdb.find_one({"_id": chat_id}) or {}
            self.auth[chat_id] = set(doc.get("user_ids", []))
        return self.auth[chat_id]

    async def is_auth(self, chat_id: int, user_id: int) -> bool:
        return user_id in await self._get_auth(chat_id)

    async def add_auth(self, chat_id: int, user_id: int) -> None:
        users = await self._get_auth(chat_id)
        if user_id not in users:
            users.add(user_id)
            await self.authdb.update_one(
                {"_id": chat_id}, {"$addToSet": {"user_ids": user_id}}, upsert=True
            )

    async def rm_auth(self, chat_id: int, user_id: int) -> None:
        users = await self._get_auth(chat_id)
        if user_id in users:
            users.discard(user_id)
            await self.authdb.update_one(
                {"_id": chat_id}, {"$pull": {"user_ids": user_id}}
            )

    # ASSISTANT METHODS
    async def set_assistant(self, chat_id: int) -> int:
        from anony import userbot
        if not userbot.clients:
            raise RuntimeError("No assistant clients are running")
        num = randint(1, len(userbot.clients))
        await self.assistantdb.update_one(
            {"_id": chat_id}, {"$set": {"num": num}}, upsert=True
        )
        self.assistant[chat_id] = num
        return num

    async def get_assistant_num(self, chat_id: int, total_assistants: int | None = None) -> int:
        from anony import userbot
        total = total_assistants or len(userbot.clients)
        if total <= 0:
            raise RuntimeError("No assistant clients are running")

        num = self.assistant.get(chat_id)
        if num is None:
            doc = await self.assistantdb.find_one({"_id": chat_id})
            num = doc.get("num") if doc else None
        if not num or num > total:
            num = randint(1, total)
            await self.assistantdb.update_one(
                {"_id": chat_id}, {"$set": {"num": num}}, upsert=True
            )
        self.assistant[chat_id] = num
        return num

    async def get_assistant(self, chat_id: int):
        from anony import userbot
        num = await self.get_assistant_num(chat_id, len(userbot.clients))
        return userbot.clients[num - 1]

    async def get_client(self, chat_id: int):
        return await self.get_assistant(chat_id)

    # BLACKLIST METHODS
    async def add_blacklist(self, chat_id: int) -> None:
        if str(chat_id).startswith("-"):
            self.blacklisted.append(chat_id)
            return await self.cache.update_one(
                {"_id": "bl_chats"},
                {"$addToSet": {"chat_ids": chat_id}},
                upsert=True,
            )
        await self.cache.update_one(
            {"_id": "bl_users"},
            {"$addToSet": {"user_ids": chat_id}},
            upsert=True,
        )

    async def del_blacklist(self, chat_id: int) -> None:
        if str(chat_id).startswith("-"):
            self.blacklisted.remove(chat_id) if chat_id in self.blacklisted else None
            return await self.cache.update_one(
                {"_id": "bl_chats"},
                {"$pull": {"chat_ids": chat_id}},
            )
        await self.cache.update_one(
            {"_id": "bl_users"},
            {"$pull": {"user_ids": chat_id}},
        )

    async def get_blacklisted(self, chat: bool = False, reload: bool = False) -> list[int]:
        if chat:
            if not self.blacklisted or reload:
                doc = await self.cache.find_one({"_id": "bl_chats"})
                self.blacklisted = doc.get("chat_ids", []) if doc else []
            return self.blacklisted
        doc = await self.cache.find_one({"_id": "bl_users"})
        return doc.get("user_ids", []) if doc else []

    # CHAT METHODS
    async def is_chat(self, chat_id: int) -> bool:
        return chat_id in self.chats

    async def add_chat(self, chat_id: int) -> None:
        if not await self.is_chat(chat_id):
            self.chats.append(chat_id)
            await self.chatsdb.insert_one({"_id": chat_id})

    async def rm_chat(self, chat_id: int) -> None:
        if chat_id in self.chats:
            self.chats.remove(chat_id)
        # Always attempt the DB delete, even if this chat isn't in the
        # in-memory cache, so rm_chat can't silently no-op.
        await self.chatsdb.delete_one({"_id": chat_id})

    async def get_chats(self, reload: bool = False) -> list:
        if not self.chats or reload:
            self.chats = [chat["_id"] async for chat in self.chatsdb.find()]
        return self.chats

    # COMMAND DELETE
    async def get_cmd_delete(self, chat_id: int) -> bool:
        if chat_id not in self.cmd_delete:
            doc = await self.chatsdb.find_one({"_id": chat_id})
            if doc and doc.get("cmd_delete"):
                self.cmd_delete.append(chat_id)
        return chat_id in self.cmd_delete

    async def set_cmd_delete(self, chat_id: int, delete: bool = False) -> None:
        if delete:
            if chat_id not in self.cmd_delete:
                self.cmd_delete.append(chat_id)
        elif chat_id in self.cmd_delete:
            self.cmd_delete.remove(chat_id)
        await self.chatsdb.update_one(
            {"_id": chat_id},
            {"$set": {"cmd_delete": delete}},
            upsert=True,
        )

    # LANGUAGE METHODS
    async def set_lang(self, chat_id: int, lang_code: str):
        await self.langdb.update_one(
            {"_id": chat_id},
            {"$set": {"lang": lang_code}},
            upsert=True,
        )
        self.lang[chat_id] = lang_code

    async def get_lang(self, chat_id: int) -> str:
        if chat_id not in self.lang:
            doc = await self.langdb.find_one({"_id": chat_id})
            self.lang[chat_id] = doc["lang"] if doc else config.LANG_CODE
        return self.lang[chat_id]

    # LOGGER METHODS
    async def is_logger(self) -> bool:
        return self.logger

    async def get_logger(self) -> bool:
        doc = await self.cache.find_one({"_id": "logger"})
        if doc:
            self.logger = doc["status"]
        return self.logger

    async def set_logger(self, status: bool) -> None:
        self.logger = status
        await self.cache.update_one(
            {"_id": "logger"},
            {"$set": {"status": status}},
            upsert=True,
        )

    # PLAY MODE METHODS
    async def get_play_mode(self, chat_id: int) -> bool:
        if chat_id not in self.admin_play:
            doc = await self.chatsdb.find_one({"_id": chat_id})
            if doc and doc.get("admin_play"):
                self.admin_play.append(chat_id)
        return chat_id in self.admin_play

    async def set_play_mode(self, chat_id: int, remove: bool = False) -> None:
        if remove:
            if chat_id in self.admin_play:
                self.admin_play.remove(chat_id)
        elif chat_id not in self.admin_play:
            self.admin_play.append(chat_id)
        await self.chatsdb.update_one(
            {"_id": chat_id},
            {"$set": {"admin_play": not remove}},
            upsert=True,
        )

    # AUTOPLAY METHODS
    async def get_autoplay(self, chat_id: int) -> bool:
        if chat_id not in self.autoplay:
            doc = await self.chatsdb.find_one({"_id": chat_id})
            if doc and doc.get("autoplay"):
                self.autoplay.append(chat_id)
        return chat_id in self.autoplay

    async def set_autoplay(self, chat_id: int, enable: bool) -> None:
        if enable and chat_id not in self.autoplay:
            self.autoplay.append(chat_id)
        elif not enable and chat_id in self.autoplay:
            self.autoplay.remove(chat_id)
        await self.chatsdb.update_one(
            {"_id": chat_id}, {"$set": {"autoplay": enable}}, upsert=True
        )

    # BASS BOOST METHODS
    async def get_bass(self, chat_id: int) -> int:
        if chat_id not in self.bass:
            doc = await self.chatsdb.find_one({"_id": chat_id})
            self.bass[chat_id] = (doc.get("bass") or 0) if doc else 0
        return self.bass[chat_id]

    async def set_bass(self, chat_id: int, level: int) -> None:
        self.bass[chat_id] = level
        await self.chatsdb.update_one(
            {"_id": chat_id}, {"$set": {"bass": level}}, upsert=True
        )

    # THUMBNAIL GENERATION (per-group, OFF by default)
    async def get_thumbnail_gen(self, chat_id: int) -> bool:
        if chat_id not in self.thumbnail_gen:
            doc = await self.chatsdb.find_one({"_id": chat_id}, {"thumbnail_gen": 1})
            self.thumbnail_gen[chat_id] = bool(doc.get("thumbnail_gen", False)) if doc else False
        return self.thumbnail_gen[chat_id]

    async def set_thumbnail_gen(self, chat_id: int, enabled: bool) -> None:
        enabled = bool(enabled)
        self.thumbnail_gen[chat_id] = enabled
        await self.chatsdb.update_one(
            {"_id": chat_id},
            {"$set": {"thumbnail_gen": enabled}},
            upsert=True,
        )

    # AUTOPLAY HISTORY (persisted so a restart doesn't erase what autoplay
    # has already played per chat, otherwise it can immediately re-suggest
    # a track that was just played before the restart)
    async def get_autoplay_history(self, chat_id: int) -> list[str]:
        doc = await self.chatsdb.find_one({"_id": chat_id})
        return (doc.get("history") or []) if doc else []

    async def add_autoplay_history(self, chat_id: int, track_id: str) -> None:
        if not track_id:
            return
        await self.chatsdb.update_one(
            {"_id": chat_id},
            {"$push": {"history": {"$each": [track_id], "$slice": -50}}},
            upsert=True,
        )

    async def clear_autoplay_history(self, chat_id: int) -> None:
        await self.chatsdb.update_one(
            {"_id": chat_id}, {"$set": {"history": []}}, upsert=True
        )

    # SUDO METHODS
    async def add_sudo(self, user_id: int) -> None:
        await self.cache.update_one(
            {"_id": "sudoers"}, {"$addToSet": {"user_ids": user_id}}, upsert=True
        )

    async def del_sudo(self, user_id: int) -> None:
        await self.cache.update_one(
            {"_id": "sudoers"}, {"$pull": {"user_ids": user_id}}
        )

    async def get_sudoers(self) -> list[int]:
        doc = await self.cache.find_one({"_id": "sudoers"})
        return doc.get("user_ids", []) if doc else []

    # USER METHODS
    async def is_user(self, user_id: int) -> bool:
        return user_id in self.users

    async def add_user(self, user_id: int) -> None:
        if not await self.is_user(user_id):
            self.users.append(user_id)
            await self.usersdb.insert_one({"_id": user_id})

    async def rm_user(self, user_id: int) -> None:
        if user_id in self.users:
            self.users.remove(user_id)
        # Always attempt the DB delete, even if the in-memory cache never
        # saw this user (e.g. it was added by another process/instance),
        # so rm_user can't silently no-op.
        await self.usersdb.delete_one({"_id": user_id})

    async def get_users(self, reload: bool = False) -> list:
        if not self.users or reload:
            self.users = [user["_id"] async for user in self.usersdb.find()]
        return self.users


    async def migrate_coll(self) -> None:
        logger.info("Migrating users and chats from old collections...")

        users, musers, mchats = [], [], []
        seen_chats, seen_users = set(), set()
        users.extend([user async for user in self.usersdb.find()])
        users.extend([user async for user in self.db.tgusersdb.find()])

        for user in users:
            _id = user.get("_id")
            try:
                if isinstance(_id, int):
                    user_id = _id
                else:
                    user_id = int(user.get("user_id"))
            except (TypeError, ValueError):
                logger.warning(f"Skipping malformed user document during migration: {user!r}")
                continue

            if user_id in seen_users:
                continue
            seen_users.add(user_id)
            # Preserve any extra fields already present on the document
            # instead of collapsing it down to just "_id".
            doc = dict(user)
            doc["_id"] = user_id
            doc.pop("user_id", None)
            musers.append(doc)

        await self.usersdb.drop()
        await self.db.tgusersdb.drop()
        if musers:
            await self.usersdb.insert_many(musers)

        async for chat in self.chatsdb.find():
            _id = chat.get("_id")
            try:
                if isinstance(_id, int):
                    chat_id = _id
                else:
                    chat_id = int(chat.get("chat_id"))
            except (TypeError, ValueError):
                logger.warning(f"Skipping malformed chat document during migration: {chat!r}")
                continue

            if chat_id in seen_chats:
                continue
            seen_chats.add(chat_id)
            # Preserve any extra fields (cmd_delete, admin_play, autoplay,
            # etc.) instead of wiping them by reinserting with only "_id".
            doc = dict(chat)
            doc["_id"] = chat_id
            doc.pop("chat_id", None)
            mchats.append(doc)

        await self.chatsdb.drop()
        if mchats:
            await self.chatsdb.insert_many(mchats)

        await self.cache.insert_one({"_id": "migrated"})
        logger.info("Migration completed successfully.")

    async def load_cache(self) -> None:
        doc = await self.cache.find_one({"_id": "migrated"})
        if not doc:
            await self.migrate_coll()

        await self.get_chats()
        await self.get_users()
        await self.get_blacklisted(True)
        await self.get_logger()
        logger.info("Database cache loaded.")
