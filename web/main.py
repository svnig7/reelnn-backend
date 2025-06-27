from typing import List, Optional
from fastapi import FastAPI, Query, Request, HTTPException, Form, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from utils.db_utils.config_db import ConfigDatabase
import jwt
from fastapi.security import APIKeyQuery
from datetime import datetime
from fastapi.staticfiles import StaticFiles
from utils.api.search_results import get_cached_search_results
from utils.api.hero_slider import get_hero_slider_items
from utils.api.get_latest import get_latest_entries
from utils.api.getMovieDetails import get_movie_details
from utils.api.getShowDetalis import get_show_details
from utils.api.pagination import get_paginated_entries
from utils.api.get_trending import get_trending_entries
from utils.api.get_simillar import get_similar_by_genre
from utils.cache_manager import update_trending_cache
from pathlib import Path
from state import work_loads, multi_clients
from app import LOGGER
from utils.exceptions import InvalidHash
from utils.custom_dl import ByteStreamer
import math
import secrets
import mimetypes
from fastapi.responses import StreamingResponse
from config import SITE_SECRET
import time
from web.auth import verify_token, authenticate_user
from contextlib import asynccontextmanager
import asyncio
from utils.db_utils.user_db import UserDatabase

app = FastAPI()
class_cache = {}
token_query = APIKeyQuery(name="token", auto_error=False)

BASE_DIR = Path(__file__).resolve().parent
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)

templates_dir = BASE_DIR / "templates"
templates_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache_cleaner_task = asyncio.create_task(periodic_cache_cleanup())
    yield
    cache_cleaner_task.cancel()
    try:
        await cache_cleaner_task
    except asyncio.CancelledError:
        pass


async def periodic_cache_cleanup():
    while True:
        await asyncio.sleep(900)
        clean_cache()
        LOGGER.debug(f"Cache cleaned. Items remaining: {len(class_cache)}")


def verify_stream_token(token: str):
    try:
        decoded = jwt.decode(token, SITE_SECRET, algorithms=["HS256"])

        if "expiry" in decoded and decoded["expiry"] < datetime.now().timestamp():
            raise HTTPException(status_code=401, detail="Token has expired")

        return decoded
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


