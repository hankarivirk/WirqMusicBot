from pyrogram import Client
from wirq import config, logger

class Userbot(Client):
    def __init__(self):
        self.clients = []
        clients_map = {"one": "SESSION1", "two": "SESSION2", "three": "SESSION3"}
        for key, string_key in clients_map.items():
            session = getattr(config, string_key, None)
            if session:
                setattr(
                    self,
                    key,
                    Client(
                        name=f"AnonyUB{key.capitalize()}",
                        api_id=config.API_ID,
                        api_hash=config.API_HASH,
                        session_string=session,
                    ),
                )
            else:
                setattr(self, key, None)

    async def boot_client(self, num: int, client: Client):
        if not client:
            return
        await client.start()
        me = client.me
        client.id = me.id
        client.name = me.first_name
        client.username = me.username
        client.mention = me.mention
        self.clients.append(client)
        try:
            await client.send_message(config.LOGGER_ID, f"Assistant {num} Started Successfully")
        except Exception:
            pass
        logger.info(f"Assistant {num} started as @{client.username}")

    async def boot(self):
        if getattr(self, "one", None):
            await self.boot_client(1, self.one)
        if getattr(self, "two", None):
            await self.boot_client(2, self.two)
        if getattr(self, "three", None):
            await self.boot_client(3, self.three)

    async def exit(self):
        for c in self.clients:
            try:
                await c.stop()
            except Exception:
                pass
        logger.info("Assistants stopped.")
