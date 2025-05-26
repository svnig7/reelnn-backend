from pyrogram import Client
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from utils.get_details import get_content_details
from utils.db_utils.show_db import ShowDatabase
from utils.db_utils.movie_db import MovieDatabase
from utils.utils import remove_redandent
from asyncio import sleep, create_task, Queue, Task
from app import LOGGER
import config
from utils.auto_poster import auto_poster
from utils.cache_manager import update_all_caches
from utils.telegram_logger import send_info, send_error, send_warning

message_queue = Queue()

worker_task: Task = None

movie_db = MovieDatabase()
show_db = ShowDatabase()


async def process_video(client: Client, message: Message, update_cache: bool):
    """Process a single video message."""
    try:
        file = message.video or message.document or message.animation
        if config.USE_CAPTION:
            title = message.caption or message.text
        else:
            title = file.file_name if file.file_name else file.file_id
        title = remove_redandent(title)

        try:
            _result = await get_content_details(title, client, message)
        except Exception as e:
            LOGGER.error(f"Error getting content details: {str(e)}")
            await send_error(client, f"Error getting content details for '{title}'", e)
            await message.reply_text(f"Error processing media: {str(e)}")
            return

        if not _result.get("success"):
            error_msg = _result.get("error", "Unknown error")
            LOGGER.error(f"Content details error: {error_msg}")
            await send_error(
                client, f"Content details error for '{title}': {error_msg}"
            )
            await message.reply_text(f"Error: {error_msg}")
            return

        media_details = _result["data"]
        media_type = _result["_type"]

        if media_type == "movie":
            LOGGER.info(f"Processing movie: {title}")

            try:
                upload_result = movie_db.upsert_movie(media_details)
                print(media_details)
                await send_info(
                    client,
                    f"✅ Movie **{media_details.get('title', 'Unknown')}** {upload_result['status']} successfully",
                )
                if update_cache:
                    LOGGER.info("Triggering cache update after movie addition")
                    create_task(update_all_caches())
            except Exception as e:
                LOGGER.error(f"Error uploading movie data: {str(e)}")
                await send_error(client, f"Error uploading movie data for '{title}'", e)
                await message.reply_text(f"Error uploading movie data: {str(e)}")

        elif media_type == "show":
            LOGGER.info(f"Processing show: {title}")
            try:
                upload_result = show_db.upsert_show(media_details)
                print(media_details)
                await send_info(
                    client,
                    f"✅ Show **{media_details.get('title', 'Unknown')}** {upload_result['status']} successfully",
                )
                if update_cache:
                    LOGGER.info("Triggering cache update after show addition")
                    create_task(update_all_caches())
            except Exception as e:
                LOGGER.error(f"Error uploading show data: {str(e)}")
                await send_error(client, f"Error uploading show data for '{title}'", e)
                await message.reply_text(f"Error uploading show data: {str(e)}")

        else:
            LOGGER.warning(f"Unsupported media type: {media_type}")
            await send_warning(
                client, f"⚠️ Unsupported media type: {media_type} for '{title}'"
            )
            await message.reply_text("Unsupported media type.")

        if config.POST_UPDATES:
            await auto_poster(client, message, media_details, media_type)

        LOGGER.debug(f"Media details: {media_details}")

    except FloodWait as e:
        LOGGER.warning(f"FloodWait error: {e.value}s")
        await send_warning(client, f"⚠️ FloodWait error: waiting for {e.value}s")
        await message.reply_text(f"Rate limit exceeded. Waiting for {e.value} seconds.")
        await sleep(e.value)
        # Re-queue the message to try again
        await message_queue.put((client, message))
    except Exception as e:
        LOGGER.error(f"Unexpected error: {str(e)}")
        await send_error(
            client,
            f"Unexpected error processing '{title if 'title' in locals() else 'unknown content'}'",
            e,
        )
        await message.reply_text(f"An unexpected error occurred: {str(e)}")


async def process_video_queue(update_cache: bool):
    """Worker that processes videos from the queue one by one."""
    while True:
        try:

            client, message = await message_queue.get()

            try:
                LOGGER.info(f"Processing queued video: {message.id}")
                await process_video(client, message, update_cache)

                await sleep(1)
            except Exception as e:
                LOGGER.error(f"Error processing queued video: {str(e)}")
            finally:

                message_queue.task_done()

        except Exception as e:
            LOGGER.error(f"Queue worker error: {str(e)}")
            await sleep(5)


@Client.on_message(filters.chat(config.AUTH_CHATS))
async def get_video(client: Client, message: Message):
    """Add video messages to the processing queue."""
    global worker_task

    if worker_task is None or worker_task.done():
        worker_task = create_task(process_video_queue(True))
        LOGGER.info("Started video processing worker")

    if not (message.video or message.document or message.animation):
        return

    await message_queue.put((client, message))

    file = message.video or message.document or message.animation
    title = file.file_name if file.file_name else "Unknown file"
    LOGGER.info(f"Queued video for processing: {title}")


async def shutdown():
    if worker_task and not worker_task.done():
        await message_queue.join()
        worker_task.cancel()
        try:
            await worker_task
        except:
            pass
