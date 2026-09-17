# Wirq Music Bot - Interactive Callback Handler
import time
from pyrogram import filters, types
from wirq import app, calls, db, lang, queue, yt, logger, config
from wirq.helpers import buttons, admin_check

@app.on_callback_query(~app.bl_users)
async def callback_router(_, q: types.CallbackQuery):
    data = q.data
    chat_id = q.message.chat.id if q.message and q.message.chat else 0
    user_id = q.from_user.id if q.from_user else 0

    # 1. Close Button
    if data == "close_btn":
        try:
            await q.message.delete()
        except Exception:
            pass
        return await q.answer("Closed.")

    # 2. Language Selection Callback
    if data.startswith("lang_"):
        code = data.split("_")[1]
        if q.message.chat.type.value == "private":
            await db.set_user_lang(user_id, code)
            target = "your direct messages"
        else:
            await db.set_lang(chat_id, code)
            target = "this group"
        lang_name = lang.lang_codes.get(code, code)
        await q.answer(f"Language set to {lang_name}!", show_alert=True)
        try:
            await q.message.edit_text(
                f"🌐 <b>Language successfully updated for {target}:</b> <code>{lang_name}</code>",
                reply_markup=buttons.lang_markup(code)
            )
        except Exception:
            pass
        return

    # 3. Help Submenus
    if data == "help_menu":
        text = (
            f"<b>📚 {config.BOT_NAME} Help Hub:</b>\\n\\n"
            "Select a category below to view commands and controls."
        )
        return await q.edit_message_text(text, reply_markup=buttons.help_markup())

    if data == "help_play":
        text = (
            "<b>🎵 Playback Commands:</b>\\n\\n"
            "• <code>/play &lt;query/link&gt;</code> - Stream audio in voice chat\\n"
            "• <code>/vplay &lt;query/link&gt;</code> - Stream video + audio in HD\\n"
            "• <code>/search &lt;query&gt;</code> - Interactive YouTube search buttons\\n"
            "• <code>/pause</code> - Pause stream\\n"
            "• <code>/resume</code> - Resume stream\\n"
            "• <code>/skip</code> - Skip to next queued item\\n"
            "• <code>/stop</code> - Stop playback and clear voice chat\\n"
            "• <code>/replay</code> - Replay current song\\n"
            "• <code>/queue</code> - View active playlist"
        )
        return await q.edit_message_text(text, reply_markup=types.InlineKeyboardMarkup([
            [types.InlineKeyboardButton("🔙 Back", callback_data="help_menu")]
        ]))

    if data == "help_admin":
        text = (
            "<b>🛡️ Admin Commands:</b>\\n\\n"
            "• <code>/loop</code> - Cycle 3-state loop (OFF / Song / Queue)\\n"
            "• <code>/autoplay</code> - Toggle smart recommendations\\n"
            "• <code>/volume &lt;1-100&gt;</code> - Set voice chat volume\\n"
            "• <code>/seek &lt;sec&gt;</code> - Jump to timestamp\\n"
            "• <code>/thumbnail [on|off]</code> - Toggle custom player cards\\n"
            "• <code>/leave</code> - Force assistant to leave voice chat"
        )
        return await q.edit_message_text(text, reply_markup=types.InlineKeyboardMarkup([
            [types.InlineKeyboardButton("🔙 Back", callback_data="help_menu")]
        ]))

    # 4. Search Play Callback (Section 5)
    if data.startswith("search_play "):
        parts = data.split()
        target_chat = int(parts[1])
        video_id = parts[2]
        await q.answer("⏳ Adding track to voice chat...")
        try:
            await q.message.delete()
        except Exception:
            pass
        track = await yt.search(f"https://www.youtube.com/watch?v={video_id}", q.message.id)
        if track:
            setattr(track, "user", q.from_user.mention)
            queue.put(target_chat, track)
            if not await db.get_call(target_chat):
                msg = await app.send_message(chat_id=target_chat, text=f"⏳ Loading <b>{track.title}</b>...")
                track.file_path = await yt.download(track.id, video=False)
                await calls.play_media(target_chat, msg, track)
            else:
                await app.send_message(
                    chat_id=target_chat,
                    text=f"📋 <b>Queued:</b> <a href='{track.url}'>{track.title}</a> ({track.duration})"
                )
        return

    # 5. Recommendation Play & More (Section 4 & 5)
    if data.startswith("play_rec_"):
        video_id = data.replace("play_rec_", "")
        await q.answer("⏳ Streaming recommendation...")
        track = await yt.search(f"https://www.youtube.com/watch?v={video_id}", q.message.id)
        if track:
            setattr(track, "user", f"{q.from_user.mention} (Recommendation)")
            queue.put(chat_id, track)
            if not await db.get_call(chat_id):
                msg = await app.send_message(chat_id=chat_id, text=f"⏳ Streaming <b>{track.title}</b>...")
                track.file_path = await yt.download(track.id, video=False)
                await calls.play_media(chat_id, msg, track)
            else:
                await app.send_message(
                    chat_id=chat_id,
                    text=f"📋 <b>Queued Recommendation:</b> <a href='{track.url}'>{track.title}</a>"
                )
        return

    if data == "recommend_more":
        state = calls.recommend_state.get(chat_id)
        if not state:
            return await q.answer("No more recommendations stored.", show_alert=True)
        recs = state.get("recs", [])
        offset = (state.get("offset", 0) + 3) % len(recs)
        state["offset"] = offset
        batch = recs[offset:offset+3]
        if not batch:
            batch = recs[:3]
        markup = buttons.recommend_markup(batch, "🔄 More Recommendations")
        await q.answer("Showing fresh recommendations!")
        try:
            await q.edit_message_reply_markup(reply_markup=markup)
        except Exception:
            pass
        return

    # 6. Player Controls (Section 2)
    if data.startswith("controls "):
        parts = data.split()
        action = parts[1]
        target_chat = int(parts[2])

        # Verify admin permissions
        from wirq.helpers._admins import is_admin
        if not (user_id == app.owner_id or user_id in app.sudoers or await is_admin(target_chat, user_id)):
            return await q.answer("⚠️ Administrator rights required for player controls.", show_alert=True)

        if action == "pause":
            await calls.pause(target_chat)
            await q.answer("Paused ⏸")
            try:
                await q.edit_message_reply_markup(reply_markup=buttons.controls(target_chat, is_paused=True))
            except Exception:
                pass

        elif action == "resume":
            await calls.resume(target_chat)
            await q.answer("Resumed ▶️")
            try:
                await q.edit_message_reply_markup(reply_markup=buttons.controls(target_chat, is_paused=False))
            except Exception:
                pass

        elif action == "skip":
            await q.answer("Skipping to next track... ⏭")
            await calls.play_next(target_chat)

        elif action == "stop":
            await q.answer("Stopping playback... ⏹")
            await calls.stop(target_chat)
            try:
                await q.message.edit_text("⏹ <b>Playback stopped and queue cleared.</b>")
            except Exception:
                pass

        elif action == "replay":
            await q.answer("Replaying track from start... 🔄")
            await calls.replay(target_chat)

        elif action == "loop":
            curr = await db.get_loop(target_chat)
            new_mode = (curr + 1) % 3
            await db.set_loop(target_chat, new_mode)
            labels = ["Loop OFF", "Loop Current Song", "Loop Entire Queue"]
            await q.answer(f"🔁 {labels[new_mode]}", show_alert=True)

        elif action == "autoplay":
            curr = await db.get_autoplay(target_chat)
            new_auto = not curr
            await db.set_autoplay(target_chat, new_auto)
            await q.answer(f"⚡ Autoplay: {'ENABLED' if new_auto else 'DISABLED'}", show_alert=True)

        elif action == "shuffle":
            queue.shuffle(target_chat)
            await q.answer("🔀 Queue shuffled successfully!", show_alert=True)

        elif action == "volume_menu":
            vol = await db.get_volume(target_chat)
            await q.edit_message_reply_markup(reply_markup=buttons.volume_markup(target_chat, vol))

        elif action == "leave":
            await calls.leave(target_chat)
            await q.answer("Voice assistant left the chat.")
            try:
                await q.message.edit_text("🚪 <b>Assistant left voice chat.</b>")
            except Exception:
                pass

        elif action == "back":
            await q.edit_message_reply_markup(reply_markup=buttons.controls(target_chat))

    # 7. Volume Preset Selection
    if data.startswith("set_vol "):
        parts = data.split()
        target_chat = int(parts[1])
        level = int(parts[2])
        await calls.volume(target_chat, level)
        await q.answer(f"Volume adjusted to {level}%", show_alert=True)
        await q.edit_message_reply_markup(reply_markup=buttons.controls(target_chat))
