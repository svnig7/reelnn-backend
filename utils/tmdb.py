import asyncio
import functools
import re
from typing import Dict, Any, Optional, TypedDict
from themoviedb import aioTMDb
from app import LOGGER
from utils.utils import get_official_trailer_url
from config import TMDB_API_KEY

tmdb = aioTMDb(key=TMDB_API_KEY, language="en-US", region="US")

class TMDbResult(TypedDict):
    """Type definition for TMDb API results"""
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]

def async_lru_cache(maxsize=128, typed=False):
    def decorator(fn):
        _cache = {}

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            if key in _cache:
                return _cache[key]
            result = await fn(*args, **kwargs)
            if len(_cache) >= maxsize:
                _cache.pop(next(iter(_cache)))
            _cache[key] = result
            return result

        return wrapper
    return decorator

# ========================
# COMMON HELPER FUNCTIONS
# ========================

async def _fetch_logos(media_type: str, media_id: int) -> str:
    """Fetch logos for either movie or TV"""
    try:
        images = await getattr(tmdb, media_type)(media_id).images()
        if hasattr(images, "logos") and images.logos:
            en_logos = [logo for logo in images.logos if hasattr(logo, "iso_639_1") and logo.iso_639_1 == "en"]
            in_logos = [logo for logo in images.logos if hasattr(logo, "iso_639_1") and logo.iso_639_1 == "in"]
            return (
                en_logos[0].file_path if en_logos
                else in_logos[0].file_path if in_logos
                else ""
            )
    except Exception as e:
        LOGGER.warning(f"Error fetching logos for {media_type} {media_id}: {str(e)}")
    return ""

async def _fetch_external_ids(media_type: str, media_id: int) -> Dict[str, str]:
    """Fetch external IDs for either movie or TV"""
    try:
        ids = await getattr(tmdb, media_type)(media_id).external_ids()
        return {k: v for k, v in vars(ids).items() if not k.startswith('_') and v}
    except Exception as e:
        LOGGER.warning(f"Error fetching external IDs for {media_type} {media_id}: {str(e)}")
    return {}

# ========================
# MOVIE-SPECIFIC FUNCTIONS
# ========================

async def fetch_movie_by_tmdb_id(movie_id: int) -> TMDbResult:
    """Fetch movie details by TMDB ID"""
    try:
        movie_data = {
            "mid": movie_id,
            "title": "",
            "trailer": "",
            "original_title": "",
            "release_date": None,
            "overview": "",
            "poster_path": "",
            "directors": [],
            "backdrop_path": "",
            "runtime": 0,
            "popularity": 0,
            "vote_average": 0,
            "vote_count": 0,
            "cast": [],
            "logo": "",
            "genres": [],
            "studios": [],
            "links": [f"https://www.themoviedb.org/movie/{movie_id}"],
        }

        # Fetch basic details
        try:
            details = await tmdb.movie(movie_id).details()
            movie_data.update({
                "title": getattr(details, "title", ""),
                "original_title": getattr(details, "original_title", ""),
                "release_date": str(details.release_date) if hasattr(details, "release_date") and details.release_date else None,
                "overview": getattr(details, "overview", ""),
                "poster_path": getattr(details, "poster_path", "") or "",
                "backdrop_path": getattr(details, "backdrop_path", "") or "",
                "runtime": getattr(details, "runtime", 0) or 0,
                "popularity": getattr(details, "popularity", 0) or 0,
                "vote_average": getattr(details, "vote_average", 0) or 0,
                "vote_count": getattr(details, "vote_count", 0) or 0,
                "genres": [genre.name for genre in getattr(details, "genres", []) if hasattr(genre, "name")],
                "studios": [
                    getattr(company, "name", "")
                    for company in getattr(details, "production_companies", [])
                    if hasattr(company, "name")
                ],
            })
        except Exception as e:
            LOGGER.warning(f"Error fetching movie details for ID {movie_id}: {str(e)}")

        # Fetch additional data
        movie_data["logo"] = await _fetch_logos("movie", movie_id)
        
        external_ids = await _fetch_external_ids("movie", movie_id)
        if external_ids.get("imdb_id"):
            movie_data["links"].append(f"https://www.imdb.com/title/{external_ids['imdb_id']}")

        try:
            casts = await tmdb.movie(movie_id).credits()
            if hasattr(casts, "cast"):
                movie_data["cast"] = [
                    {
                        "name": getattr(actor, "name", ""),
                        "imageUrl": getattr(actor, "profile_path", "") or "",
                        "character": getattr(actor, "character", "") or "",
                    }
                    for actor in casts.cast[:20]
                    if hasattr(actor, "name")
                ]

            if hasattr(casts, "crew"):
                movie_data["directors"] = [
                    getattr(member, "name", "")
                    for member in casts.crew
                    if hasattr(member, "job")
                    and member.job == "Director"
                    and hasattr(member, "name")
                ]
        except Exception as e:
            LOGGER.warning(f"Error fetching cast/crew for movie ID {movie_id}: {str(e)}")

        await asyncio.sleep(1)

        try:
            videos = await tmdb.movie(movie_id).videos()
            movie_data["trailer"] = get_official_trailer_url(videos) or ""
        except Exception as e:
            LOGGER.warning(f"Error fetching videos for movie ID {movie_id}: {str(e)}")

        return {"success": True, "data": movie_data, "error": None}
    except Exception as e:
        LOGGER.error(f"Error fetching movie details for ID {movie_id}: {str(e)}")
        return {"success": False, "data": None, "error": f"TMDb API error: {str(e)}"}

