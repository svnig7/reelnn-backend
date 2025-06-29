import PTN
from typing import Dict, Any, Optional, TypedDict
from utils.tmdb import fetch_movie_tmdb_data, fetch_tv_tmdb_data
from utils.mediainfo import media_quality
from utils.utils import get_readable_file_size
from app import LOGGER
from utils.models.show_model import ShowSchema
from utils.models.movie_model import MovieSchema
from pyrogram.types import Message
from pyrogram import Client

class ContentResult(TypedDict):
    success: bool
    data: Optional[Dict[str, Any]]
    _type: Optional[str]
    error: Optional[str]

async def get_movie_details(title: str, client: Client, year: Optional[int], message: Message) -> ContentResult:
    """Fetch and process movie details from TMDb API"""
    try:
        
        tmdb_result = await fetch_movie_tmdb_data(title, year)
        
        if not tmdb_result["success"]:
            return {"success": False, "error": tmdb_result["error"], "data": None, "_type": None}
        
        
        movie_quality, media_info = await media_quality(client, message)
        
        
        file = message.video or message.document or message.animation
        movie_dict = tmdb_result["data"].copy()
        movie_dict["quality"] = [{
            "type": f"{movie_quality}",
            "file_hash": file.file_unique_id[:6],
            "msg_id": message.id,
            "chat_id": message.chat.id, 
            "size": f"{get_readable_file_size(file.file_size)}", 
            "audio": media_info["audio"] if media_info["audio"] else "N/A", 
            "video_codec": media_info["video_codec"] if media_info["video_codec"] else "N/A", 
            "file_type": media_info["file_type"] if media_info["file_type"] else "N/A", 
            "subtitle": media_info["subtitle"] if media_info["subtitle"] else "N/A"
        }]
        
        try:
            validated_movie = MovieSchema(**movie_dict)
            validated_data = validated_movie.model_dump()
            return {"success": True, "data": validated_data, "_type": "movie", "error": None}
        except Exception as validation_error:
            LOGGER.error(f"Schema validation error: {str(validation_error)}")
            return {"success": False, "error": f"Data validation failed: {str(validation_error)}", 
                    "data": None, "_type": None}
    except Exception as e:
        LOGGER.error(f"Error in get_movie_details: {str(e)}")
        return {"success": False, "error": f"Failed to process movie data: {str(e)}", "data": None, "_type": None}

async def get_tv_details(title: str, client: Client, season: int, episode: int, message: Message) -> ContentResult:
    """Fetch and process TV show details from TMDb API"""
    try:
        
        tmdb_result = await fetch_tv_tmdb_data(title, season, episode)
        
        if not tmdb_result["success"]:
            return {"success": False, "error": tmdb_result["error"], "data": None, "_type": None}
        
        
        quality_type, media_info = await media_quality(client, message)
        
        
        file = message.video or message.document or message.animation
        tv_dict = tmdb_result["data"].copy()
        
        
        tv_dict["season"][0]["episodes"][0]["quality"] = [{
            "type": quality_type,
            "file_hash": file.file_unique_id[:6],
            "msg_id": message.id,
            "chat_id": message.chat.id,
            "size": get_readable_file_size(file.file_size),
            "audio": media_info["audio"] if media_info["audio"] else "N/A",
            "video_codec": media_info["video_codec"] if media_info["video_codec"] else "N/A",
            "file_type": media_info["file_type"] if media_info["file_type"] else "N/A",
            "subtitle": media_info["subtitle"] if media_info["subtitle"] else "N/A",
            "runtime": tv_dict["season"][0]["episodes"][0]["runtime"],
        }]
        
        try:
            validated_show = ShowSchema(**tv_dict)
            validated_data = validated_show.model_dump()
            return {"success": True, "data": validated_data, "_type": "show", "error": None}
        except Exception as validation_error:
            LOGGER.error(f"Schema validation error: {str(validation_error)}")
            return {"success": False, "error": f"Data validation failed: {str(validation_error)}", 
                    "data": None, "_type": None}
    except Exception as e:
        LOGGER.error(f"Error in get_tv_details: {str(e)}")
        return {"success": False, "error": f"Failed to process TV data: {str(e)}", "data": None, "_type": None}

async def get_content_details(mtitle: str, client: Client, message: Message) -> ContentResult:
    """Parse media filename and fetch detailed information from TMDb."""
    LOGGER.info(f"Processing content: {mtitle}")
    
    try:
        
        parsed_data = PTN.parse(mtitle)
        
        if not parsed_data.get("title"):
            return {"success": False, "error": "Could not parse title from filename", "data": None, "_type": None}
            
        title = parsed_data.get("title").replace("_", " ").replace("-", " ").replace(":", " ")
        title = ' '.join(title.split())
        year = parsed_data.get("year")
        season = parsed_data.get("season")
        episode = parsed_data.get("episode")
        
        LOGGER.info(f"Parsed: Title='{title}', Year={year}, Season={season}, Episode={episode}")
        
        
        if season is None:
            return await get_movie_details(title, client, year, message)
        elif episode is None:
            return {"success": False, "error": "Episode number not found in filename", "data": None, "_type": None}
        else:
            return await get_tv_details(title, client, season, episode, message)
            
    except Exception as e:
        LOGGER.error(f"Unexpected error in get_content_details: {str(e)}")
        return {"success": False, "error": f"Failed to process content: {str(e)}", "data": None, "_type": None}
