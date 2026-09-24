import logging
import config

LOGGER = logging.getLogger("MusicFlow.Bot")

try:
    from pyrogram import Client
    class MusicBot(Client):
        def __init__(self):
            super().__init__(
                name="MusicFlowBot",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                bot_token=config.BOT_TOKEN,
            )

        async def start(self):
            await super().start()
            get_me = await self.get_me()
            self.username = get_me.username
            self.id = get_me.id
            self.name = get_me.first_name
            config.BOT_USERNAME = get_me.username
            LOGGER.info(f"[MUSIC FLOW] Bot started as @{self.username} (ID: {self.id})")

        async def stop(self):
            await super().stop()
            LOGGER.info("[MUSIC FLOW] Bot stopped.")

    Bot = MusicBot()
except ImportError:
    class MockBot:
        def __init__(self):
            self.name = "MusicFlowBot"
            self.username = "MusicFlowBot"
            self.id = 123456789
            self.first_name = "MUSIC FLOW"
        async def start(self):
            pass
        async def stop(self):
            pass
        async def get_me(self):
            return self
        def on_message(self, *args, **kwargs):
            return lambda f: f
        def on_callback_query(self, *args, **kwargs):
            return lambda f: f
        def on_inline_query(self, *args, **kwargs):
            return lambda f: f
    Bot = MockBot()
