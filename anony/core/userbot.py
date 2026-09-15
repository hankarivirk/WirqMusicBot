from pyrogram import Client
from anony import config, logger


class Userbot:
    """Owns up to five assistant Pyrogram clients."""

    def __init__(self):
        self.clients = []
        self._all = []
        sessions = [
            ("one", config.SESSION1),
            ("two", config.SESSION2),
            ("three", config.SESSION3),
            ("four", config.SESSION4),
            ("five", config.SESSION5),
        ]
        for index, (key, session) in enumerate(sessions[:config.MAX_ASSISTANTS], 1):
            client = Client(
                name=f"WirqUB{index}",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                session_string=session,
            )
            setattr(self, key, client)
            self._all.append((index, client, session))

    async def _boot_one(self, index: int, client: Client):
        await client.start()
        try:
            await client.send_message(config.LOGGER_ID, f"Assistant {index} Started")
        except Exception as exc:
            await client.stop()
            raise SystemExit(
                f"Assistant {index} failed to send message in logger group: {exc}"
            )

        client.id = client.me.id
        client.name = client.me.first_name
        client.username = client.me.username
        client.mention = client.me.mention
        self.clients.append(client)

        try:
            await client.join_chat("fallenx")
        except Exception:
            pass

        logger.info("Assistant %s started as @%s", index, client.username)

    async def boot(self):
        for index, client, session in self._all:
            if session:
                try:
                    await self._boot_one(index, client)
                except Exception as exc:
                    logger.exception("Assistant %s failed to start: %s", index, exc)

        if not self.clients:
            raise SystemExit("No assistant session could be started.")

    async def exit(self):
        for _, client, session in self._all:
            if session:
                try:
                    await client.stop()
                except Exception:
                    logger.debug("Assistant stop failed", exc_info=True)
        self.clients.clear()
        logger.info("Assistants stopped.")
