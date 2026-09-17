# Wirq Music Bot - Search Plugin (Section 5)
from pyrogram import filters, types
from py_yt import VideosSearch
from wirq import app, lang, logger
from wirq.helpers import buttons

@app.on_message(filters.command(["search"]) & filters.group & ~app.bl_users)
@lang.language()
async def _search(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text("<b>Usage:</b> <code>/search &lt;song or artist name&gt;</code>")

    query = " ".join(m.command[1:])
    sent = await m.reply_text("🔎 <b>Searching YouTube...</b>")

    try:
        search = VideosSearch(query, limit=5)
        res = await search.next()
        results = res.get("result", [])
        if not results:
            return await sent.edit_text("❌ No results found on YouTube.")

        markup = buttons.search_markup(results, m.chat.id)
        await sent.edit_text(
            f"🔎 <b>Search Results for:</b> <i>{query}</i>\\n\\n"
            "<i>Tap any result below to directly stream or queue it in voice chat:</i>",
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        await sent.edit_text(f"❌ Search failed: <code>{e}</code>")
