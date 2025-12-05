# Ban System Plugin
# Modified By: @Codeflix_Bots
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from config import OWNER_ID
from database.database import ban_user, unban_user, get_banned_users, is_admin
from helper_func import is_owner_or_admin

@Client.on_message(filters.command("ban") & is_owner_or_admin)
async def ban_command(client: Client, message: Message):
    """Ban a user from using the bot."""
    print(f"[v0] Ban command triggered by user {message.from_user.id}")
    
    # Check if command is used as a reply
    if not message.reply_to_message:
        # Check if user ID is provided
        if len(message.command) >= 2:
            try:
                target_user_id = int(message.command[1])
                reason = " ".join(message.command[2:]) if len(message.command) > 2 else None
                
                # Prevent banning owner
                if target_user_id == OWNER_ID:
                    return await message.reply_text(
                        "<b>❌ Cannot ban the bot owner!</b>",
                        parse_mode=ParseMode.HTML
                    )
                
                # Prevent banning admins
                if await is_admin(target_user_id):
                    return await message.reply_text(
                        "<b>❌ Cannot ban an admin!</b>",
                        parse_mode=ParseMode.HTML
                    )
                
                # Try to get user info
                try:
                    target_user = await client.get_users(target_user_id)
                    target_user_name = target_user.first_name
                except:
                    target_user_name = "Unknown User"
                
                # Ban the user
                success = await ban_user(target_user_id, message.from_user.id, reason)
                
                if success:
                    user_mention = f'<a href="tg://user?id={target_user_id}">{target_user_name}</a>'
                    reason_text = f"\n<b>Reason:</b> {reason}" if reason else ""
                    await message.reply_text(
                        f"🚫 <b>USER BANNED</b>\n\n"
                        f"<b>User:</b> {user_mention}\n"
                        f"<b>User ID:</b> <code>{target_user_id}</code>\n"
                        f"<b>Banned by:</b> {message.from_user.mention}"
                        f"{reason_text}",
                        parse_mode=ParseMode.HTML
                    )
                    print(f"[v0] User {target_user_id} banned successfully")
                else:
                    await message.reply_text(
                        "<b>❌ Failed to ban user. Please try again.</b>",
                        parse_mode=ParseMode.HTML
                    )
                    print(f"[v0] Failed to ban user {target_user_id}")
                return
            except ValueError:
                pass
        
        return await message.reply_text(
            "<b>Usage:</b>\n"
            "• Reply to a user's message: <code>/ban [reason]</code>\n"
            "• Or use: <code>/ban {user_id} [reason]</code>",
            parse_mode=ParseMode.HTML
        )
    
    target_user = message.reply_to_message.from_user
    if not target_user:
        return await message.reply_text(
            "<b>❌ Unable to identify user.</b>",
            parse_mode=ParseMode.HTML
        )
    
    target_user_id = target_user.id
    
    # Prevent banning owner
    if target_user_id == OWNER_ID:
        return await message.reply_text(
            "<b>❌ Cannot ban the bot owner!</b>",
            parse_mode=ParseMode.HTML
        )
    
    # Prevent banning admins
    if await is_admin(target_user_id):
        return await message.reply_text(
            "<b>❌ Cannot ban an admin!</b>",
            parse_mode=ParseMode.HTML
        )
    
    # Get reason if provided
    reason = None
    if len(message.text.split(None, 1)) > 1:
        reason = message.text.split(None, 1)[1]
    
    # Ban the user
    success = await ban_user(target_user_id, message.from_user.id, reason)
    
    if success:
        user_mention = f'<a href="tg://user?id={target_user_id}">{target_user.first_name}</a>'
        reason_text = f"\n<b>Reason:</b> {reason}" if reason else ""
        await message.reply_text(
            f"🚫 <b>USER BANNED</b>\n\n"
            f"<b>User:</b> {user_mention}\n"
            f"<b>User ID:</b> <code>{target_user_id}</code>\n"
            f"<b>Banned by:</b> {message.from_user.mention}"
            f"{reason_text}",
            parse_mode=ParseMode.HTML
        )
        print(f"[v0] User {target_user_id} banned successfully")
    else:
        await message.reply_text(
            "<b>❌ Failed to ban user. Please try again.</b>",
            parse_mode=ParseMode.HTML
        )
        print(f"[v0] Failed to ban user {target_user_id}")

