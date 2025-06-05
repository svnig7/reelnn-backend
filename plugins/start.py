from pyrogram import Client, filters
from pyrogram.types import Message
from utils.db_utils.movie_db import MovieDatabase
from utils.db_utils.show_db import ShowDatabase
import asyncio
import logging
import config

scheduled_deletions = {}



async def delete_after_delay(client, chat_id, message_id, delay_seconds):
    """Delete a message after specified delay"""
    try:
        await asyncio.sleep(delay_seconds)
        await client.delete_messages(chat_id, message_id)
        logging.info(f"Auto-deleted message {message_id} in chat {chat_id}")
        
        if (chat_id, message_id) in scheduled_deletions:
            del scheduled_deletions[(chat_id, message_id)]
    except Exception as e:
        logging.error(f"Error deleting message {message_id} in chat {chat_id}: {str(e)}")

LINK_FLITER = filters.private & filters.create(
    lambda _, __, msg: msg.text and msg.text.startswith("/start file_")
)


@Client.on_message(LINK_FLITER, -2)
async def forward_(client: Client, message: Message):
    try:
        
        processing_msg = await message.reply_text("Processing your request, please wait...")
        
        token = message.text.split("file_")[1]
        details = token.split("_")
        
        if len(details) < 5:
            await processing_msg.edit_text("Invalid file link format.")
            return
            
        id = details[0]
        media_type = details[1]
        quality = details[2]
        season = details[3]
        episode = details[4]

        if media_type == "m":  
            movie_db = MovieDatabase()
            try:
                movie = movie_db.find_movie_by_id(int(id))
                if not movie:
                    await processing_msg.edit_text("Sorry, movie not found.")
                    return
                    
                
                file_data = movie["quality"][int(quality)]
                
                        
                if not file_data or "msg_id" not in file_data or "chat_id" not in file_data:
                    await processing_msg.edit_text(f"Sorry, {quality} quality not available for this movie.")
                    return
                
                
                await processing_msg.edit_text("Found your file! Forwarding it now...")
                
                
                forwarded_msg = await client.forward_messages(
                    chat_id=message.chat.id,
                    from_chat_id=file_data["chat_id"],
                    message_ids=file_data["msg_id"],
                    drop_author=True
                )
                
                
                task = asyncio.create_task(delete_after_delay(client, message.chat.id, forwarded_msg.id, 60*config.DELETE_AFTER_MINUTES))
                scheduled_deletions[(message.chat.id, forwarded_msg.id)] = task

                await message.reply_text("Please forward this file to your saved messages. This file will be deleted in 10 minutes.")
                
                
                await processing_msg.delete()
                
            finally:
                pass
                
        elif media_type == "s":  
            show_db = ShowDatabase()
            try:
                show = show_db.find_show_by_id(int(id))
                if not show:
                    await processing_msg.edit_text("Sorry, show not found.")
                    return
                    
                
                season_data = None
                for s in show.get("season", []):
                    if s["season_number"] == int(season):
                        season_data = s
                        break
                        
                if not season_data:
                    await processing_msg.edit_text(f"Sorry, season {season} not found for this show.")
                    return
                    
                
                episode_data = None
                for e in season_data.get("episodes", []):
                    if e["episode_number"] == int(episode):
                        episode_data = e
                        break
                        
                if not episode_data:
                    await processing_msg.edit_text(f"Sorry, episode {episode} not found in season {season}.")
                    return
                    
                
                file_data = episode_data["quality"][int(quality)]
                
                        
                if not file_data or "msg_id" not in file_data or "chat_id" not in file_data:
                    await processing_msg.edit_text(f"Sorry, {quality} quality not available for this episode.")
                    return
                
                
                await processing_msg.edit_text("Found your file! Forwarding it now...")
                
                
                forwarded_msg = await client.forward_messages(
                    chat_id=message.chat.id,
                    from_chat_id=file_data["chat_id"],
                    message_ids=file_data["msg_id"],
                    drop_author=True
                )
                
                
                task = asyncio.create_task(delete_after_delay(client, message.chat.id, forwarded_msg.id, 60*config.DELETE_AFTER_MINUTES))
                scheduled_deletions[(message.chat.id, forwarded_msg.id)] = task

                #await message.reply_text("Please forward this file to your saved messages. This file will be deleted in 10 minutes.")
                
                
                await processing_msg.delete()
                
            finally:
                pass
                
        else:
            await processing_msg.edit_text("Invalid media type. Expected 'm' for movie or 's' for show.")
            
    except Exception as e:
        if 'processing_msg' in locals():
            await processing_msg.edit_text(f"Sorry, an error occurred while processing your request.")
        else:
            await message.reply_text(f"Sorry, an error occurred while processing your request.")


# @Client.on_message(filters.command("start", prefixes="/") & filters.private)
# async def start_command(client: Client, message: Message):
#     await message.reply_text("Hello! I am your bot. How can I assist you today?")

