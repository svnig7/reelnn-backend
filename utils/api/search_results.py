from typing import Dict, List, Any
import asyncio
import functools
from utils.db_utils.movie_db import MovieDatabase
from utils.db_utils.show_db import ShowDatabase


def async_lru_cache(maxsize=100):
    """Async-compatible LRU cache decorator."""
    def decorator(fn):
        
        cache = {}
        cache_order = []  
        
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            
            key = str((args, frozenset(kwargs.items())))
            
            
            if key in cache:
                cache_order.remove(key)
                cache_order.append(key)
                return cache[key]
            
            
            result = await fn(*args, **kwargs)
            
            
            cache[key] = result
            cache_order.append(key)
            
            
            if len(cache) > maxsize:
                oldest_key = cache_order.pop(0)
                cache.pop(oldest_key)
                
            return result
        
        
        def cache_info():
            return {
                "maxsize": maxsize,
                "currsize": len(cache)
            }
        
        def cache_clear():
            cache.clear()
            cache_order.clear()
            
        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        
        return wrapper
    return decorator

@async_lru_cache(maxsize=100)
async def get_cached_search_results(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get cached search results for frequently searched terms.
    This is now a directly awaitable async function.
    """
    return await search_all_media(query, limit)
async def search_all_media(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Search for content across both movie and show databases concurrently using Atlas Search.
    
    Args:
        query: Search term
        limit: Maximum number of results to return per media type
        
    Returns:
        Combined and sorted list of search results
    """
    movie_task = asyncio.create_task(search_movies(query, limit))
    show_task = asyncio.create_task(search_shows(query, limit))
    
    movie_results, show_results = await asyncio.gather(movie_task, show_task)
    
    
    combined_results = movie_results + show_results
    combined_results.sort(key=lambda x: x.get('score', 0), reverse=True)
    print(f"Combined results: {combined_results}")
    
    return combined_results

async def search_movies(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Search movies using Atlas Search with fuzzy matching.
    """
    movie_db = MovieDatabase()
    try:
        
        search_pipeline = [
            {
                "$search": {
                    "index": "movie",  
                    "text": {
                        "query": query,
                        "path": "title",
                        "fuzzy": {
                            "maxEdits": 1,
                            "prefixLength": 1
                        }
                    },
                    "highlight": {
                        "path": "title"
                    }
                }
            },
            {
                "$project": {
                    "mid": 1,
                    "title": 1,
                    "poster_path": 1,
                    "release_date": 1,
                    "vote_average": 1,
                    "vote_count": 1,
                    "score": {"$meta": "searchScore"},
                    "highlights": {"$meta": "searchHighlights"}
                }
            },
            {"$limit": limit}
        ]
        
        results = list(movie_db.movies_collection.aggregate(search_pipeline))
        
        processed_results = []
        for item in results:
            
            year = None
            if "release_date" in item and item["release_date"]:
                try:
                    year = int(item["release_date"].split("-")[0])
                except (IndexError, ValueError, AttributeError):
                    pass
                    
            processed_results.append({
                "id": item.get("mid"),
                "title": item.get("title"),
                "year": year,
                "poster": item.get("poster_path"),
                "vote_average": item.get("vote_average", 0),
                "vote_count": item.get("vote_count", 0),
                "media_type": "movie",
                
            })
        
        return processed_results
    finally:
        pass

async def search_shows(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Search shows using Atlas Search with fuzzy matching.
    """
    show_db = ShowDatabase()
    try:
        
        search_pipeline = [
            {
                "$search": {
                    "index": "shows",  
                    "text": {
                        "query": query,
                        "path": "title",
                        "fuzzy": {
                            "maxEdits": 1,
                            "prefixLength": 1
                        }
                    },
                    "highlight": {
                        "path": "title"
                    }
                }
            },
            {
                "$project": {
                    "sid": 1,
                    "title": 1,
                    "poster_path": 1,
                    "release_date": 1,
                    "vote_average": 1,
                    "vote_count": 1,
                    "score": {"$meta": "searchScore"},
                    "highlights": {"$meta": "searchHighlights"}
                }
            },
            {"$limit": limit}
        ]
        
        results = list(show_db.shows_collection.aggregate(search_pipeline))
        
        processed_results = []
        for item in results:
            
            year = None
            if "release_date" in item and item["release_date"]:
                try:
                    year = int(item["release_date"].split("-")[0])
                except (IndexError, ValueError, AttributeError):
                    pass
                    
            processed_results.append({
                "id": item.get("sid"),
                "title": item.get("title"),
                "year": year,
                "poster": item.get("poster_path"),
                "vote_average": item.get("vote_average", 0),
                "vote_count": item.get("vote_count", 0),
                "media_type": "show",
                
            })
            
        return processed_results
    finally:
        pass
        
def calculate_relevance_score(item: Dict[str, Any], query: str) -> float:
    """
    Calculate a custom relevance score for search results.
    This can be used to further refine the ranking if needed.
    
    Args:
        item: The search result item
        query: The original search query
        
    Returns:
        A relevance score
    """
    
    score = item.get("score", 0)
    
    
    vote_count = item.get("vote_count", 0)
    if vote_count > 1000:
        score *= 1.2
    elif vote_count > 500:
        score *= 1.1
        
    
    if item.get("title", "").lower() == query.lower():
        score *= 2
        
    return score