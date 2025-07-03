import asyncio
import functools
from typing import Dict, Any, Optional, TypedDict
from themoviedb import aioTMDb
from app import LOGGER
from utils.utils import get_official_trailer_url
from config import TMDB_API_KEY
from guessit import guessit

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

def parse_tmdb_input(
    input_text: str,
    is_tv: bool = False,
    default_season: int = 1,
    default_episode: int = 1
) -> Dict[str, Any]:
    """
    Parses a text input to extract either a TMDb ID or a title.
    Supports inputs like:
    - '1121330\n8 A.M. Metro ...'
    - '8 A.M. Metro ...'

    Args:
        input_text (str): Raw caption or filename input
        is_tv (bool): Whether it's a TV show
        default_season (int): Default season for TV
        default_episode (int): Default episode for TV

    Returns:
        dict: Parsed data with tmdb_id or title, and optional season/episode
    """

    # Normalize literal "\\n" to real newlines
    cleaned = input_text.replace("\\n", "\n").strip()
    lines = cleaned.splitlines()

    result: Dict[str, Any] = {}

    # First line is a TMDb ID (e.g. 1121330)
    if lines and lines[0].strip().isdigit():
        result["tmdb_id"] = int(lines[0].strip())
    else:
        result["title"] = cleaned  # fallback to full cleaned input

    # If TV, add season and episode info
    if is_tv:
        result["season"] = default_season
        result["episode"] = default_episode

    return result
    
@async_lru_cache(maxsize=100)
async def fetch_movie_tmdb_data(
    title: Optional[str] = None,
    year: Optional[int] = None,
    tmdb_id: Optional[int] = None
) -> TMDbResult:
    """
    Fetch movie details from TMDb API using TMDb ID first, then title search
    """
    try:
        movie_id = None

        if tmdb_id:
            try:
                await tmdb.movie(tmdb_id).details()
                movie_id = tmdb_id
            except Exception as e:
                LOGGER.warning(f"TMDb ID {tmdb_id} not found, fallback to title search: {e}")

        if not movie_id:
            if not title:
                return {"success": False, "data": None, "error": "No title or valid TMDb ID provided"}
            search = await tmdb.search().movies(query=title, year=year)
            if not search or not hasattr(search, "results") or len(search.results) == 0:
                return {"success": False, "data": None, "error": f"No movie found for '{title}'"}
            movie_id = search.results[0].id

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

        try:
            movie_details = await tmdb.movie(movie_id).details()
            movie_data["title"] = getattr(movie_details, "title", "")
            movie_data["original_title"] = getattr(movie_details, "original_title", "")
            movie_data["release_date"] = str(getattr(movie_details, "release_date", "")) or None
            movie_data["overview"] = getattr(movie_details, "overview", "")
            movie_data["poster_path"] = getattr(movie_details, "poster_path", "") or ""
            movie_data["backdrop_path"] = getattr(movie_details, "backdrop_path", "") or ""
            movie_data["runtime"] = getattr(movie_details, "runtime", 0) or 0
            movie_data["popularity"] = getattr(movie_details, "popularity", 0) or 0
            movie_data["vote_average"] = getattr(movie_details, "vote_average", 0) or 0
            movie_data["vote_count"] = getattr(movie_details, "vote_count", 0) or 0

            production_companies = getattr(movie_details, "production_companies", [])
            movie_data["studios"] = [company.name for company in production_companies if hasattr(company, "name")]
        except Exception as e:
            LOGGER.warning(f"Error fetching movie details for '{title}': {str(e)}")

        try:
            logos = await tmdb.movie(movie_id).images()
            logo_path = ""
            if hasattr(logos, "logos") and logos.logos:
                en_logos = [logo for logo in logos.logos if getattr(logo, "iso_639_1", "") == "en"]
                in_logos = [logo for logo in logos.logos if getattr(logo, "iso_639_1", "") == "in"]
                if en_logos:
                    logo_path = en_logos[0].file_path
                elif in_logos:
                    logo_path = in_logos[0].file_path
            movie_data["logo"] = logo_path or ""
        except Exception as e:
            LOGGER.warning(f"Error fetching logos for '{title}': {str(e)}")

        try:
            movie_external_ids = await tmdb.movie(movie_id).external_ids()
            if getattr(movie_external_ids, "imdb_id", None):
                movie_data["links"].append(f"https://www.imdb.com/title/{movie_external_ids.imdb_id}")
        except Exception as e:
            LOGGER.warning(f"Error fetching external IDs for '{title}': {str(e)}")

        try:
            genre_data = await tmdb.genres().movie()
            genre_map = {genre.id: genre.name for genre in genre_data.genres}
            genre_ids = getattr(search.results[0], "genre_ids", []) if not tmdb_id else getattr(movie_details, "genres", [])
            movie_data["genres"] = [genre.name for genre in genre_ids] if tmdb_id else [genre_map.get(i) for i in genre_ids]
        except Exception as e:
            LOGGER.warning(f"Error fetching genres for '{title}': {str(e)}")

        try:
            casts = await tmdb.movie(movie_id).credits()
            if hasattr(casts, "cast"):
                movie_data["cast"] = [
                    {
                        "name": getattr(actor, "name", ""),
                        "imageUrl": getattr(actor, "profile_path", "") or "",
                        "character": getattr(actor, "character", "") or "",
                    }
                    for actor in casts.cast[:20] if hasattr(actor, "name")
                ]
            if hasattr(casts, "crew"):
                movie_data["directors"] = [
                    member.name for member in casts.crew if getattr(member, "job", "") == "Director"
                ]
        except Exception as e:
            LOGGER.warning(f"Error fetching cast/crew for '{title}': {str(e)}")

        await asyncio.sleep(2)
        try:
            videos = await tmdb.movie(movie_id).videos()
            movie_data["trailer"] = get_official_trailer_url(videos) or ""
        except Exception as e:
            LOGGER.warning(f"Error fetching videos for '{title}': {str(e)}")

        return {"success": True, "data": movie_data, "error": None}

    except Exception as e:
        LOGGER.error(f"Error fetching movie details (TMDb ID: {tmdb_id}, title: {title}): {str(e)}")
        return {"success": False, "data": None, "error": f"TMDb API error: {str(e)}"}