@app.post("/api/v1/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """Login and get access token."""
    token = await authenticate_user(username, password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": token, "token_type": "bearer"}
    

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def get_index():
    """Serve the admin interface for managing trending content"""
    with open(templates_dir / "index.html") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/v1/auth-check")
async def auth_check(token_data: dict = Depends(verify_token)):
    """Check if the user is authenticated"""
    return {"authenticated": True, "user": token_data.get("sub", "Unknown")}


@app.get("/api/v1/heroslider")
async def get_hero_slider(request: Request):
    items = get_hero_slider_items()
    return JSONResponse(content=items)


@app.get("/api/v1/getlatest/{media_type}")
async def get_latest(media_type: str, limit: int = Query(21, gt=0)):
    """
    Get the most recently added movie or show entries from the database.

    Args:
        media_type: String specifying "movie" or "show"
        limit: Number of entries to return (default: 8)

    Returns:
        List of movie or show dictionaries or error dict
    """
    items = get_latest_entries(media_type, limit)

    return JSONResponse(content=items)


@app.get("/api/v1/getMovieDetails/{mid}")
async def getmovie_details(mid: str):
    """
    Get movie details by movie ID (mid).

    Args:
        mid: The movie ID to look up

    Returns:
        Dictionary containing the requested movie fields or an error message
    """
    details = get_movie_details(mid)
    if not details:
        raise HTTPException(status_code=404, detail="Movie not found")
    return JSONResponse(content=details)


@app.get("/api/v1/getShowDetails/{sid}")
async def getshow_details(sid: str):
    """
    Get show details by show ID (sid).

    Args:
        sid: The show ID to look up

    Returns:
        Dictionary containing the requested show fields or an error message
    """
    details = get_show_details(sid)
    if not details:
        raise HTTPException(status_code=404, detail="Show not found")
    return JSONResponse(content=details)


@app.get("/api/v1/paginated/{media_type}")
async def get_paginated(
    media_type: str,
    page: int = Query(1, gt=0),
    items_per_page: int = Query(20, gt=0, le=100),
    sort_by: str = Query(
        "new", description="Sort by: new_release, most_rated, release_date"
    ),
):
    """
    Get paginated movie or show entries from the database.

    Args:
        media_type: String specifying "movie" or "show"
        page: Page number to retrieve (default: 1)
        items_per_page: Number of items per page (default: 20, max: 100)
        sort_by: Sorting method (default: "new_release")

    Returns:
        Dictionary containing items and pagination metadata
    """
    response = get_paginated_entries(media_type, page, items_per_page, sort_by)

    if "status" in response and response["status"] == "error":
        raise HTTPException(status_code=400, detail=response["message"])
    return JSONResponse(content=response)


@app.get("/api/v1/trending")
async def get_trending_items():
    """
    Get the currently configured trending movies and shows.

    Returns:
        Dictionary with 'movie' and 'show' keys containing formatted entry details
    """
    try:

        result = get_trending_entries()
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/search/{media_type}")
async def search_media(media_type: str, query: str = Query(..., min_length=2)):
    """
    Search for movies or shows by title

    Args:
        media_type: "movie" or "show"
        query: Search term (minimum 2 characters)

    Returns:
        List of matching items with basic details
    """
    if media_type not in ["movie", "show"]:
        raise HTTPException(
            status_code=400, detail="Media type must be 'movie' or 'show'"
        )

    try:
        if media_type == "movie":
            from utils.db_utils.movie_db import MovieDatabase

            db = MovieDatabase()
            results = db.find_movies_by_title(query)
        else:
            from utils.db_utils.show_db import ShowDatabase

            db = ShowDatabase()
            results = db.find_shows_by_title(query)

        processed_results = []
        id_field = "mid" if media_type == "movie" else "sid"

        if len(results) == 0:
            return JSONResponse(content=[])
        for item in results:
            year = None
            if "release_date" in item and item["release_date"]:
                try:
                    year = int(item["release_date"].split("-")[0])
                except (IndexError, ValueError, AttributeError):
                    pass

            processed_results.append(
                {
                    "id": item.get(id_field),
                    "title": item.get("title"),
                    "year": year,
                    "poster": item.get("poster_path"),
                    "vote_average": item.get("vote_average", 0),
                    "media_type": media_type,
                }
            )

        return JSONResponse(content=processed_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/update_trending")
async def update_trending(request: Request, token: str = Depends(token_query)):
    """
    Update the trending movies and shows

    Request body should be a JSON with:
    {
        "movie": [list of movie IDs],
        "show": [list of show IDs]
    }

    Returns:
        Success message or error
    """
    try:
        payload = await request.json()

        if (
            not isinstance(payload, dict)
            or "movie" not in payload
            or "show" not in payload
        ):
            raise ValueError("Payload must contain 'movie' and 'show' lists")

        movie_ids = [int(mid) for mid in payload.get("movie", [])]
        show_ids = [int(sid) for sid in payload.get("show", [])]

        config = ConfigDatabase()
        save_result = config.save_trending_config(movie_ids, show_ids)

        if save_result["status"] in ["inserted", "updated"]:
            update_trending_cache()
            result = get_trending_entries({"movie": movie_ids, "show": show_ids})
            return JSONResponse(content={"status": "success", "data": result})
        else:
            raise Exception(
                f"Failed to save trending configuration: {save_result.get('message', 'Unknown error')}"
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/similar")
async def get_similar_media(
    media_type: str = Query(..., description="Type of media: 'movie' or 'show'"),
    genres: List[str] = Query(
        ..., description="Genres to search for (max 2)", max_length=2
    ),
):
    """
    Find movies or shows that match specific genres.

    Args:
        media_type: "movie" or "show"
        genres: List of genre names to search for (max 2)

    Returns:
        List of media items matching at least one of the requested genres
    """
    if media_type not in ["movie", "show"]:
        raise HTTPException(
            status_code=400, detail="Media type must be 'movie' or 'show'"
        )

    if not genres or len(genres) > 2:
        raise HTTPException(status_code=400, detail="Must provide 1-2 genre keywords")

    try:
        results = get_similar_by_genre(media_type, genres)
        if not results:
            return JSONResponse(content=[])
        return JSONResponse(content=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/search")
async def search_all(
    query: str = Query(..., min_length=2, description="Search term"),
    limit: int = Query(20, ge=1, le=50, description="Maximum results per media type"),
):
    """
    Search across both movies and shows by title

    Args:
        query: Search term (minimum 2 characters)
        limit: Maximum number of results to return

    Returns:
        List of matching items with basic details from both movies and shows
    """
    if len(query) < 2:
        return JSONResponse(content=[])

    try:
        results = await get_cached_search_results(query, limit)
        return JSONResponse(content=results)
    except Exception as e:
        LOGGER.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/api/v1/dl/{id}")
async def stream_handler(
    request: Request,
    id: str,
    token: str = Query(None, description="JWT stream token"),
    media_type: str = Query(None, description="Type of media: 'movie' or 'show'"),
    quality_index: int = Query(
        None, description="Index of the quality option to select"
    ),
    season_number: Optional[int] = Query(
        None, description="Season number (required for shows)"
    ),
    episode_number: Optional[int] = Query(
        None, description="Episode number (required for shows)"
    ),
):
    """
    Stream movie or show content using JWT token authentication.
    """

    if not token:
        raise HTTPException(status_code=401, detail="Stream token required")

    try:
        token_data = verify_stream_token(token)

        token_id = token_data.get("id")
        token_media_type = token_data.get("mediaType")
        token_quality_index = token_data.get("qualityIndex", 0)
        token_season_number = token_data.get("seasonNumber")
        token_episode_number = token_data.get("episodeNumber")

        if token_id != id:
            raise HTTPException(status_code=401, detail="Token ID mismatch")

        media_type = token_media_type
        quality_index = token_quality_index
        season_number = token_season_number
        episode_number = token_episode_number

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation error: {str(e)}")

    try:

        from utils.api.get_video import get_video_details

        file_details = await get_video_details(
            id, media_type, quality_index, season_number, episode_number
        )

        msg_id = file_details["msg_id"]
        chat_id = f"{file_details['chat_id']}"
        file_hash = file_details["hash"]

        try:
            return await media_streamer(request, int(chat_id), int(msg_id), file_hash)
        except TimeoutError:

            raise HTTPException(
                status_code=503,
                detail="Streaming service temporarily unavailable. Please try again in a few moments.",
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error streaming content: {str(e)}"
        )

# Credits:
# This code is adapted from TechZIndex by TechShreyash (GitHub Username)
# Source: https://github.com/TechShreyash/TechZIndex
# Also thanks to https://github.com/weebzone/Surf-TG for some optimizations


async def media_streamer(request: Request, chat_id: int, id: int, secure_hash: str):
    range_header = request.headers.get("Range", 0)

    if not work_loads:
        LOGGER.warning("No clients available in work_loads dictionary")

    index = min(work_loads, key=work_loads.get)

    faster_client = multi_clients[index]

    if index not in multi_clients:
        LOGGER.error(
            f"Client index {index} found in work_loads but not in multi_clients"
        )
        raise HTTPException(
            status_code=503, detail="Streaming client configuration error"
        )

    LOGGER.debug(f"Client {index} is now serving {request.client.host}")

    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]["object"]
        LOGGER.debug(f"Using cached ByteStreamer object for client {index}")
    else:
        LOGGER.debug(f"Creating new ByteStreamer object for client {index}")
        tg_connect = ByteStreamer(faster_client)
        class_cache[faster_client] = {"object": tg_connect, "timestamp": time.time()}

    LOGGER.debug("before calling get_file_properties")
    try:
        file_id = await tg_connect.get_file_properties(chat_id=chat_id, message_id=id)
    except Exception as e:
        LOGGER.error(f"Error getting file properties: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving file: {str(e)}")

    LOGGER.debug("after calling get_file_properties")

    if file_id.unique_id[:6] != secure_hash:
        LOGGER.debug(f"Invalid hash for message with ID {id}")
        raise InvalidHash

    file_size = file_id.file_size
    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = 0
        until_bytes = file_size - 1
    if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
        return StreamingResponse(
            content=(f"416: Range not satisfiable",),
            status_code=416,
            headers={"Content-Range": f"bytes */{file_size}"},
        )
    chunk_size = min(1024 * 1024, max(1024, file_size // 10))
    until_bytes = min(until_bytes, file_size - 1)

    offset = from_bytes - (from_bytes % chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = until_bytes % chunk_size + 1

    req_length = until_bytes - from_bytes + 1
    part_count = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)
    body = tg_connect.yield_file(
        file_id, index, offset, first_part_cut, last_part_cut, part_count, chunk_size
    )
    mime_type = file_id.mime_type
    file_name = file_id.file_name
    disposition = "inline"

    if mime_type:
        if not file_name:
            try:
                file_name = f"{secrets.token_hex(2)}.{mime_type.split('/')[1]}"
            except (IndexError, AttributeError):
                file_name = f"{secrets.token_hex(2)}.unknown"
    else:
        if file_name:
            mime_type = mimetypes.guess_type(file_name)[0]
        else:
            mime_type = "application/octet-stream"
            file_name = f"{secrets.token_hex(2)}.unknown"

    return StreamingResponse(
        status_code=206 if range_header else 200,
        content=body,
        headers={
            "Content-Type": f"{mime_type}",
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Content-Type",
        },
    )


def clean_cache():
    current_time = time.time()
    expired_keys = [
        k for k, v in class_cache.items() if current_time - v["timestamp"] > 3600
    ]
    for key in expired_keys:
        del class_cache[key]


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve the login page."""
    with open(templates_dir / "login.html") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/v1/users")
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    token: str = Depends(token_query),
):
    """Get all users with pagination"""
    try:
        user_db = UserDatabase()
        users = user_db.get_all_users(skip=skip, limit=limit)

        if not isinstance(users, list):
            users = []

        for user in users:
            if "_id" in user:
                user["_id"] = str(user["_id"])

        return {"users": users, "count": len(users)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")


@app.get("/api/v1/users/search")
async def search_users(
    query: str = Query(..., min_length=1), token: str = Depends(token_query)
):
    """Search users by username, first name, or user ID"""
    try:
        user_db = UserDatabase()
        users = user_db.search_users(query)

        if not isinstance(users, list):
            users = []

        for user in users:
            if "_id" in user:
                user["_id"] = str(user["_id"])

        return {"users": users, "count": len(users)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.put("/api/v1/users/{user_id}")
async def update_user(
    user_id: int, request: Request, token: str = Depends(token_query)
):
    """Update user information"""
    try:
        payload = await request.json()

        if "user_id" in payload:
            del payload["user_id"]

        user_db = UserDatabase()
        result = user_db.update_user(user_id, payload)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@app.delete("/api/v1/users/{user_id}")
async def delete_user(user_id: int, token: str = Depends(token_query)):
    """Delete user"""
    try:
        user_db = UserDatabase()
        result = user_db.delete_user(user_id)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@app.put("/api/v1/updateMovie/{movie_id}")
async def update_movie(
    movie_id: int, request: Request, token: str = Depends(token_query)
):
    """Update movie information"""
    try:
        payload = await request.json()

        from utils.db_utils.movie_db import MovieDatabase

        movie_db = MovieDatabase()

        existing_movie = movie_db.find_movie_by_id(movie_id)
        if not existing_movie:
            raise HTTPException(status_code=404, detail="Movie not found")

        for field, value in payload.items():
            existing_movie[field] = value

        result = movie_db.movies_collection.update_one(
            {"mid": movie_id}, {"$set": payload}
        )

        if result.modified_count > 0:
            return {"status": "success", "message": "Movie updated successfully"}
        else:
            return {"status": "no_changes", "message": "No changes made"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@app.post("/api/v1/checkUser")
async def check_user_endpoint(request: Request):
    """
    Check if a user exists in the database using JWT token.

    Expects JSON payload with:
    {
        "token": "jwt_token_containing_user_id"
    }

    Returns:
        User details if found, error message otherwise
    """
    try:
        payload = await request.json()
        token = payload.get("token")

        if not token:
            raise HTTPException(status_code=400, detail="Token is required")

        try:
            decoded = jwt.decode(token, SITE_SECRET, algorithms=["HS256"])
            print(decoded)
            user_id = decoded.get("user_id")

            if not user_id:
                raise HTTPException(
                    status_code=400, detail="Token does not contain user_id"
                )

        except jwt.PyJWTError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

        from utils.api.checkUser import check_user

        result = check_user(int(user_id))
        print(result)

        if result["status"] == "success":
            return JSONResponse(content=result)
        elif result["status"] == "not_found":
            raise HTTPException(status_code=404, detail=result["message"])
        else:
            raise HTTPException(status_code=500, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.put("/api/v1/updateShow/{show_id}")
async def update_show(
    show_id: int, request: Request, token: str = Depends(token_query)
):
    """Update show information"""
    try:
        payload = await request.json()

        from utils.db_utils.show_db import ShowDatabase

        show_db = ShowDatabase()

        existing_show = show_db.find_show_by_id(show_id)
        if not existing_show:
            raise HTTPException(status_code=404, detail="Show not found")

        for field, value in payload.items():
            existing_show[field] = value

        result = show_db.shows_collection.update_one(
            {"sid": show_id}, {"$set": payload}
        )

        if result.modified_count > 0:
            return {"status": "success", "message": "Show updated successfully"}
        else:
            return {"status": "no_changes", "message": "No changes made"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
