from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserSchema(BaseModel):
    """Schema for user data validation."""
    user_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(None, description="Telegram username")
    first_name: Optional[str] = Field(None, description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")
    registration_date: datetime = Field(default_factory=datetime.now, description="Registration date and time")
    slimit: int = Field(default=30, description="User's streaming limit")
    is_active: bool = Field(default=True, description="User account status")