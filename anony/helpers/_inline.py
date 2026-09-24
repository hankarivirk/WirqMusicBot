from typing import List, Dict, Any, Optional
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import config

# -------------------------------------------------------------
# 1. START PANELS (SECTIONS 3, 4, 5, 61, 72)
# -------------------------------------------------------------

def start_private_markup() -> InlineKeyboardMarkup:
    bot_user = config.BOT_USERNAME or "MusicFlowBot"
    buttons = [
        [
            InlineKeyboardButton(text="Play", switch_inline_query_current_chat=""),
            InlineKeyboardButton(text="Search", switch_inline_query_current_chat=""),
            InlineKeyboardButton(text="Queue", callback_data="btn_queue"),
            InlineKeyboardButton(text="Settings", callback_data="btn_settings"),
        ],
        [
            InlineKeyboardButton(text="Help", callback_data="help_main"),
            InlineKeyboardButton(text="Language", callback_data="settings_lang"),
        ]
    ]
    if config.OWNER_URL and config.OWNER_URL.strip():
        buttons.append([
            InlineKeyboardButton(text="Owner", url=config.OWNER_URL.strip())
        ])
    return InlineKeyboardMarkup(buttons)

def start_group_markup(chat_id: Optional[int] = None) -> InlineKeyboardMarkup:
    c_id = chat_id or 0
    buttons = [
        [
            InlineKeyboardButton(text="Play", switch_inline_query_current_chat=""),
            InlineKeyboardButton(text="Queue", callback_data=f"panel_queue_{c_id}"),
            InlineKeyboardButton(text="Controls", callback_data=f"panel_controls_{c_id}"),
        ],
        [
            InlineKeyboardButton(text="Settings", callback_data=f"btn_settings_{c_id}"),
            InlineKeyboardButton(text="Help", callback_data="help_main"),
        ]
    ]
    if config.OWNER_URL and config.OWNER_URL.strip():
        buttons.append([
            InlineKeyboardButton(text="Owner", url=config.OWNER_URL.strip())
        ])
    return InlineKeyboardMarkup(buttons)

def simple_start_markup() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Play", switch_inline_query_current_chat=""),
            InlineKeyboardButton(text="Search", switch_inline_query_current_chat=""),
            InlineKeyboardButton(text="Queue", callback_data="btn_queue"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)

# -------------------------------------------------------------
# 2. PLAYER CONTROLS (SECTIONS 10, 56, 72, 73)
# FROZEN ROW 1: ▷ II ⥁ ‣‣I ▢
# -------------------------------------------------------------

