# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot

"""
Renders our limited HTML subset (b, u, i, code, blockquote, a href) PLUS
known premium-emoji characters into (plain_text, entities) — bypassing
parse_mode=HTML's own tag parsing entirely for these specific messages.

Why: Telegram's premium/custom emoji requires a CUSTOM_EMOJI message
entity pointing at a custom_emoji_id. There's no way to express that as
plain text, and guessing at pyrogram/kurigram's internal HTML tag syntax
for it (tried once already) isn't reliable without a live test. This
instead builds pyrogram.types.MessageEntity objects directly — the same
public, documented type used when READING entities off any message — so
it doesn't depend on any internal/undocumented parsing behavior.

The offset/length math (the genuinely fiddly part: Telegram counts
UTF-16 code units, not Python string indices, so any character outside
the Basic Multilingual Plane — which is most emoji — takes 2 units, not
1) is covered by tests in test_richtext.py and is provably correct
independent of pyrogram. What ISN'T verifiable without a live bot is
whether Telegram's servers accept a custom_emoji_id you don't personally
have unlocked in your own account — bots aren't supposed to need that,
but if these still don't render after this change, that's the next
thing to check.
"""

import re

from pyrogram.enums import MessageEntityType
from pyrogram.types import MessageEntity

_TAG_RE = re.compile(r'<(/?)(b|u|i|code|blockquote|a)(?:\s+href=(["\']?)([^"\'>]*)\3)?>')
_TAG_TYPE = {
    "b": MessageEntityType.BOLD,
    "u": MessageEntityType.UNDERLINE,
    "i": MessageEntityType.ITALIC,
    "code": MessageEntityType.CODE,
    "blockquote": MessageEntityType.BLOCKQUOTE,
    "a": MessageEntityType.TEXT_LINK,
}
_ESCAPES = (("&lt;", "<"), ("&gt;", ">"), ("&amp;", "&"))


def _utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def render_rich(html_text: str, emoji_map: dict[str, str]) -> tuple[str, list[MessageEntity]]:
    """emoji_map: base emoji codepoint (without variation selector) ->
    custom_emoji_id string. Matches the VS16 (️) variant first if
    present so no stray variation selector is left in the output text."""
    idx = 0
    n = len(html_text)
    output: list[str] = []
    stack: list[list] = []
    entities: list[MessageEntity] = []

    while idx < n:
        m = _TAG_RE.match(html_text, idx)
        if m:
            closing, tag, _, href = m.groups()
            cur_offset = _utf16_len("".join(output))
            if not closing:
                stack.append([tag, cur_offset, href])
            else:
                for i in range(len(stack) - 1, -1, -1):
                    if stack[i][0] == tag:
                        _, start_offset, href_val = stack.pop(i)
                        length = cur_offset - start_offset
                        if length > 0:
                            kwargs = {}
                            if tag == "a":
                                kwargs["url"] = href_val
                            entities.append(MessageEntity(
                                type=_TAG_TYPE[tag],
                                offset=start_offset,
                                length=length,
                                **kwargs,
                            ))
                        break
            idx = m.end()
            continue

        matched = None
        for base, emoji_id in emoji_map.items():
            for variant in (base + "\ufe0f", base):
                if html_text.startswith(variant, idx):
                    matched = (variant, emoji_id)
                    break
            if matched:
                break

        if matched:
            variant, emoji_id = matched
            cur_offset = _utf16_len("".join(output))
            entities.append(MessageEntity(
                type=MessageEntityType.CUSTOM_EMOJI,
                offset=cur_offset,
                length=_utf16_len(variant),
                custom_emoji_id=emoji_id,
            ))
            output.append(variant)
            idx += len(variant)
            continue

        escaped = False
        for esc, real in _ESCAPES:
            if html_text.startswith(esc, idx):
                output.append(real)
                idx += len(esc)
                escaped = True
                break
        if escaped:
            continue

        output.append(html_text[idx])
        idx += 1

    return "".join(output), entities


# base emoji codepoint (no variation selector) -> premium custom_emoji_id
PREMIUM_EMOJI: dict[str, str] = {
    "\u26a0": "5316798307014556036",   # ⚠
    "\U0001f4a1": "5316637280100693932",  # 💡
    "\U0001f6ab": "5316538964004321334",  # 🚫
    "\u2705": "5316571734604790521",   # ✅
    "\U0001f310": "5316698440434989602",  # 🌐
    "\U0001f511": "5370993432716129583",  # 🔑
    "\U0001f4cb": "5316901708352207829",  # 📋
    "\U0001f4ca": "5316575892133132571",  # 📊
    "\U0001f399": "5316765712507747050",  # 🎙
    "\u2795": "5318760565902947324",   # ➕
    "\U0001fa84": "5316558016479245582",  # 🪄
    "\U0001f512": "5316990468146346495",  # 🔒
    "\U0001f507": "5316639745411922559",  # 🔇
    "\U0001f6e1": "5316705578670636235",  # 🛡
    "\U0001f502": "5316930493223025689",  # 🔂
    "\U0001f504": "5316977222467206948",  # 🔄
    "\U0001f6d1": "5316538964004321334",  # 🛑
    "\u2b07": "5316591603123502631",   # ⬇
    "\U0001f4e2": "5316773525053258010",  # 📢
    "\U0001f3b5": "5319090522470495400",  # 🎵
    "\U0001f4c4": "5317051834639071081",  # 📄
    "\U0001fa69": "5316631095347788915",  # 🪩
    "\U0001f501": "5316504505481709320",  # 🔁
    "\U0001f50d": "5319091153830688459",  # 🔍
    "\U0001f464": "5316992572680320646",  # 👤
    "\u274c": "5316660455744223443",   # ❌
    "\U0001f500": "5316599316884766402",  # 🔀
    "\U0001f4ed": "5317017092648613267",  # 📭
    "\U0001f940": "5316899719782348541",  # 🥀
    "\U0001f329": "5316653661105961462",  # 🌩
    "\u2601": "5316653661105961462",   # ☁
    "\U0001f4d6": "5316826301611390284",  # 📖
    "\U0001f4e1": "5316765712507747050",  # 📡
    "\U0001f451": "5316990468146346495",  # 👑
    "\U0001f390": "6039505337151655702",  # 🎐
    "\U0001fab6": "6039454987250044861",  # 🪶
    "\U0001f300": "5850346984501680054",  # 🌀
    "\U0001f98b": "6037622221625626773",  # 🦋
    "\U0001f54a": "6030537007350944596",  # 🕊
    "\U0001f3d3": "5319070993254201336",  # 🏓
    "\U0001f916": "5316798307014556036",  # 🤖
    "\U0001f4c3": "5778299625370817409",  # 📃
    "\U0001f3a7": "5929546997483704366",  # 🎧
    "\u2699": "5316832430529722441",   # ⚙
    "\U0001fa81": "5316930493223025689",  # 🪁
    "\U0001f343": "5316710702566619149",  # 🍃
    "\U0001f4dc": "6030466823290360017",  # 📜
    "\U0001f44b": "5319007286004299794",  # 👋
    "\U0001f7e2": "6039584437564347225",  # 🟢
    "\U0001f534": "6030563507299160824",  # 🔴
}


def rich(text: str) -> tuple[str, list[MessageEntity]]:
    """Convenience wrapper using the bot's built-in premium emoji map."""
    return render_rich(text, PREMIUM_EMOJI)