def parse_movie_filename(filename: str) -> tuple:
    """
    Parse movie filename to extract ID/title and year
    
    Returns tuple: (identifier, title, year, is_id)
    """
    # Try ID + title + year pattern (e.g., "123456 Movie Title 2023")
    match = re.match(r"^(\d+)\s+(.+?)\s+(\d{4})", filename)
    if match:
        return match.group(1), match.group(2), int(match.group(3)), True
    
    # Try title + year patterns
    match = re.match(r"^(.+?)\s*\((\d{4})\)", filename)  # "Title (2023)"
    if not match:
        match = re.match(r"^(.+?)\s+(\d{4})", filename)  # "Title 2023"
    if not match:
        match = re.match(r"^(.+?)\.(\d{4})", filename)  # "Title.2023"
    
    if match:
        title = match.group(1).replace('.', ' ').strip()
        return None, title, int(match.group(2)), False
    
    # Try ID-only pattern
    if filename.strip().isdigit():
        return filename.strip(), None, None, True
    
    # Fallback to title only
    return None, filename.strip(), None, False

@async_lru_cache(maxsize=100)
async def fetch_movie_tmdb_data(
    identifier: Optional[str] = None,
    title: Optional[str] = None,
    year: Optional[int] = None
) -> TMDbResult:
    """Fetch movie data using either ID or title"""
    try:
        # Try ID first if available
        if identifier:
            try:
                result = await fetch_movie_by_tmdb_id(int(identifier))
                if result["success"]:
                    return result
                LOGGER.warning(f"ID {identifier} lookup failed, falling back to title search")
            except ValueError:
                pass  # Not a valid ID
        
        # Fall back to title search
        if title:
            search = await tmdb.search().movies(query=title, year=year)
            
            if not search or not hasattr(search, "results") or len(search.results) == 0:
                return {
                    "success": False,
                    "data": None,
                    "error": f"No movie found for '{title}'" + (f" ({year})" if year else ""),
                }

            movie_id = search.results[0].id
            return await fetch_movie_by_tmdb_id(movie_id)
        
        return {
            "success": False,
            "data": None,
            "error": "No valid identifier or title provided"
        }
    except Exception as e:
        LOGGER.error(f"Error fetching movie details: {str(e)}")
        return {"success": False, "data": None, "error": f"TMDb API error: {str(e)}"}

async def process_movie_file(filename: str) -> TMDbResult:
    """Complete movie filename processing pipeline"""
    identifier, title, year, is_id = parse_movie_filename(filename)
    return await fetch_movie_tmdb_data(
        identifier=identifier,
        title=title,
        year=year
    )

# ======================
# TV-SPECIFIC FUNCTIONS
# ======================