def stream_markup(chat_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="▷", callback_data=f"panel_resume_{chat_id}"),
            InlineKeyboardButton(text="II", callback_data=f"panel_pause_{chat_id}"),
            InlineKeyboardButton(text="⥁", callback_data=f"panel_replay_{chat_id}"),
            InlineKeyboardButton(text="‣‣I", callback_data=f"panel_skip_{chat_id}"),
            InlineKeyboardButton(text="▢", callback_data=f"panel_stop_{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="Queue", callback_data=f"panel_queue_{chat_id}"),
            InlineKeyboardButton(text="× Close", callback_data="panel_close"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def queued_markup(chat_id: int, video_id: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Play", callback_data=f"force_play_{video_id}"),
            InlineKeyboardButton(text="Queue", callback_data=f"panel_queue_{chat_id}"),
            InlineKeyboardButton(text="× Close", callback_data="panel_close"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)

# -------------------------------------------------------------
# 3. QUEUE MARKUPS (SECTIONS 11, 12, 55, 57, 72)
# -------------------------------------------------------------

def queue_markup(chat_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="↻ Refresh", callback_data=f"panel_queue_{chat_id}"),
            InlineKeyboardButton(text="Clear", callback_data=f"queue_clear_{chat_id}"),
            InlineKeyboardButton(text="‹ Back", callback_data=f"panel_controls_{chat_id}"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def empty_queue_markup() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Play", switch_inline_query_current_chat=""),
            InlineKeyboardButton(text="Search", switch_inline_query_current_chat=""),
        ]
    ]
    return InlineKeyboardMarkup(buttons)

# -------------------------------------------------------------
# 4. RECOMMENDATIONS (SECTIONS 20, 55, 72)
# -------------------------------------------------------------

def recommendation_markup(recs: List[Dict[str, Any]], session_id: str, offset: int = 0) -> InlineKeyboardMarkup:
    buttons = []
    current_chunk = recs[offset : offset + 3]
    for idx, r in enumerate(current_chunk, start=1):
        title = r.get("title", "Song Recommendation")
        artist = r.get("channel") or r.get("channel_name") or ""
        label = f"{title} — {artist}" if artist else title
        display_title = (label[:30] + "…") if len(label) > 32 else label
        vid_id = r.get("video_id") or r.get("id") or ""
        buttons.append([
            InlineKeyboardButton(
                text=display_title,
                callback_data=f"rec_play_{session_id}_{vid_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="More", callback_data=f"rec_more_{session_id}"),
        InlineKeyboardButton(text="‹ Back", callback_data="panel_close"),
    ])
    return InlineKeyboardMarkup(buttons)

# -------------------------------------------------------------
# 5. SETTINGS PANELS (SECTIONS 35, 36, 37, 38, 55, 56, 72)
# -------------------------------------------------------------

def settings_markup(chat_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Autoplay", callback_data=f"set_autoplay_menu_{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="Thumbnails", callback_data=f"set_thumb_menu_{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="Language", callback_data=f"set_lang_{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="× Close", callback_data="settings_close")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def autoplay_setting_markup(chat_id: int, is_enabled: bool) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Enable", callback_data=f"set_ap_on_{chat_id}"),
            InlineKeyboardButton(text="Disable", callback_data=f"set_ap_off_{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="‹ Back", callback_data=f"btn_settings_{chat_id}"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def thumbnail_setting_markup(chat_id: int, is_enabled: bool) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Enable", callback_data=f"set_tb_on_{chat_id}"),
            InlineKeyboardButton(text="Disable", callback_data=f"set_tb_off_{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="‹ Back", callback_data=f"btn_settings_{chat_id}"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def global_thumbnail_markup(current_state: bool) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Enable", callback_data="owner_gthumb_on"),
            InlineKeyboardButton(text="Disable", callback_data="owner_gthumb_off"),
        ],
        [
            InlineKeyboardButton(text="× Close", callback_data="owner_gthumb_close")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

# -------------------------------------------------------------
# 6. LANGUAGE SELECTION (SECTIONS 39, 55, 72)
# -------------------------------------------------------------

def language_markup(chat_id: int = 0) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="English", callback_data=f"lang_en_{chat_id}"),
            InlineKeyboardButton(text="हिन्दी", callback_data=f"lang_hi_{chat_id}"),
            InlineKeyboardButton(text="ਪੰਜਾਬੀ", callback_data=f"lang_pa_{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="Deutsch", callback_data=f"lang_de_{chat_id}"),
            InlineKeyboardButton(text="Español", callback_data=f"lang_es_{chat_id}"),
            InlineKeyboardButton(text="Français", callback_data=f"lang_fr_{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="Português", callback_data=f"lang_pt_{chat_id}"),
            InlineKeyboardButton(text="Русский", callback_data=f"lang_ru_{chat_id}"),
            InlineKeyboardButton(text="Türkçe", callback_data=f"lang_tr_{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="中文", callback_data=f"lang_zh_{chat_id}"),
            InlineKeyboardButton(text="日本語", callback_data=f"lang_ja_{chat_id}"),
            InlineKeyboardButton(text="မြန်မာ", callback_data=f"lang_my_{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="العربية", callback_data=f"lang_ar_{chat_id}"),
        ],
        [
            InlineKeyboardButton(text="‹ Back", callback_data=f"btn_settings_{chat_id}"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)

# -------------------------------------------------------------
# 7. HELP MENUS (SECTIONS 41, 42, 55, 56, 72)
# -------------------------------------------------------------

def help_main_markup() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Playback", callback_data="help_playback"),
            InlineKeyboardButton(text="Queue", callback_data="help_queue"),
        ],
        [
            InlineKeyboardButton(text="Discovery", callback_data="help_discovery"),
            InlineKeyboardButton(text="Settings", callback_data="help_settings"),
        ],
        [
            InlineKeyboardButton(text="× Close", callback_data="help_close"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def help_category_markup() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="‹ Back", callback_data="help_main"),
            InlineKeyboardButton(text="× Close", callback_data="help_close"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)

# -------------------------------------------------------------
# 8. SEARCH RESULTS & ACTION MARKUPS (SECTIONS 21, 22, 55, 72)
# -------------------------------------------------------------

def search_no_results_markup() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Search again", switch_inline_query_current_chat=""),
            InlineKeyboardButton(text="‹ Back", callback_data="panel_close"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def inline_result_markup(url: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Open", url=url),
            InlineKeyboardButton(text="Play", switch_inline_query_current_chat=url)
        ]
    ]
    return InlineKeyboardMarkup(buttons)
