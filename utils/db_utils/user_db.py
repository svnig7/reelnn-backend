from typing import Dict, List, Any, Optional
from datetime import datetime
from utils.db_utils.mongo_client import get_database


class UserDatabase:
    def __init__(self):
        """Initialize MongoDB connection."""
        db = get_database("users_db")
        self.users_collection = db["users"]

        self.users_collection.create_index("user_id", unique=True)

    def register_user(self, user_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new user in the database.

        Args:
            user_dict: Dictionary containing user data

        Returns:
            Dict with operation status and user info
        """
        user_id = user_dict.get("user_id")

        if not user_id:
            return {"status": "error", "message": "User ID is required"}

        try:

            existing_user = self.users_collection.find_one({"user_id": user_id})

            if existing_user:
                return {
                    "status": "already_exists",
                    "message": f"User {user_id} is already registered",
                    "user_id": user_id,
                    "registration_date": existing_user.get("registration_date"),
                }

            user_dict.setdefault("registration_date", datetime.now())
            user_dict.setdefault("slimit", 30)
            user_dict.setdefault("is_active", True)

            result = self.users_collection.insert_one(user_dict)

            return {
                "status": "success",
                "message": f"User {user_id} registered successfully",
                "user_id": user_id,
                "registration_date": user_dict["registration_date"],
                "slimit": user_dict["slimit"],
                "inserted_id": str(result.inserted_id),
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def find_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Find a user by their ID."""
        try:
            user_id = int(user_id)
            user = self.users_collection.find_one({"user_id": user_id}, {"_id": 0})

            if user and "_id" in user:
                user["_id"] = str(user["_id"])

            return user
        except Exception as e:
            print(f"Error finding user: {str(e)}")
            return None

    def update_user_slimit(self, user_id: int, new_slimit: int) -> Dict[str, Any]:
        """Update a user's streaming limit."""
        try:
            result = self.users_collection.update_one(
                {"user_id": user_id}, {"$set": {"slimit": new_slimit}}
            )

            if result.modified_count > 0:
                return {
                    "status": "success",
                    "message": f"User {user_id} slimit updated to {new_slimit}",
                    "modified_count": result.modified_count,
                }
            else:
                return {"status": "not_found", "message": f"User {user_id} not found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def deactivate_user(self, user_id: int) -> Dict[str, Any]:
        """Deactivate a user account."""
        try:
            result = self.users_collection.update_one(
                {"user_id": user_id}, {"$set": {"is_active": False}}
            )

            if result.modified_count > 0:
                return {
                    "status": "success",
                    "message": f"User {user_id} deactivated",
                    "modified_count": result.modified_count,
                }
            else:
                return {"status": "not_found", "message": f"User {user_id} not found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_all_users(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all users with pagination."""
        try:
            cursor = self.users_collection.find({}).skip(skip).limit(limit)
            users = list(cursor)
            return users if users else []
        except Exception as e:
            print(f"Error getting users: {str(e)}")
            return []

    def search_users(self, query: str) -> List[Dict[str, Any]]:
        """Search users by username, first name, or user ID."""
        try:

            search_filters = []

            if query.strip():
                search_filters.append({"username": {"$regex": query, "$options": "i"}})
                search_filters.append(
                    {"first_name": {"$regex": query, "$options": "i"}}
                )
                search_filters.append({"last_name": {"$regex": query, "$options": "i"}})

                if query.isdigit():
                    search_filters.append({"user_id": int(query)})

            if not search_filters:
                return []

            cursor = self.users_collection.find({"$or": search_filters})
            users = list(cursor)
            return users if users else []
        except Exception as e:
            print(f"Error searching users: {str(e)}")
            return []

    def update_user(self, user_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user information (excluding user_id)."""
        try:

            if "user_id" in update_data:
                del update_data["user_id"]

            update_data = {
                k: v for k, v in update_data.items() if v is not None and v != ""
            }

            if not update_data:
                return {"status": "error", "message": "No valid fields to update"}

            result = self.users_collection.update_one(
                {"user_id": user_id}, {"$set": update_data}
            )

            if result.modified_count > 0:
                updated_user = self.find_user_by_id(user_id)

                if updated_user and "_id" in updated_user:
                    updated_user["_id"] = str(updated_user["_id"])

                return {
                    "status": "success",
                    "message": f"User {user_id} updated successfully",
                    "user": updated_user,
                }
            else:
                return {"status": "not_found", "message": f"User {user_id} not found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_user(self, user_id: int) -> Dict[str, Any]:
        """Delete a user from the database."""
        try:
            result = self.users_collection.delete_one({"user_id": user_id})

            if result.deleted_count > 0:
                return {
                    "status": "success",
                    "message": f"User {user_id} deleted successfully",
                }
            else:
                return {"status": "not_found", "message": f"User {user_id} not found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
