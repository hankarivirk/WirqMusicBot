import html
from pyrogram import types
from wirq import app, logger
from py_yt import VideosSearch

@app.on_inline_query(~app.bl_users)
async def inline_query_handler(_, query: types.InlineQuery):
    text = query.query.strip().lower()
    if not text:
        return
    try:
        search = VideosSearch(text, limit=15)
        res = await search.next()
        results = res.get("result", [])
        answers = []
        for video in results:
            title = html.escape((video.get("title") or "Unknown Title").title())
            duration = video.get("duration") or "00:00"
            link = video.get("link") or f"https://www.youtube.com/watch?v={video.get('id')}"
            thumbs = video.get("thumbnails") or [{}]
            thumb = thumbs[0].get("url") if thumbs else None
            
            input_content = types.InputTextMessageContent(f"/play {link}")
            markup = types.InlineKeyboardMarkup([
                [types.InlineKeyboardButton("▶️ Stream in Voice Chat", url=link)]
            ])
            
            answers.append(
                types.InlineQueryResultArticle(
                    title=title,
                    description=f"Duration: {duration}",
                    thumb_url=thumb,
                    input_message_content=input_content,
                    reply_markup=markup,
                )
            )
        await query.answer(results=answers, cache_time=5)
    except Exception as e:
        logger.warning(f"Inline query error: {e}")
