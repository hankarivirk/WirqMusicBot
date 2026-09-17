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

    async def _send_startup_message(self, chat_id: int, message: str, target: str) -> bool:
        """Send a startup message without allowing a bad optional chat to stop boot."""
        if not chat_id:
            logger.warning(f"{target} ID is not configured; skipping startup message.")
            return False
        try:
            await self.send_message(chat_id, message)
            return True
        except Exception as ex:
            logger.warning(f"Failed to send startup message to {target} {chat_id}: {ex}")
            return False

    async def boot(self):
        await super().start()
        self.id = self.me.id
        self.name = self.me.first_name
        self.username = self.me.username
        self.mention = self.me.mention

        # LOGGER_ID is optional. An invalid or inaccessible logger must never
        # prevent the bot from starting.
        logger_message_sent = await self._send_startup_message(
            self.logger,
            "<b>WirqMusic Bot Started Successfully</b>",
            "logger group",
        )
        if logger_message_sent:
            try:
                member = await self.get_chat_member(self.logger, self.id)
                if member.status != ChatMemberStatus.ADMINISTRATOR:
                    logger.warning("Please promote the bot to Administrator in your logger group.")
            except Exception as ex:
                logger.warning(f"Failed to check logger group permissions: {ex}")

        # Always notify the owner independently of LOGGER_ID.
        await self._send_startup_message(
            self.owner,
            (
                "<b>✅ WirqMusic Bot started</b>\n\n"
                f"Bot: @{self.username}\n"
                f"Logger notifications: {'enabled' if logger_message_sent else 'unavailable'}"
            ),
            "owner",
        )
        logger.info(f"Bot started as @{self.username}")

    async def exit(self):
        await super().stop()
        logger.info("Bot stopped.")
