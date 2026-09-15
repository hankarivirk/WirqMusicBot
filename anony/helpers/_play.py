# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Wirq Music Bot


import asyncio

from pyrogram import enums, errors, types

import anony
from anony import config, logger
from anony.helpers import utils


def checkUB(play):
    async def wrapper(_, m: types.Message):
        if not m.from_user:
            return await m.reply_text(m.lang["play_user_invalid"])

        chat_id = m.chat.id
        if m.chat.type != enums.ChatType.SUPERGROUP:
            await m.reply_text(m.lang["play_chat_invalid"])
            return await anony.app.leave_chat(chat_id)

        if not m.reply_to_message and (
            len(m.command) < 2 or (len(m.command) == 2 and m.command[1] == "-f")
        ):
            return await m.reply_text(m.lang["play_usage"])

        force = m.command[0].endswith("force") or (
            len(m.command) > 1 and m.command[1] == "-f"
        )

        # A forced play replaces/bumps the current track rather than
        # appending to the queue, so the queue-limit check (which only
        # makes sense for a normal append) must not reject it before
        # `force` is even known.
        if not force and len(anony.queue.get_queue(chat_id)) >= config.QUEUE_LIMIT:
            return await m.reply_text(m.lang["play_queue_full"].format(config.QUEUE_LIMIT))

        video = m.command[0][0] == "v" and config.VIDEO_PLAY
        music = "music" in m.command[0]
        url = utils.get_url(m)
        if url and anony.yt.invalid(url):
            return await m.reply_text(m.lang["play_not_found"].format(config.SUPPORT_CHAT))
        m3u8 = url and not anony.yt.valid(url)

        play_mode = await anony.db.get_play_mode(chat_id)
        if play_mode or force:
            adminlist = await anony.db.get_admins(chat_id)
            if (
                m.from_user.id not in adminlist
                and not await anony.db.is_auth(chat_id, m.from_user.id)
                and not m.from_user.id in anony.app.sudoers
            ):
                return await m.reply_text(m.lang["play_admin"])

        if chat_id not in anony.db.active_calls:
            client = await anony.db.get_client(chat_id)
            try:
                member = await anony.app.get_chat_member(chat_id, client.id)
                if member.status in [
                    enums.ChatMemberStatus.BANNED,
                    enums.ChatMemberStatus.RESTRICTED,
                ]:
                    try:
                        await anony.app.unban_chat_member(
                            chat_id=chat_id, user_id=client.id
                        )
                    except Exception:
                        return await m.reply_text(
                            m.lang["play_banned"].format(
                                anony.app.name,
                                client.id,
                                client.mention,
                                f"@{client.username}" if client.username else None,
                            )
                        )
            except errors.ChatAdminRequired:
                return await m.reply_text(m.lang["admin_required"])
            except errors.UserNotParticipant:
                if m.chat.username:
                    invite_link = m.chat.username
                else:
                    try:
                        invite_link = (await anony.app.get_chat(chat_id)).invite_link
                        if not invite_link:
                            invite_link = await anony.app.export_chat_invite_link(chat_id)
                    except errors.ChatAdminRequired:
                        return await m.reply_text(m.lang["admin_required"])
                    except Exception as ex:
                        return await m.reply_text(
                            m.lang["play_invite_error"].format(type(ex).__name__)
                        )

                umm = await m.reply_text(m.lang["play_invite"].format(anony.app.name))
                await asyncio.sleep(2)
                try:
                    await client.join_chat(invite_link)
                except errors.UserAlreadyParticipant:
                    pass
                except errors.InviteRequestSent:
                    await asyncio.sleep(2)
                    try:
                        await anony.app.approve_chat_join_request(chat_id, client.id)
                    except errors.HideRequesterMissing:
                        pass
                    except Exception as ex:
                        return await umm.edit_text(
                            m.lang["play_invite_error"].format(type(ex).__name__)
                        )
                except Exception as ex:
                    logger.error(f"Error joining chat - {chat_id}: {ex}")
                    return await umm.edit_text(
                        m.lang["play_invite_error"].format(type(ex).__name__)
                    )

                await umm.delete()

        if await anony.db.get_cmd_delete(chat_id):
            try:
                await m.delete()
            except Exception:
                pass

        return await play(_, m, force, m3u8, video, url, music)

    return wrapper
