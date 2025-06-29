import asyncio
import functools
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


async def fetch_movie_by_tmdb_id(movie_id: int) -> TMDbResult:
    """
    Fetch movie details from TMDb API using TMDB ID

    Args:
        movie_id: TMDB movie ID

    Returns:
        Dictionary with movie data or error information
    """
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
            movie_details = await tmdb.movie(movie_id).details()
            movie_data["title"] = getattr(movie_details, "title", "")
            movie_data["original_title"] = getattr(movie_details, "original_title", "")
            movie_data["release_date"] = (
                str(movie_details.release_date)
                if hasattr(movie_details, "release_date") and movie_details.release_date
                else None
            )
            movie_data["overview"] = getattr(movie_details, "overview", "")
            movie_data["poster_path"] = getattr(movie_details, "poster_path", "") or ""
            movie_data["backdrop_path"] = (
                getattr(movie_details, "backdrop_path", "") or ""
            )
            movie_data["runtime"] = getattr(movie_details, "runtime", 0) or 0
            movie_data["popularity"] = getattr(movie_details, "popularity", 0) or 0
            movie_data["vote_average"] = getattr(movie_details, "vote_average", 0) or 0
            movie_data["vote_count"] = getattr(movie_details, "vote_count", 0) or 0

            # Genres
            if hasattr(movie_details, "genres"):
                movie_data["genres"] = [
                    genre.name for genre in movie_details.genres if hasattr(genre, "name")
                ]

            # Production companies
            production_companies = getattr(movie_details, "production_companies", [])
            movie_data["studios"] = [
                getattr(company, "name", "")
                for company in production_companies
                if hasattr(company, "name")
            ]
        except Exception as e:
            LOGGER.warning(f"Error fetching movie details for ID {movie_id}: {str(e)}")

        # Fetch additional data (logos, external IDs, cast, videos)
        await _fetch_movie_additional_data(movie_id, movie_data)

        return {"success": True, "data": movie_data, "error": None}
    except Exception as e:
        LOGGER.error(f"Error fetching movie details for ID {movie_id}: {str(e)}")
        return {"success": False, "data": None, "error": f"TMDb API error: {str(e)}"}


async def fetch_tv_by_tmdb_id(tv_id: int, season: Optional[int] = None, episode: Optional[int] = None) -> TMDbResult:
    """
    Fetch TV show details from TMDb API using TMDB ID

    Args:
        tv_id: TMDB TV show ID
        season: Optional season number
        episode: Optional episode number

    Returns:
        Dictionary with TV show data or error information
    """
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

        # Fetch basic details
        try:
            tv_show_details = await tmdb.tv(tv_id).details()
            tv_data["title"] = getattr(tv_show_details, "name", "")
            tv_data["total_seasons"] = len(getattr(tv_show_details, "seasons", []))
            tv_data["total_episodes"] = getattr(
                tv_show_details, "number_of_episodes", 0
            )
            tv_data["status"] = getattr(tv_show_details, "status", "")
            tv_data["original_title"] = getattr(tv_show_details, "original_name", "")
            tv_data["creators"] = [
                str(creator.name)
                for creator in getattr(tv_show_details, "created_by", [])
                if hasattr(creator, "name")
            ]
            tv_data["release_date"] = (
                str(tv_show_details.first_air_date)
                if hasattr(tv_show_details, "first_air_date")
                and tv_show_details.first_air_date
                else None
            )
            tv_data["overview"] = getattr(tv_show_details, "overview", "")
            tv_data["poster_path"] = getattr(tv_show_details, "poster_path", "") or ""
            tv_data["backdrop_path"] = (
                getattr(tv_show_details, "backdrop_path", "") or ""
            )
            tv_data["popularity"] = getattr(tv_show_details, "popularity", 0)
            tv_data["vote_average"] = getattr(tv_show_details, "vote_average", 0)
            tv_data["vote_count"] = getattr(tv_show_details, "vote_count", 0)

            # Genres
            if hasattr(tv_show_details, "genres"):
                tv_data["genres"] = [
                    genre.name for genre in tv_show_details.genres if hasattr(genre, "name")
                ]

            # Production companies
            production_companies = getattr(tv_show_details, "production_companies", [])
            tv_data["studios"] = [
                getattr(company, "name", "")
                for company in production_companies
                if hasattr(company, "name")
            ]
        except Exception as e:
            LOGGER.warning(f"Error fetching TV show details for ID {tv_id}: {str(e)}")

        # Fetch season/episode data if specified
        if season is not None:
            season_data = {
                "season_number": int(season),
                "episodes": [],
            }
            
            if episode is not None:
                episode_data = {
                    "episode_number": int(episode),
                    "name": "",
                    "runtime": 0,
                    "overview": "",
                    "still_path": "",
                    "air_date": None,
                }
                
                try:
                    episode_details = await tmdb.episode(tv_id, season, episode).details()
                    episode_data["name"] = getattr(episode_details, "name", "")
                    episode_data["runtime"] = int(getattr(episode_details, "runtime", 0) or 0)
                    episode_data["overview"] = getattr(episode_details, "overview", "")
                    episode_data["still_path"] = (
                        getattr(episode_details, "still_path", "") or ""
                    )
                    episode_data["air_date"] = (
                        str(episode_details.air_date)
                        if hasattr(episode_details, "air_date") and episode_details.air_date
                        else None
                    )
                    tv_data["still_path"] = episode_data["still_path"]
                except Exception as e:
                    LOGGER.warning(
                        f"Error fetching episode details for ID {tv_id} S{season}E{episode}: {str(e)}"
                    )
                
                season_data["episodes"].append(episode_data)
            
            tv_data["season"].append(season_data)

        # Fetch additional data (logos, external IDs, cast, videos)
        await _fetch_tv_additional_data(tv_id, tv_data)

        return {"success": True, "data": tv_data, "error": None}
    except Exception as e:
        LOGGER.error(f"Error fetching TV details for ID {tv_id}: {str(e)}")
        return {"success": False, "data": None, "error": f"TMDb API error: {str(e)}"}


