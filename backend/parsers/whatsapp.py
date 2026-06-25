import re
from typing import BinaryIO
from datetime import datetime
from parsers.base import BaseParser
from models.domain import Conversation, Message

class WhatsAppParser(BaseParser):
    def __init__(self):
        # Matches patterns like: [24/06/2026, 12:30:45] Sender: Message
        # Or: 24/06/2026, 12:30 - Sender: Message
        self.pattern = re.compile(
            r'\[?(?P<date>\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}),?\s+(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\s?[aApP][mM])?)\]?\s+[-]?\s*(?P<sender>[^:]+):\s+(?P<content>.*)'
        )
        self.media_pattern = re.compile(r'<Media omitted>|\(file attached\)|video omitted|image omitted', re.IGNORECASE)
    
    def parse(self, file: BinaryIO) -> Conversation:
        content = file.read().decode('utf-8')
        lines = content.splitlines()
        
        messages = []
        participants = set()
        
        current_message = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            match = self.pattern.match(line)
            if match:
                if current_message:
                    messages.append(current_message)
                    
                date_str = match.group('date')
                time_str = match.group('time')
                sender = match.group('sender').strip()
                # Strip invisible bidirectional unicode characters (LTR/RTL marks)
                sender = sender.replace('\u200e', '').replace('\u200f', '')
                text = match.group('content').strip()
                
                participants.add(sender)
                
                # Parse datetime. A bit tricky since format varies by region.
                # Assuming DD/MM/YYYY or MM/DD/YYYY. We'll use a generic parsing for now.
                try:
                    # Naive attempt, can be improved with dateutil
                    dt_str = f"{date_str} {time_str}"
                    # Just an example format, real parsing requires dateutil or robust format checking
                    # We will store it as a string parsed roughly, or use dateutil in production
                    from dateutil.parser import parse as date_parse
                    timestamp = date_parse(dt_str, fuzzy=True)
                except Exception:
                    timestamp = datetime.now() # Fallback
                
                is_media = bool(self.media_pattern.search(text))
                
                current_message = Message(
                    timestamp=timestamp,
                    sender=sender,
                    content=text,
                    is_media=is_media
                )
            else:
                # Multiline message continuation
                if current_message:
                    current_message.content += f"\n{line}"
                    if self.media_pattern.search(line):
                        current_message.is_media = True
        
        if current_message:
            messages.append(current_message)
            
        if not messages:
            raise ValueError("No valid messages found in the file")
            
        start_date = messages[0].timestamp
        end_date = messages[-1].timestamp
        
        return Conversation(
            participants=list(participants),
            messages=messages,
            start_date=start_date,
            end_date=end_date,
            total_messages=len(messages)
        )
