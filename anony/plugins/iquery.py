import logging
from pyrogram import filters
from pyrogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from anony import app
from anony.core.youtube import YouTube
from anony.helpers._inline import inline_result_markup

LOGGER = logging.getLogger("MusicFlow.InlineQuery")

@app.on_inline_query()
async def inline_search_handler(_, query: InlineQuery):
    text = query.query.strip()
    if not text:
        return

    try:
        tracks = await YouTube.search_many(text, limit=10)
        results = []
        for track in tracks:
            title = track.get("title", "Unknown")
            views = track.get("views", "N/A")
            duration = track.get("duration", "00:00")
            channel = track.get("channel", "YouTube")
            channel_url = track.get("channel_url", "")
            published = track.get("published", "N/A")
            url = track.get("url", "")
            thumb = track.get("thumbnail")

            caption = (
                "MUSIC FLOW SEARCH\n\n"
                f"<b>{title}</b>\n\n"
                f"<b>Duration:</b> {duration}\n"
                f"<b>Views:</b> <code>{views}</code>\n"
                f"<b>Channel:</b> <a href=\"{channel_url}\">{channel}</a>\n"
                f"<b>Published:</b> {published}"
            )
            desc = f"{views} · {duration} · {channel}"
            results.append(
                InlineQueryResultArticle(
                    title=title,
                    description=desc,
                    thumb_url=thumb,
                    input_message_content=InputTextMessageContent(caption, disable_web_page_preview=False),
                    reply_markup=inline_result_markup(url)
                )
            )
        await query.answer(results, cache_time=60)
    except Exception as e:
        LOGGER.error(f"Inline search failed: {e}")
        await query.answer([], cache_time=5)
