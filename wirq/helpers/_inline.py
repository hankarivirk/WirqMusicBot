# Wirq Music Bot - Inline Keyboard Manager
# Bot Name: Wirq Music Bot
# Owner: @wirq4 | Support: @wirqbots | GitHub: Hankarivirk/WirqMusicbot

from typing import List, Optional
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import Config

config = Config()

class Inline:
    def __init__(self):
        self.ikm = InlineKeyboardMarkup
        self.ikb = InlineKeyboardButton

    def controls(
        self,
        chat_id: int,
        status: Optional[str] = None,
        timer: Optional[str] = None,
        is_paused: bool = False,
    ) -> InlineKeyboardMarkup:
        keyboard = []
        top_bar = status or timer
        if top_bar:
            keyboard.append([self.ikb(text=top_bar, callback_data=f"controls status {chat_id}")])

        play_pause_btn = (
            self.ikb("▷ Resume", callback_data=f"controls resume {chat_id}")
            if is_paused
            else self.ikb("II Pause", callback_data=f"controls pause {chat_id}")
        )

        keyboard.extend([
            [
                self.ikb("⏮ Prev", callback_data=f"controls replay {chat_id}"),
                play_pause_btn,
                self.ikb("⏭ Skip", callback_data=f"controls skip {chat_id}"),
                self.ikb("⏹ Stop", callback_data=f"controls stop {chat_id}"),
            ],
            [
                self.ikb("🔁 Loop", callback_data=f"controls loop {chat_id}"),
                self.ikb("🔀 Shuffle", callback_data=f"controls shuffle {chat_id}"),
                self.ikb("📋 Queue", callback_data=f"queue_{chat_id}"),
                self.ikb("🔊 Vol", callback_data=f"controls volume_menu {chat_id}"),
            ],
            [
                self.ikb("⚡ Autoplay", callback_data=f"controls autoplay {chat_id}"),
                self.ikb("🚪 Leave", callback_data=f"controls leave {chat_id}"),
            ],
            [
                self.ikb("📢 Support Channel", url=config.SUPPORT_CHANNEL),
                self.ikb("💬 Support Group", url=config.SUPPORT_CHAT),
            ]
        ])
        return self.ikm(keyboard)

    def start_markup(self, bot_username: str = "") -> InlineKeyboardMarkup:
        add_url = f"https://t.me/{bot_username}?startgroup=true" if bot_username else "https://t.me/wirqbots"
        return self.ikm([
            [
                self.ikb("➕ Add Me to Your Group ➕", url=add_url),
            ],
            [
                self.ikb("▶️ Play", callback_data="help_play"),
                self.ikb("🎥 Video Play", callback_data="help_vplay"),
            ],
            [
                self.ikb("📚 Help & Commands", callback_data="help_menu"),
                self.ikb("⚙️ Settings", callback_data="settings_menu"),
            ],
            [
                self.ikb("📢 Channel", url=config.SUPPORT_CHANNEL),
                self.ikb("🐙 GitHub", url=config.GITHUB_REPO),
            ]
        ])

    def help_markup(self) -> InlineKeyboardMarkup:
        return self.ikm([
            [
                self.ikb("🎵 Playback", callback_data="help_play"),
                self.ikb("🛡️ Admins", callback_data="help_admin"),
            ],
            [
                self.ikb("🔁 Loop & Autoplay", callback_data="help_loop"),
                self.ikb("⚙️ Settings", callback_data="settings_menu"),
            ],
            [
                self.ikb("❌ Close Menu", callback_data="close_btn"),
            ]
        ])

    def search_markup(self, results: list, chat_id: int) -> InlineKeyboardMarkup:
        buttons = []
        for idx, item in enumerate(results[:5], 1):
            vid = item.get("id")
            title = (item.get("title") or "Track")[:38]
            dur = item.get("duration") or ""
            dur_str = f" ({dur})" if dur else ""
            buttons.append([
                self.ikb(f"{idx}. {title}{dur_str}", callback_data=f"search_play {chat_id} {vid}")
            ])
        buttons.append([self.ikb("❌ Cancel Search", callback_data="close_btn")])
        return self.ikm(buttons)

    def recommend_markup(self, tracks: list, more_str: str = "🔄 More Recommendations") -> InlineKeyboardMarkup:
        buttons = []
        for t in tracks[:3]:
            vid = t.get("id") if isinstance(t, dict) else getattr(t, "id", "")
            title = t.get("title") if isinstance(t, dict) else getattr(t, "title", "Track")
            dur = t.get("duration") if isinstance(t, dict) else getattr(t, "duration", "")
            dur_str = f" [{dur}]" if dur else ""
            display = f"▶️ {title[:32]}{dur_str}"
            buttons.append([self.ikb(display, callback_data=f"play_rec_{vid}")])
        buttons.append([self.ikb(more_str, callback_data="recommend_more")])
        buttons.append([self.ikb("❌ Close", callback_data="close_btn")])
        return self.ikm(buttons)

    def lang_markup(self, current: str) -> InlineKeyboardMarkup:
        languages = [
            ("English 🇬🇧", "en"),
            ("हिन्दी 🇮🇳", "hi"),
            ("ਪੰਜਾਬੀ 🇮🇳", "pa"),
        ]
        buttons = []
        row = []
        for name, code in languages:
            tag = "✅ " if code == current else ""
            row.append(self.ikb(f"{tag}{name}", callback_data=f"lang_{code}"))
        buttons.append(row)
        buttons.append([self.ikb("❌ Close", callback_data="close_btn")])
        return self.ikm(buttons)

    def volume_markup(self, chat_id: int, current_vol: int) -> InlineKeyboardMarkup:
        return self.ikm([
            [
                self.ikb("🔈 25%", callback_data=f"set_vol {chat_id} 25"),
                self.ikb("🔉 50%", callback_data=f"set_vol {chat_id} 50"),
                self.ikb("🔊 75%", callback_data=f"set_vol {chat_id} 75"),
                self.ikb("📢 100%", callback_data=f"set_vol {chat_id} 100"),
            ],
            [
                self.ikb("🔙 Back to Player", callback_data=f"controls back {chat_id}"),
                self.ikb("❌ Close", callback_data="close_btn"),
            ]
        ])

buttons = Inline()
