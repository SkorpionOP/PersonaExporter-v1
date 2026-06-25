from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Message(BaseModel):
    timestamp: datetime
    sender: str
    content: str
    is_media: bool = False
    media_type: Optional[str] = None

class Conversation(BaseModel):
    participants: List[str]
    messages: List[Message]
    start_date: datetime
    end_date: datetime
    total_messages: int
