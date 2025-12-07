
import asyncio
import base64
import time
from asyncio import Lock
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.enums import ParseMode, ChatMemberStatus, ChatAction
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram.errors import FloodWait, UserNotParticipant, UserIsBlocked, InputUserDeactivated
import os
import asyncio
from asyncio import sleep
from asyncio import Lock
import random 

from bot import Bot
from datetime import datetime, timedelta
from config import *
from database.database import *
from plugins.newpost import revoke_invite_after_5_minutes
from helper_func import *

# Create a lock dictionary for each channel to prevent concurrent link generation
channel_locks = defaultdict(asyncio.Lock)

user_banned_until = {}

# Broadcast variables
cancel_lock = asyncio.Lock()
is_canceled = False

@Bot.on_message(filters.command('start') & filters.private)
async def start_command(client: Bot, message: Message):
    user_id = message.from_user.id

    if user_id in user_banned_until:
        if datetime.now() < user_banned_until[user_id]:
            return await message.reply_text(
                "<b><blockquote expandable>You are temporarily banned from using commands due to spamming. Try again later.</b>",
                parse_mode=ParseMode.HTML
            )
            
    await add_user(user_id)

    text = message.text
    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
            is_request = base64_string.startswith("req_")
            
            if is_request:
                base64_string = base64_string[4:]
                channel_id = await get_channel_by_encoded_link2(base64_string)
            else:
                channel_id = await get_channel_by_encoded_link(base64_string)
            
            if not channel_id:
                return await message.reply_text(
                    "<b><blockquote expandable>Invalid or expired invite link.</b>",
                    parse_mode=ParseMode.HTML
                )

            # Get channel info for title
            try:
                chat = await client.get_chat(channel_id)
                channel_title = chat.title
                # Remove "Hindi" from end of title if present
                if channel_title.endswith(" Hindi"):
                    channel_title = channel_title[:-6].strip()
            except Exception as e:
                print(f"Error getting channel title for {channel_id}: {e}")
                channel_title = "the channel" # Fallback title

            response_text = f"Here is your link for {channel_title}. Click below to proceed."

            # Check if this is a /genlink link (original_link exists)
            from database.database import get_original_link
            original_link = await get_original_link(channel_id)
            if original_link:
                button = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("• Proceed to Link •", url=original_link)]]
                )
                return await message.reply_text(
                    response_text,
                    reply_markup=button,
                    parse_mode=ParseMode.HTML
                )

            # Use a lock for this channel to prevent concurrent link generation
            async with channel_locks[channel_id]:
                # Check if we already have a valid link
                old_link_info = await get_current_invite_link(channel_id)
                current_time = datetime.now()
                
                # If we have an existing link and it's not expired yet (assuming 5 minutes validity)
                if old_link_info:
                    link_created_time = await get_link_creation_time(channel_id)
                    if link_created_time and (current_time - link_created_time).total_seconds() < 240:  # 4 minutes
                        # Use existing link
                        invite_link = old_link_info["invite_link"]
                        is_request_link = old_link_info["is_request"]
                    else:
                        # Revoke old link and create new one
                        try:
                            await client.revoke_chat_invite_link(channel_id, old_link_info["invite_link"])
                            print(f"Revoked old {'request' if old_link_info['is_request'] else 'invite'} link for channel {channel_id}")
                        except Exception as e:
                            print(f"Failed to revoke old link for channel {channel_id}: {e}")
                        
                        # Create new link
                        invite = await client.create_chat_invite_link(
                            chat_id=channel_id,
                            expire_date=current_time + timedelta(minutes=10),
                            creates_join_request=is_request
                        )
                        invite_link = invite.invite_link
                        is_request_link = is_request
                        await save_invite_link(channel_id, invite_link, is_request_link)
                else:
                    # Create new link
                    invite = await client.create_chat_invite_link(
                        chat_id=channel_id,
                        expire_date=current_time + timedelta(minutes=10),
                        creates_join_request=is_request
                    )
                    invite_link = invite.invite_link
                    is_request_link = is_request
                    await save_invite_link(channel_id, invite_link, is_request_link)

            from database.database import get_channel_photo
            photo_link = await get_channel_photo(channel_id)
            
            button_text = "• ʀᴇǫᴜᴇsᴛ ᴛᴏ ᴊᴏɪɴ •" if is_request_link else "• ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ •"
            button = InlineKeyboardMarkup([[InlineKeyboardButton(button_text, url=invite_link)]])

            wait_msg = await message.reply_text(
                "⏳",
                parse_mode=ParseMode.HTML
            )
            
            await wait_msg.delete()
            
            if photo_link:
                try:
                    await message.reply_photo(
                        photo=photo_link,
                        caption=response_text,
                        reply_markup=button,
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    print(f"Error sending photo message: {e}")
                    # Fallback to text message if photo fails
                    await message.reply_text(
                        response_text,
                        reply_markup=button,
                        parse_mode=ParseMode.HTML
                    )
            else:
                # Original text message behavior
                await message.reply_text(
                    response_text,
                    reply_markup=button,
                    parse_mode=ParseMode.HTML
                )

            asyncio.create_task(revoke_invite_after_5_minutes(client, channel_id, invite_link, is_request_link))

        except Exception as e:
            await message.reply_text(
                "<b><blockquote expandable>Invalid or expired invite link.</b>",
                parse_mode=ParseMode.HTML
            )
            print(f"Decoding error: {e}")
    else:
        inline_buttons = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("• ᴀʙᴏᴜᴛ", callback_data="about"),
                 InlineKeyboardButton("• ᴄʜᴀɴɴᴇʟs", callback_data="channels")],
                [InlineKeyboardButton("• Close •", callback_data="close")]
            ]
        )
        
        # Show waiting emoji and instantly delete it
        wait_msg = await message.reply_text("⏳")
        await asyncio.sleep(0.1)
        await wait_msg.delete()
        
        try:
            await message.reply_photo(
                photo=START_PIC,
                caption=START_MSG,
                reply_markup=inline_buttons,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            print(f"Error sending start picture: {e}")
            await message.reply_text(
                START_MSG,
                reply_markup=inline_buttons,
                parse_mode=ParseMode.HTML
            )


#=====================================================================================##
# Don't Remove Credit @CodeFlix_Bots, @rohit_1888
# Ask Doubt on telegram @CodeflixSupport

async def get_link_creation_time(channel_id):
    """Get the creation time of the current invite link for a channel."""
    try:
        from database.database import channels_collection
        channel = await channels_collection.find_one({"channel_id": channel_id, "status": "active"})
        if channel and "invite_link_created_at" in channel:
            return channel["invite_link_created_at"]
        return None
    except Exception as e:
        print(f"Error fetching link creation time for channel {channel_id}: {e}")
        return None

# Create a global dictionary to store chat data
chat_data_cache = {}

async def get_chat_data(client, chat_id):
    if chat_id in chat_data_cache:
        return chat_data_cache[chat_id]
    
    try:
        chat = await client.get_chat(chat_id)
        chat_data_cache[chat_id] = chat
        return chat
    except Exception as e:
        print(f"Error fetching chat data for {chat_id}: {e}")
        return None

async def not_joined(client, message):
    buttons = []
    
    fsub_channels = await get_fsub_channels()
    if fsub_channels:
        for channel_id in fsub_channels:
            chat = await get_chat_data(client, channel_id)
            if chat:
                buttons.append([InlineKeyboardButton(chat.title, url=chat.invite_link)])
    
    if buttons:
        await message.reply_text(
            "<b><blockquote expandable>You must join our channel(s) to use this bot.</b>",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML
        )

async def is_subscribed(client, user_id):
    fsub_channels = await get_fsub_channels()
    if not fsub_channels:
        return True

    for channel_id in fsub_channels:
        try:
            member = await client.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status not in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT]:
                continue
        except UserNotParticipant:
            pass
        return False
    return True