@Client.on_message(filters.command("unban") & is_owner_or_admin)
async def unban_command(client: Client, message: Message):
    """Unban a user."""
    print(f"[v0] Unban command triggered by user {message.from_user.id}")
    
    # Check if command is used as a reply or with user ID
    target_user_id = None
    target_user_name = None
    
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        if target_user:
            target_user_id = target_user.id
            target_user_name = target_user.first_name
    elif len(message.command) == 2 and message.command[1].isdigit():
        target_user_id = int(message.command[1])
        try:
            user = await client.get_users(target_user_id)
            target_user_name = user.first_name
        except:
            target_user_name = "Unknown"
    else:
        return await message.reply_text(
            "<b>Usage:</b>\n"
            "• Reply to a user's message: <code>/unban</code>\n"
            "• Or use: <code>/unban {user_id}</code>",
            parse_mode=ParseMode.HTML
        )
    
    if not target_user_id:
        return await message.reply_text(
            "<b>❌ Unable to identify user.</b>",
            parse_mode=ParseMode.HTML
        )
    
    # Unban the user
    success = await unban_user(target_user_id)
    
    if success:
        user_mention = f'<a href="tg://user?id={target_user_id}">{target_user_name}</a>'
        await message.reply_text(
            f"✅ <b>USER UNBANNED</b>\n\n"
            f"<b>User:</b> {user_mention}\n"
            f"<b>User ID:</b> <code>{target_user_id}</code>\n"
            f"<b>Unbanned by:</b> {message.from_user.mention}",
            parse_mode=ParseMode.HTML
        )
        print(f"[v0] User {target_user_id} unbanned successfully")
    else:
        await message.reply_text(
            "<b>❌ Failed to unban user. User might not be banned.</b>",
            parse_mode=ParseMode.HTML
        )
        print(f"[v0] Failed to unban user {target_user_id}")

@Client.on_message(filters.command("banlist") & is_owner_or_admin)
async def banlist_command(client: Client, message: Message):
    """Show all banned users with clickable names."""
    print(f"[v0] Banlist command triggered by user {message.from_user.id}")
    
    banned_users = await get_banned_users()
    
    if not banned_users:
        return await message.reply_text(
            "<b>✅ No banned users found.</b>",
            parse_mode=ParseMode.HTML
        )
    
    # Build the banlist message
    banlist_text = "🚫 <b>𝗕𝗔𝗡𝗡𝗘𝗗 𝗨𝗦𝗘𝗥 𝗟𝗜𝗦𝗧 :</b>\n\n"
    
    for banned_user in banned_users:
        user_id = banned_user['_id']
        
        # Try to get user details
        try:
            user = await client.get_users(user_id)
            user_name = user.first_name
            if user.last_name:
                user_name += f" {user.last_name}"
            
            # Add formatted user info with clickable name
            banlist_text += f"<b>NAME:</b> <a href=\"tg://user?id={user_id}\">{user_name}</a>\n"
            banlist_text += f"<b>(ID: {user_id})</b>\n\n"
            
        except Exception as e:
            print(f"[v0] Failed to get user info for {user_id}: {e}")
            # If unable to fetch user details
            banlist_text += f"<b>ɪᴅ:</b> <code>{user_id}</code>\n"
            banlist_text += f"<b>ᴜɴᴀʙʟᴇ ᴛᴏ ʟᴏᴀᴅ ᴏᴛʜᴇʀ ᴅᴇᴛᴀɪʟs..</b>\n\n"
    
    # Add total count
    banlist_text += f"<b>━━━━━━━━━━━━━━━\nTotal Banned: {len(banned_users)}</b>"
    
    await message.reply_text(
        banlist_text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )
    print(f"[v0] Banlist sent with {len(banned_users)} users")
