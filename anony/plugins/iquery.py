# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


import html

from py_yt import VideosSearch
from pyrogram import types

from anony import app, logger
from anony.helpers import buttons


@app.on_inline_query(~app.bl_users)
async def inline_query_handler(_, query: types.InlineQuery):
    text = query.query.strip().lower()
    if not text:
        return

    answered = False
    try:
        search = VideosSearch(text, limit=15)
        results = (await search.next()).get("result", [])

        answers = []
        for video in results:
            try:
                title = (video.get("title") or "Unknown Title").title()
                duration = video.get("duration") or "N/A"
                views = video.get("viewCount", {}).get("short") or "N/A"
                thumbs = video.get("thumbnails") or [{}]
                thumbnail = (thumbs[0].get("url") or "").split("?")[0]
                channel = video.get("channel", {}).get("name") or "Unknown Channel"
                channellink = video.get("channel", {}).get("link") or "https://youtube.com"
                link = video.get("link") or "https://youtube.com"
                published = video.get("publishedTime") or "N/A"

                description = f"{views} | {duration} | {channel} | {published}"
                # title/channel come straight from YouTube metadata and can
                # contain <, >, & — escape them (and quote-escape the href
                # values) before dropping them into an HTML caption, or a
                # single malformed title can break this caption's parse
                # and, worse, invalidate the whole answer_inline_query()
                # call for every result in the batch.
                safe_title = html.escape(title[:250])
                safe_channel = html.escape(channel)
                safe_link = html.escape(link, quote=True)
                safe_channellink = html.escape(channellink, quote=True)
                caption = (
                    f"<b>Title:</b> <a href='{safe_link}'>{safe_title}</a>\n\n"
                    f"<b>Duration:</b> {html.escape(duration)}\n"
                    f"<b>Views:</b> <code>{html.escape(views)}</code>\n"
                    f"<b>Channel:</b> <a href='{safe_channellink}'>{safe_channel}</a>\n"
                    f"<b>Published:</b> {html.escape(published)}\n\n"
                    f"<u><i>Fetched by {html.escape(app.name)}</i></u>"
                )

                answers.append(
                    types.InlineQueryResultPhoto(
                        photo_url=thumbnail,
                        title=title,
                        description=description,
                        caption=caption,
                        reply_markup=buttons.yt_key(link),
                    )
                )
            except Exception as e:
                logger.warning(f"Skipping malformed inline result: {e}")
                continue

        if answers:
            await app.answer_inline_query(query.id, results=answers, cache_time=5)
            answered = True
    except Exception as e:
        logger.warning(f"Inline query failed for {text!r}: {e}")
    finally:
        if not answered:
            # Leave the query answered with no results instead of letting
            # it hang unanswered on the client if anything above failed.
            try:
                await app.answer_inline_query(query.id, results=[], cache_time=5)
            except Exception:
                pass