async def check_subscription_status(client, user_id, fsub_channels):
    is_subscribed = True
    subscription_message = "<b><blockquote expandable>You must join our channel(s) to use this bot.</b>"
    subscription_buttons = []

    for channel_id in fsub_channels:
        try:
            member = await client.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT]:
                is_subscribed = False
        except UserNotParticipant:
            is_subscribed = False
        
        if not is_subscribed:
            try:
                chat = await client.get_chat(channel_id)
                if chat.invite_link:
                    subscription_buttons.append([InlineKeyboardButton(chat.title, url=chat.invite_link)])
            except Exception as e:
                print(f"Error getting chat info for fsub channel {channel_id}: {e}")

    return is_subscribed, subscription_message, InlineKeyboardMarkup(subscription_buttons) if subscription_buttons else None

@Bot.on_callback_query()
async def cb_handler(client: Bot, query: CallbackQuery):
    user_id = query.from_user.id

    if query.data == "close":
        await query.message.delete()

    elif query.data == "about":
        await query.answer(
            "Bot by @Codeflix_Bots\n\n"            "Contact @CodeflixSupport for help.",
            show_alert=True
        )

    elif query.data == "channels":
        fsub_channels = await get_fsub_channels()
        if not fsub_channels:
            return await query.answer("No channels configured.", show_alert=True)

        buttons = []
        for channel_id in fsub_channels:
            chat = await get_chat_data(client, channel_id)
            if chat:
                buttons.append([InlineKeyboardButton(chat.title, url=chat.invite_link)])
        
        if buttons:
            await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
        else:
            await query.answer("Could not fetch channel information.", show_alert=True)

    elif query.data.startswith("ban_"): 
        try: 
            user_id = int(query.data.split("_")[1])
            await client.ban_chat_member(BANNED_CHANNEL, user_id)
            await query.answer("User Banned", show_alert=True)
        except Exception as e:
            await query.answer(f"Error: {e}", show_alert=True)

    elif query.data.startswith("unban_"):
        try:
            user_id = int(query.data.split("_")[1])
            await client.unban_chat_member(BANNED_CHANNEL, user_id)
            await query.answer("User Unbanned", show_alert=True)
        except Exception as e:
            await query.answer(f"Error: {e}", show_alert=True)

#=====================================================================================##
# Don't Remove Credit @CodeFlix_Bots, @rohit_1888
# Ask Doubt on telegram @CodeflixSupport

async def delete_after_delay(message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        print(f"Error deleting message: {e}")

#=====================================================================================##
# Don't Remove Credit @CodeFlix_Bots, @rohit_1888
# Ask Doubt on telegram @CodeflixSupport
'''
