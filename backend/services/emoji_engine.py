"""
Emoji Engine — 100% deterministic. No LLM.
Computes emoji frequency, emoji rate, and top emojis for a target person.
"""
from collections import Counter
from typing import List
import emoji
from models.domain import Message


def extract_emojis(messages: List[Message], target_person: str) -> dict:
    """
    Finds all emojis used by target_person, counts frequency, and computes rate.
    Returns zero-hallucination facts only.
    """
    target_msgs = [m for m in messages
                   if m.sender == target_person and m.content != "<Media omitted>"]

    total_messages = len(target_msgs)
    if total_messages == 0:
        return {"top_emojis": [], "emoji_rate": 0, "emoji_count": 0}

    all_emojis: list = []
    messages_with_emoji = 0

    for msg in target_msgs:
        emojis_in_msg = [c for c in msg.content if c in emoji.EMOJI_DATA]
        if emojis_in_msg:
            messages_with_emoji += 1
            all_emojis.extend(emojis_in_msg)

    emoji_counts = Counter(all_emojis)
    top_emojis = [{"emoji": e, "count": c, "frequency_pct": round(c / total_messages * 100, 1)}
                  for e, c in emoji_counts.most_common(10)]

    return {
        "top_emojis": top_emojis,
        "emoji_rate": round(messages_with_emoji / total_messages, 3),
        "emoji_rate_pct": round(messages_with_emoji / total_messages * 100, 1),
        "total_emojis_sent": len(all_emojis),
        "unique_emojis": len(emoji_counts),
    }
