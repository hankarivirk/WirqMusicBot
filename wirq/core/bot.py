import pyrogram
from pyrogram.enums import ParseMode, ChatMemberStatus
from wirq import config, logger

class Bot(pyrogram.Client):
    def __init__(self):
        super().__init__(
            name="wirq",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            parse_mode=ParseMode.HTML,
            max_concurrent_transmissions=7,
        )
        self.owner = config.OWNER_ID
        self.logger = config.LOGGER_ID
        self.bl_users = pyrogram.filters.user()
        self.sudoers = pyrogram.filters.user(self.owner)

    async def boot(self):
        await super().start()
        self.id = self.me.id
        self.name = self.me.first_name
        self.username = self.me.username
        self.mention = self.me.mention
        try:
            await self.send_message(self.logger, "<b>WirqMusic Bot Started Successfully</b>")
            member = await self.get_chat_member(self.logger, self.id)
            if member.status != ChatMemberStatus.ADMINISTRATOR:
                logger.warning("Please promote the bot to Administrator in your logger group.")
        except Exception as ex:
            logger.warning(f"Failed to access logger group: {ex}")
        logger.info(f"Bot started as @{self.username}")

    async def exit(self):
        await super().stop()
        logger.info("Bot stopped.")
