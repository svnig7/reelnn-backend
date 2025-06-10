from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from utils.user.registeruser import UserRegistrationHandler
from utils.telegram_logger import send_info, send_error
from app import LOGGER
import config


registration_handler = UserRegistrationHandler()


@Client.on_message(filters.command("register", prefixes="/") & filters.private)
async def register_command(client: Client, message: Message):
    """Handle user registration command."""
    try:
        try:
            post_chat = client.get_chat_member(
                int(config.POST_CHAT), int(message.from_user.id)
            )
            mem_post_chat = str(post_chat.status)
        except Exception as e:
            mem_post_chat = "None"

        if mem_post_chat.lower() not in [
            "chatmemberstatus.owner",
            "chatmemberstatus.member",
            "chatmemberstatus.administrator",
            "chatmemberstatus.creator",
        ]:
            await message.reply(
                f"""You're not a part of <b>{config.SITE_NAME}</b> family. Please join this channel and try to register again 😊""",
                disable_web_page_preview=True,
                quote=True,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                f"{config.SITE_NAME} 🎬", url=f"{config.POST_CHAT_LINK}"
                            )
                        ]
                    ]
                ),
            )
            return

        if not config.ENABLE_REGISTRATION:
            await message.reply_text("❌ Registration is currently disabled.")
            return

        user = message.from_user

        if not user:
            await message.reply_text("❌ Unable to get user information.")
            return

        result = registration_handler.register_user_from_telegram(user)

        if result["status"] == "success":
            response_text = (
                f"✅ **Registration Successful!**\n\n"
                f"👤 **User ID:** `{result['user_id']}`\n"
                f"📅 **Registration Date:** {result['registration_date'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"🎬 **Subscribed for:** {result['slimit']} days\n\n"
                f"Welcome to reelnn! You can now access media files."
            )

            await send_info(
                client,
                f"✅ New user registered: {result['user_id']} ({user.first_name})",
            )
            LOGGER.info(f"User {result['user_id']} registered successfully")

        elif result["status"] == "already_exists":
            response_text = (
                f"ℹ️ **Already Registered!**\n\n"
                f"👤 **User ID:** `{result['user_id']}`\n"
                f"📅 **Registration Date:** {result['registration_date'].strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"You are already registered and can access media files."
            )

        else:
            response_text = (
                f"❌ Registration failed: {result.get('message', 'Unknown error')}"
            )
            await send_error(
                client,
                f"Registration failed for user {user.id}",
                Exception(result.get("message")),
            )
            LOGGER.error(
                f"Registration failed for user {user.id}: {result.get('message')}"
            )

        await message.reply_text(response_text)

    except Exception as e:
        error_message = (
            "❌ An error occurred during registration. Please try again later."
        )
        await message.reply_text(error_message)
        await send_error(
            client,
            f"Registration error for user {message.from_user.id if message.from_user else 'unknown'}",
            e,
        )
        LOGGER.error(f"Registration command error: {str(e)}")


@Client.on_message(filters.command("profile", prefixes="/") & filters.private)
async def profile_command(client: Client, message: Message):
    """Show user profile information."""
    try:
        user = message.from_user

        if not user:
            await message.reply_text("❌ Unable to get user information.")
            return

        result = registration_handler.get_user_info(user.id)

        if result["status"] == "found":
            user_data = result["user"]
            response_text = (
                f"👤 **Your Profile**\n\n"
                f"🆔 **User ID:** `{user_data['user_id']}`\n"
                f"👤 **Name:** {user_data.get('first_name', 'N/A')} {user_data.get('last_name', '') or ''}\n"
                f"📝 **Username:** @{user_data.get('username', 'N/A')}\n"
                f"📅 **Registered:** {user_data['registration_date'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"🎬 **Subscribed for:** {user_data.get('slimit', 30)} days\n"
                f"✅ **Status:** {'Active' if user_data.get('is_active', True) else 'Inactive'}"
            )
        else:
            response_text = (
                "❌ **Not Registered**\n\n"
                "You need to register first. Use /register command to get started."
            )

        await message.reply_text(response_text)

    except Exception as e:
        await message.reply_text("❌ An error occurred while fetching your profile.")
        LOGGER.error(f"Profile command error: {str(e)}")
