import json
from typing import BinaryIO
from datetime import datetime
from parsers.base import BaseParser
from models.domain import Conversation, Message
from dateutil.parser import parse as date_parse

class TelegramParser(BaseParser):
    def parse(self, file: BinaryIO) -> Conversation:
        try:
            content = file.read().decode('utf-8')
            data = json.loads(content)
        except Exception as e:
            raise ValueError(f"Invalid JSON format for Telegram export: {str(e)}")
            
        # The Telegram export structure is typically:
        # {
        #   "name": "Chat Name",
        #   "type": "personal_chat",
        #   "id": 123456,
        #   "messages": [ ... ]
        # }
        # Let's also support a list of messages directly to be extra robust.
        if isinstance(data, dict):
            raw_messages = data.get("messages", [])
        elif isinstance(data, list):
            raw_messages = data
        else:
            raise ValueError("Telegram export must be a JSON object containing messages or a list of messages")
            
        messages = []
        participants = set()
        
        for msg in raw_messages:
            if not isinstance(msg, dict):
                continue
            
            # We only care about chat messages, not service/event notifications
            if msg.get("type") != "message":
                continue
                
            sender = msg.get("from")
            if not sender:
                # Fallback to actor if from is not present (for some automated/service style messages or channels)
                sender = msg.get("actor")
                
            if not sender:
                continue
                
            # Clean up the sender's name from bidirectional markers (like \u200e and \u200f)
            sender = sender.replace('\u200e', '').replace('\u200f', '').strip()
            if not sender:
                continue
                
            participants.add(sender)
            
            # Reconstruct content from Telegram's 'text' representation
            # Text can be a plain string, or a list of mixed strings and formatting dicts:
            # e.g., ["Hello ", {"type": "bold", "text": "world"}, "!"]
            text_field = msg.get("text", "")
            content_text = ""
            if isinstance(text_field, str):
                content_text = text_field
            elif isinstance(text_field, list):
                parts = []
                for part in text_field:
                    if isinstance(part, str):
                        parts.append(part)
                    elif isinstance(part, dict):
                        parts.append(part.get("text", ""))
                content_text = "".join(parts)
            
            # Parse timestamp
            date_str = msg.get("date")
            try:
                timestamp = date_parse(date_str) if date_str else datetime.now()
            except Exception:
                timestamp = datetime.now()
                
            # Detect if message represents media
            media_type = msg.get("media_type")
            is_media = False
            # Check for sticker, photo, video, document, or files
            if media_type or "photo" in msg or "file" in msg or msg.get("media_type") is not None:
                is_media = True
                
            messages.append(Message(
                timestamp=timestamp,
                sender=sender,
                content=content_text,
                is_media=is_media,
                media_type=media_type
            ))
            
        if not messages:
            raise ValueError("No valid messages found in the Telegram export")
            
        # Ensure chronological order
        messages.sort(key=lambda m: m.timestamp)
        
        start_date = messages[0].timestamp
        end_date = messages[-1].timestamp
        
        return Conversation(
            participants=list(participants),
            messages=messages,
            start_date=start_date,
            end_date=end_date,
            total_messages=len(messages)
        )