def parse_tv_filename(filename: str) -> tuple:
    """
    Enhanced TV show filename parser that handles:
    - "The Family Man (2019) S01 E02"
    - "The.Family.Man.S01E02"
    - "12345 The Family Man S01E02" (with ID)
    """
    # Try patterns with year first
    match = re.match(r"^(\d+)\s+(.+?)\s+\((\d{4})\)\s+[sS](\d+)\s*[eE](\d+)", filename)  # ID + "Title (Year) S01E01"
    if not match:
        match = re.match(r"^(.+?)\s+\((\d{4})\)\s+[sS](\d+)\s*[eE](\d+)", filename)  # "Title (Year) S01E01"
    if not match:
        match = re.match(r"^(\d+)\s+(.+?)\s+[sS](\d+)\s*[eE](\d+)", filename)  # ID + Title + S01E01
    if not match:
        match = re.match(r"^(.+?)[\s\.][sS](\d+)[\s\.]*[eE](\d+)", filename)  # Title.S01E01
    
    if match:
        groups = match.groups()
        if len(groups) == 5:  # ID + Title + Year + Season + Episode
            return groups[0], f"{groups[1]} ({groups[2]})", int(groups[3]), int(groups[4]), True
        elif len(groups) == 4:  # Title + Year + Season + Episode
            return None, f"{groups[0]} ({groups[1]})", int(groups[2]), int(groups[3]), False
        elif len(groups) == 3:  # Title + Season + Episode
            return None, groups[0], int(groups[1]), int(groups[2]), False
    
    return None, None, None, None, False

async def process_tv_file(filename: str) -> TMDbResult:
    """Robust TV show processor with complete error handling"""
    try:
        identifier, title, season, episode, is_id = parse_tv_filename(filename)
        
        if season is None or episode is None:
            return {
                "success": False,
                "data": None,
                "error": f"Could not parse season/episode from filename: {filename}"
            }
        
        # Try with the full title first (including year if present)
        result = await fetch_tv_tmdb_data(
            identifier=identifier,
            title=title,
            season=season,
            episode=episode
        )

        # If that fails, try removing the year
        if not result["success"] and "(" in title and ")" in title:
            simple_title = title.split("(")[0].strip()
            LOGGER.info(f"Retrying with simplified title: {simple_title}")
            result = await fetch_tv_tmdb_data(
                identifier=identifier,
                title=simple_title,
                season=season,
                episode=episode
            )

        if not result["success"]:
            return result

        tv_data = result["data"]
        
        # Ensure season data structure exists
        if not tv_data.get("season"):
            tv_data["season"] = [{
                "season_number": season,
                "episodes": []
            }]
        
        # Ensure we have our target season
        target_season = None
        for s in tv_data["season"]:
            if s.get("season_number") == season:
                target_season = s
                break
        
        if not target_season:
            target_season = {
                "season_number": season,
                "episodes": []
            }
            tv_data["season"].append(target_season)
        
        # Ensure episodes list exists
        if not target_season.get("episodes"):
            target_season["episodes"] = []
        
        # Find or create our episode
        target_episode = None
        for ep in target_season["episodes"]:
            if ep.get("episode_number") == episode:
                target_episode = ep
                break
        
        if not target_episode:
            target_episode = {
                "episode_number": episode,
                "name": "Unknown",
                "runtime": 0,
                "overview": "",
                "still_path": "",
                "air_date": None
            }
            target_season["episodes"].append(target_episode)
        
        # Ensure still_path is populated
        if not tv_data.get("still_path") and target_episode.get("still_path"):
            tv_data["still_path"] = target_episode["still_path"]
        
        return {"success": True, "data": tv_data, "error": None}

    except Exception as e:
        LOGGER.error(f"Failed to process TV file {filename}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "data": None,
            "error": f"Failed to process TV file: {str(e)}"
        }

async def fetch_tv_tmdb_data(
    identifier: Optional[str] = None,
    title: Optional[str] = None,
    season: Optional[int] = None,
    episode: Optional[int] = None
) -> TMDbResult:
    """Fetch TV show data using either ID or title"""
    try:
        # Try ID first if available
        if identifier:
            try:
                result = await fetch_tv_by_tmdb_id(int(identifier), season, episode)
                if result["success"]:
                    return result
                LOGGER.warning(f"ID {identifier} lookup failed, falling back to title search")
            except ValueError:
                pass  # Not a valid ID
        
        # Fall back to title search
        if title:
            tv_search = await tmdb.search().tv(query=title)
            
            if not tv_search or not hasattr(tv_search, "results") or len(tv_search.results) == 0:
                return {
                    "success": False,
                    "data": None,
                    "error": f"No TV show found for '{title}'",
                }

            tv_show_id = tv_search.results[0].id
            return await fetch_tv_by_tmdb_id(tv_show_id, season, episode)
        
        return {
            "success": False,
            "data": None,
            "error": "No valid identifier or title provided"
        }
    except Exception as e:
        LOGGER.error(f"Error fetching TV details: {str(e)}")
        return {"success": False, "data": None, "error": f"TMDb API error: {str(e)}"}

async def fetch_tv_by_tmdb_id(
    tv_id: int, 
    season: Optional[int] = None, 
    episode: Optional[int] = None
) -> TMDbResult:
    """Fetch TV show details by TMDB ID with robust episode handling"""
    try:
        tv_data = {
            "sid": tv_id,
            "title": "",
            "total_seasons": 0,
            "total_episodes": 0,
            "status": "",
            "trailer": "",
            "original_title": "",
            "release_date": None,
            "creators": [],
            "overview": "",
            "poster_path": "",
            "backdrop_path": "",
            "popularity": 0,
            "vote_average": 0,
            "vote_count": 0,
            "genres": [],
            "cast": [],
            "logo": "",
            "still_path": "",
            "studios": [],
            "links": [f"https://www.themoviedb.org/tv/{tv_id}"],
            "season": [],
        }

        # Fetch basic details with error handling
        try:
            details = await tmdb.tv(tv_id).details()
            if details:
                tv_data.update({
                    "title": getattr(details, "name", ""),
                    "total_seasons": len(getattr(details, "seasons", [])),
                    "total_episodes": getattr(details, "number_of_episodes", 0),
                    "status": getattr(details, "status", ""),
                    "original_title": getattr(details, "original_name", ""),
                    "creators": [
                        str(creator.name)
                        for creator in getattr(details, "created_by", [])
                        if hasattr(creator, "name")
                    ],
                    "release_date": str(details.first_air_date) if hasattr(details, "first_air_date") else None,
                    "overview": getattr(details, "overview", ""),
                    "poster_path": getattr(details, "poster_path", "") or "",
                    "backdrop_path": getattr(details, "backdrop_path", "") or "",
                    "popularity": float(getattr(details, "popularity", 0)),
                    "vote_average": float(getattr(details, "vote_average", 0)),
                    "vote_count": int(getattr(details, "vote_count", 0)),
                    "genres": [genre.name for genre in getattr(details, "genres", []) if hasattr(genre, "name")],
                    "studios": [
                        getattr(company, "name", "")
                        for company in getattr(details, "production_companies", [])
                        if hasattr(company, "name")
                    ],
                })
        except Exception as e:
            LOGGER.warning(f"Error fetching TV show details for ID {tv_id}: {str(e)}")

        # Enhanced season/episode handling
        if season is not None:
            # Initialize season data
            season_data = {
                "season_number": season,
                "episodes": []
            }
            
            if episode is not None:
                # Try to get episode details
                try:
                    episode_details = await tmdb.episode(tv_id, season, episode).details()
                    episode_data = {
                        "episode_number": episode,
                        "name": getattr(episode_details, "name", "Unknown"),
                        "runtime": int(getattr(episode_details, "runtime", 0)),
                        "overview": getattr(episode_details, "overview", ""),
                        "still_path": getattr(episode_details, "still_path", "") or "",
                        "air_date": str(getattr(episode_details, "air_date", "")) or None
                    }
                    tv_data["still_path"] = episode_data["still_path"]
                except Exception as e:
                    LOGGER.warning(f"Error fetching episode {episode} details: {str(e)}")
                    episode_data = {
                        "episode_number": episode,
                        "name": "Unknown",
                        "runtime": 0,
                        "overview": "",
                        "still_path": "",
                        "air_date": None
                    }
                
                season_data["episodes"].append(episode_data)
            
            tv_data["season"].append(season_data)

        # Fetch additional data
        try:
            tv_data["logo"] = await _fetch_logos("tv", tv_id)
            
            external_ids = await _fetch_external_ids("tv", tv_id)
            if external_ids.get("imdb_id"):
                tv_data["links"].append(f"https://www.imdb.com/title/{external_ids['imdb_id']}")

            casts = await tmdb.tv(tv_id).credits()
            if hasattr(casts, "cast"):
                tv_data["cast"] = [
                    {
                        "name": getattr(actor, "name", ""),
                        "imageUrl": getattr(actor, "profile_path", "") or "",
                        "character": getattr(actor, "character", "") or "",
                    }
                    for actor in casts.cast[:20]
                    if hasattr(actor, "name")
                ]

            await asyncio.sleep(1)
            
            videos = await tmdb.tv(tv_id).videos()
            tv_data["trailer"] = get_official_trailer_url(videos) or ""
        except Exception as e:
            LOGGER.warning(f"Error fetching additional data for TV ID {tv_id}: {str(e)}")

        return {"success": True, "data": tv_data, "error": None}
    except Exception as e:
        LOGGER.error(f"Error fetching TV details for ID {tv_id}: {str(e)}")
        return {"success": False, "data": None, "error": f"TMDb API error: {str(e)}"}
