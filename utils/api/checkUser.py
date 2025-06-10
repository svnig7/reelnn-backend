from utils.db_utils.user_db import UserDatabase
from typing import Dict, Any
from datetime import datetime


def check_user(user_id: int) -> Dict[str, Any]:
    """
    Check if a user exists in the database and return their details.

    Args:
        user_id: The user ID to check

    Returns:
        Dict containing user details or error message
    """
    try:
        user_db = UserDatabase()
        user = user_db.find_user_by_id(user_id)

        if user:

            if "registration_date" in user and isinstance(
                user["registration_date"], datetime
            ):
                user["registration_date"] = user["registration_date"].isoformat()

            return {"status": "success", "message": "User found", "user": user}
        else:
            return {
                "status": "not_found",
                "message": f"User {user_id} not found in database",
            }
    except Exception as e:
        return {"status": "error", "message": f"Error checking user: {str(e)}"}