async def _fetch_movie_additional_data(movie_id: int, movie_data: Dict[str, Any]) -> None:
    """Helper function to fetch additional movie data"""
    try:
        # Fetch logos
        logos = await tmdb.movie(movie_id).images()
        logo_path = ""
        if hasattr(logos, "logos") and logos.logos:
            en_logos = [
                logo
                for logo in logos.logos
                if hasattr(logo, "iso_639_1") and logo.iso_639_1 == "en"
            ]
            in_logos = [
                logo
                for logo in logos.logos
                if hasattr(logo, "iso_639_1") and logo.iso_639_1 == "in"
            ]

            if en_logos:
                logo_path = en_logos[0].file_path
            elif in_logos:
                logo_path = in_logos[0].file_path

        movie_data["logo"] = logo_path or ""
    except Exception as e:
        LOGGER.warning(f"Error fetching logos for movie ID {movie_id}: {str(e)}")

    try:
        # Fetch external IDs
        movie_external_ids = await tmdb.movie(movie_id).external_ids()
        if hasattr(movie_external_ids, "imdb_id") and movie_external_ids.imdb_id:
            movie_data["links"].append(
                f"https://www.imdb.com/title/{movie_external_ids.imdb_id}"
            )
    except Exception as e:
        LOGGER.warning(f"Error fetching external IDs for movie ID {movie_id}: {str(e)}")

    try:
        # Fetch cast and crew
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

    await asyncio.sleep(2)

    try:
        # Fetch videos
        videos = await tmdb.movie(movie_id).videos()
        movie_data["trailer"] = get_official_trailer_url(videos) or ""
    except Exception as e:
        LOGGER.warning(f"Error fetching videos for movie ID {movie_id}: {str(e)}")


async def _fetch_tv_additional_data(tv_id: int, tv_data: Dict[str, Any]) -> None:
    """Helper function to fetch additional TV show data"""
    try:
        # Fetch logos
        logos = await tmdb.tv(tv_id).images()
        logo_path = ""
        if hasattr(logos, "logos") and logos.logos:
            en_logos = [
                logo
                for logo in logos.logos
                if hasattr(logo, "iso_639_1") and logo.iso_639_1 == "en"
            ]
            in_logos = [
                logo
                for logo in logos.logos
                if hasattr(logo, "iso_639_1") and logo.iso_639_1 == "in"
            ]

            if en_logos:
                logo_path = en_logos[0].file_path
            elif in_logos:
                logo_path = in_logos[0].file_path

        tv_data["logo"] = logo_path or ""
    except Exception as e:
        LOGGER.warning(f"Error fetching logos for TV ID {tv_id}: {str(e)}")

    try:
        # Fetch external IDs
        tv_external_ids = await tmdb.tv(tv_id).external_ids()
        if hasattr(tv_external_ids, "imdb_id") and tv_external_ids.imdb_id:
            tv_data["links"].append(
                f"https://www.imdb.com/title/{tv_external_ids.imdb_id}"
            )
    except Exception as e:
        LOGGER.warning(f"Error fetching external IDs for TV ID {tv_id}: {str(e)}")

    try:
        # Fetch cast
        casts = await tmdb.tv(tv_id).credits()
        if hasattr(casts, "cast"):
            tv_data["cast"] = [
                {
                    "name": getattr(actor, "name", ""),
                    "imageUrl": getattr(actor, "profile_path", ""),
                    "character": getattr(actor, "character", ""),
                }
                for actor in casts.cast[:20]
                if hasattr(actor, "name")
            ]
    except Exception as e:
        LOGGER.warning(f"Error fetching cast/crew for TV ID {tv_id}: {str(e)}")

    await asyncio.sleep(1)

    try:
        # Fetch videos
        videos = await tmdb.tv(tv_id).videos()
        tv_data["trailer"] = get_official_trailer_url(videos)
    except Exception as e:
        LOGGER.warning(f"Error fetching videos for TV ID {tv_id}: {str(e)}")


# Update the original functions to use the new helper functions
@async_lru_cache(maxsize=100)
async def fetch_movie_tmdb_data(title: str, year: Optional[int] = None) -> TMDbResult:
    """
    Fetch movie details from TMDb API

    Args:
        title: Movie title to search for
        year: Optional release year for more accurate search

    Returns:
        Dictionary with movie data or error information
    """
    try:
        search = await tmdb.search().movies(query=title, year=year)

        if not search or not hasattr(search, "results") or len(search.results) == 0:
            return {
                "success": False,
                "data": None,
                "error": f"No movie found for '{title}'",
            }

        movie_id = search.results[0].id
        return await fetch_movie_by_tmdb_id(movie_id)
    except Exception as e:
        LOGGER.error(f"Error searching for movie '{title}': {str(e)}")
        return {"success": False, "data": None, "error": f"Search error: {str(e)}"}


async def fetch_tv_tmdb_data(
    identifier: str, 
    season: int, 
    episode: int,
    is_id: bool = False
) -> TMDbResult:
    """
    Fetch TV show details from TMDb API

    Args:
        identifier: Either TV show title or TMDB ID
        season: Season number
        episode: Episode number
        is_id: Whether the identifier is a TMDB ID

    Returns:
        Dictionary with TV show data or error information
    """
    try:
        if is_id:
            # Directly fetch by ID if we know it's an ID
            return await fetch_tv_by_tmdb_id(int(identifier), season, episode)
        else:
            # Try to parse ID from filename if it starts with numbers
            if identifier[:1].isdigit():
                try:
                    # Try fetching as ID first
                    result = await fetch_tv_by_tmdb_id(int(identifier), season, episode)
                    if result["success"]:
                        return result
                except ValueError:
                    pass  # Not a valid ID, fall through to title search
            
            # Fall back to title search
            tv_search = await tmdb.search().tv(query=identifier)

            if (
                not tv_search
                or not hasattr(tv_search, "results")
                or len(tv_search.results) == 0
            ):
                return {
                    "success": False,
                    "data": None,
                    "error": f"No TV show found for '{identifier}'",
                }

            tv_show_id = tv_search.results[0].id
            return await fetch_tv_by_tmdb_id(tv_show_id, season, episode)
    except Exception as e:
        LOGGER.error(
            f"Error fetching TV details for '{identifier}' S{season}E{episode}: {str(e)}"
        )
        return {"success": False, "data": None, "error": f"TMDb API error: {str(e)}"}
