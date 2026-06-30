from typing import List, Dict, Any
from models.domain import Message
from datetime import datetime
import collections
import emoji

def _compute_chunk_metrics(messages: List[Message], target_person: str) -> Dict[str, Any]:
    target_msgs = [m for m in messages if m.sender == target_person]
    if not target_msgs:
        return None
        
    total_words = sum(len(m.content.split()) for m in target_msgs)
    avg_words = total_words / len(target_msgs)
    
    emoji_msgs = sum(1 for m in target_msgs if any(c in emoji.EMOJI_DATA for c in m.content))
    emoji_rate = emoji_msgs / len(target_msgs) * 100
    
    question_msgs = sum(1 for m in target_msgs if '?' in m.content)
    question_rate = question_msgs / len(target_msgs) * 100
    
    return {
        "message_count": len(target_msgs),
        "avg_words": round(avg_words, 2),
        "emoji_rate_pct": round(emoji_rate, 1),
        "question_rate_pct": round(question_rate, 1)
    }

def generate_timeline(messages: List[Message], target_person: str, num_chunks: int = 10) -> List[Dict[str, Any]]:
    """
    Splits the conversation into chronological chunks and computes metrics to show drift over time.
    """
    if not messages:
        return []
        
    # Sort messages by timestamp just in case
    messages.sort(key=lambda m: m.timestamp)
    
    chunk_size = max(1, len(messages) // num_chunks)
    
    timeline = []
    
    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = start_idx + chunk_size if i < num_chunks - 1 else len(messages)
        
        chunk = messages[start_idx:end_idx]
        if not chunk:
            continue
            
        metrics = _compute_chunk_metrics(chunk, target_person)
        if metrics:
            timeline.append({
                "period": f"Period {i+1}",
                "start_date": chunk[0].timestamp.strftime("%Y-%m-%d"),
                "end_date": chunk[-1].timestamp.strftime("%Y-%m-%d"),
                "metrics": metrics
            })
            
    return timeline
