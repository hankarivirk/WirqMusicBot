from pyrogram import Client
import config

class Userbot:
    def __init__(self):
        self.clients = []
        sessions = [
            config.STRING_SESSION,
            config.STRING_SESSION2,
            config.STRING_SESSION3,
            config.STRING_SESSION4,
            config.STRING_SESSION5,
        ]
        for i, s in enumerate(sessions, start=1):
            if s and s.strip():
                cli = Client(
                    name=f"MusicFlowAssistant{i}",
                    api_id=config.API_ID,
                    api_hash=config.API_HASH,
                    session_string=s.strip(),
                )
                self.clients.append(cli)

    @property
    def one(self):
        return self.clients[0] if self.clients else None

    async def start(self):
        for i, cli in enumerate(self.clients, start=1):
            try:
                await cli.start()
                me = await cli.get_me()
                print(f"[Music Flow] Assistant {i} started as @{me.username} (ID: {me.id})")
            except Exception as e:
                print(f"[Music Flow] Error starting Assistant {i}: {e}")

    async def stop(self):
        for cli in self.clients:
            try:
                await cli.stop()
            except Exception:
                pass

userbot = Userbot()
