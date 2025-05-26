from typing import Dict, Any
from utils.db_utils.show_db import ShowDatabase

def get_show_details(sid: int) -> Dict[str, Any]:
    """
    Retrieve show details by show ID (sid).
    
    Args:
        sid: The show ID to look up
        
    Returns:
        Dictionary containing the requested show fields or an error message
    """
    try:
        
        db = ShowDatabase()
        
        
        show = db.find_show_by_id(sid)
        
        if not show:
            return {
                "status": "error",
                "message": f"Show with ID {sid} not found"
            }
        
        
        result = {
            field: show.get(field) for field in [
                "title", "original_title", "release_date", "overview", 
                "poster_path", "backdrop_path", "popularity", "vote_average", 
                "vote_count", "genres", "logo", "cast", "creators", "links", 
                "studios", "season", "total_episodes", "total_seasons", "status", "trailer"
            ] if field in show
        }
        result["id"] = sid
        
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }