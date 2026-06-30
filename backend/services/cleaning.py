"""
Cleaning Engine
Normalizes chat data to improve downstream engine processing.
"""
from typing import List
from models.domain import Message

def clean_messages(messages: List[Message]) -> List[Message]:
    """
    Normalizes whitespace and standardizes basic text artifacts before processing.
    """
    cleaned = []
    for msg in messages:
        if msg.content != "<Media omitted>":
            # Normalize whitespace
            content = " ".join(msg.content.split())
            cleaned.append(Message(
                timestamp=msg.timestamp,
                sender=msg.sender,
                content=content,
                is_media=msg.is_media,
                media_type=msg.media_type
            ))
        else:
            cleaned.append(msg)
    return cleaned
