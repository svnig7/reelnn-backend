from datetime import datetime
from typing import Dict, Any
from utils.db_utils.user_db import UserDatabase
from utils.models.user_model import UserSchema
from pyrogram.types import User


class UserRegistrationHandler:
    def __init__(self):
        self.user_db = UserDatabase()

    def register_user_from_telegram(self, telegram_user: User) -> Dict[str, Any]:
        """
        Register a user from Telegram user object.

        Args:
            telegram_user: Pyrogram User object

        Returns:
            Dict with registration result
        """
        try:

            user_data = {
                "user_id": telegram_user.id,
                "username": telegram_user.username,
                "first_name": telegram_user.first_name,
                "last_name": telegram_user.last_name,
                "registration_date": datetime.now(),
                "slimit": 30,
                "is_active": True,
            }

            user_schema = UserSchema(**user_data)

            result = self.user_db.register_user(user_schema.dict())

            return result

        except Exception as e:
            return {"status": "error", "message": f"Registration failed: {str(e)}"}

    def get_user_info(self, user_id: int) -> Dict[str, Any]:
        """Get user information by ID."""
        user = self.user_db.find_user_by_id(user_id)
        if user:
            return {"status": "found", "user": user}
        else:
            return {"status": "not_found", "message": "User not found"}

    def update_user_limit(self, user_id: int, new_limit: int) -> Dict[str, Any]:
        """Update user's streaming limit."""
        return self.user_db.update_user_slimit(user_id, new_limit)