async def fetch_tv_tmdb_data(
    title: Optional[str] = None,
    season: int = 1,
    episode: int = 1,
    tmdb_id: Optional[int] = None
) -> TMDbResult:
    """
    Fetch TV show details from TMDb API using TMDb ID first, then title search
    """
    try:
        tv_show_id = None

        if tmdb_id:
            try:
                await tmdb.tv(tmdb_id).details()
                tv_show_id = tmdb_id
            except Exception as e:
                LOGGER.warning(f"TMDb ID {tmdb_id} not found, fallback to title search: {e}")

        if not tv_show_id:
            if not title:
                return {"success": False, "data": None, "error": "No title or valid TMDb ID provided"}
            tv_search = await tmdb.search().tv(query=title)
            if not tv_search or not hasattr(tv_search, "results") or len(tv_search.results) == 0:
                return {"success": False, "data": None, "error": f"No TV show found for '{title}'"}
            tv_show_id = tv_search.results[0].id

        tv_data = {
            "sid": tv_show_id,
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
            "links": [f"https://www.themoviedb.org/tv/{tv_show_id}"],
            "season": [
                {
                    "season_number": int(season),
                    "episodes": [
                        {
                            "episode_number": int(episode),
                            "name": "",
                            "runtime": 0,
                            "overview": "",
                            "still_path": "",
                            "air_date": None,
                        }
                    ],
                }
            ],
        }

        try:
            tv_show_details = await tmdb.tv(tv_show_id).details()
            tv_data["title"] = getattr(tv_show_details, "name", "")
            tv_data["total_seasons"] = len(getattr(tv_show_details, "seasons", []))
            tv_data["total_episodes"] = getattr(tv_show_details, "number_of_episodes", 0)
            tv_data["status"] = getattr(tv_show_details, "status", "")
            tv_data["original_title"] = getattr(tv_show_details, "original_name", "")
            tv_data["creators"] = [
                str(creator.name)
                for creator in getattr(tv_show_details, "created_by", [])
                if hasattr(creator, "name")
            ]
            tv_data["release_date"] = str(getattr(tv_show_details, "first_air_date", "")) or None
            tv_data["overview"] = getattr(tv_show_details, "overview", "")
            tv_data["poster_path"] = getattr(tv_show_details, "poster_path", "") or ""
            tv_data["backdrop_path"] = getattr(tv_show_details, "backdrop_path", "") or ""
            tv_data["popularity"] = getattr(tv_show_details, "popularity", 0)
            tv_data["vote_average"] = getattr(tv_show_details, "vote_average", 0)
            tv_data["vote_count"] = getattr(tv_show_details, "vote_count", 0)
            production_companies = getattr(tv_show_details, "production_companies", [])
            tv_data["studios"] = [
                company.name for company in production_companies if hasattr(company, "name")
            ]
        except Exception as e:
            LOGGER.warning(f"Error fetching TV show details for '{title}': {str(e)}")

        await asyncio.sleep(2)
        try:
            episode_details = await tmdb.episode(tv_show_id, season, episode).details()
            episode_data = tv_data["season"][0]["episodes"][0]
            episode_data["name"] = getattr(episode_details, "name", "")
            episode_data["runtime"] = int(getattr(episode_details, "runtime", 0) or 0)
            episode_data["overview"] = getattr(episode_details, "overview", "")
            episode_data["still_path"] = getattr(episode_details, "still_path", "") or ""
            episode_data["air_date"] = str(getattr(episode_details, "air_date", "")) or None
            tv_data["still_path"] = episode_data["still_path"]
        except Exception as e:
            LOGGER.warning(
                f"Error fetching episode details for '{title}' S{season}E{episode}: {str(e)}"
            )

        try:
            logos = await tmdb.tv(tv_show_id).images()
            logo_path = ""
            if hasattr(logos, "logos") and logos.logos:
                en_logos = [logo for logo in logos.logos if getattr(logo, "iso_639_1", "") == "en"]
                in_logos = [logo for logo in logos.logos if getattr(logo, "iso_639_1", "") == "in"]
                if en_logos:
                    logo_path = en_logos[0].file_path
                elif in_logos:
                    logo_path = in_logos[0].file_path
            tv_data["logo"] = logo_path or ""
        except Exception as e:
            LOGGER.warning(f"Error fetching logos for '{title}': {str(e)}")

        await asyncio.sleep(2)
        try:
            tv_external_ids = await tmdb.tv(tv_show_id).external_ids()
            if getattr(tv_external_ids, "imdb_id", None):
                tv_data["links"].append(f"https://www.imdb.com/title/{tv_external_ids.imdb_id}")
        except Exception as e:
            LOGGER.warning(f"Error fetching external IDs for '{title}': {str(e)}")

        try:
            genre_data = await tmdb.genres().tv()
            genre_map = {genre.id: genre.name for genre in genre_data.genres}
            if not tmdb_id:
                tv_search = await tmdb.search().tv(query=title)
                genre_ids = getattr(tv_search.results[0], "genre_ids", []) if tv_search.results else []
                tv_data["genres"] = [genre_map.get(gid) for gid in genre_ids if gid in genre_map]
            else:
                tv_data["genres"] = [genre.name for genre in getattr(tv_show_details, "genres", [])]
        except Exception as e:
            LOGGER.warning(f"Error fetching genres for '{title}': {str(e)}")

        try:
            casts = await tmdb.tv(tv_show_id).credits()
            if hasattr(casts, "cast"):
                tv_data["cast"] = [
                    {
                        "name": getattr(actor, "name", ""),
                        "imageUrl": getattr(actor, "profile_path", ""),
                        "character": getattr(actor, "character", ""),
                    }
                    for actor in casts.cast[:20] if hasattr(actor, "name")
                ]
        except Exception as e:
            LOGGER.warning(f"Error fetching cast/crew for '{title}': {str(e)}")

        await asyncio.sleep(1)
        try:
            videos = await tmdb.tv(tv_show_id).videos()
            tv_data["trailer"] = get_official_trailer_url(videos)
        except Exception as e:
            LOGGER.warning(f"Error fetching videos for '{title}': {str(e)}")

        return {"success": True, "data": tv_data, "error": None}

    except Exception as e:
        LOGGER.error(f"Error fetching TV details (TMDb ID: {tmdb_id}, title: {title}) S{season}E{episode}: {str(e)}")
        return {"success": False, "data": None, "error": f"TMDb API error: {str(e)}"}
