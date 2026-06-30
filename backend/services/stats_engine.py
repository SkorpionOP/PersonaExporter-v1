"""
Stats Engine
Computes comprehensive deterministic metrics including distributions, variance, and timing.
"""
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import List
import statistics
from models.domain import Message



PUNCT_CLUSTERS = [r'\?{2,}', r'!{2,}', r'\.{2,}', r'-{2,}']
REPEATED_CHAR_PATTERN = re.compile(r'([a-zA-Z])\1{2,}')

def generate_statistics(conversation) -> dict:
    """Returns a high-level summary across all participants."""
    messages = conversation.messages
    total_messages = len(messages)
    all_text = " ".join(m.content for m in messages if m.content != "<Media omitted>")
    total_words = len(all_text.split())
    avg_length = round(total_words / max(total_messages, 1), 2)
    sender_counts = Counter(m.sender for m in messages)

    return {
        "total_messages": total_messages,
        "total_words": total_words,
        "average_message_length": avg_length,
        "messages_per_sender": dict(sender_counts),
    }

def compute_target_stats(messages: List[Message], target_person: str) -> dict:
    target_msgs = [m for m in messages if m.sender == target_person and m.content != "<Media omitted>"]
    if not target_msgs:
        return {"error": f"No messages found for {target_person}"}

    # Word counts
    msg_word_counts = [len(m.content.split()) for m in target_msgs]
    total = len(target_msgs)
    
    avg_words = round(statistics.mean(msg_word_counts), 1)
    median_words = round(statistics.median(msg_word_counts), 1)
    p90_words = round(statistics.quantiles(msg_word_counts, n=10)[8], 1) if total >= 10 else max(msg_word_counts)
    longest_words = max(msg_word_counts)
    shortest_words = min(msg_word_counts)
    variance_words = round(statistics.variance(msg_word_counts), 2) if total > 1 else 0
    stddev_words = round(statistics.stdev(msg_word_counts), 2) if total > 1 else 0

    # Timing
    timing = {"morning": 0, "afternoon": 0, "evening": 0, "night": 0, "weekend": 0, "weekday": 0}
    for m in target_msgs:
        hour = m.timestamp.hour
        if 6 <= hour < 12: timing["morning"] += 1
        elif 12 <= hour < 17: timing["afternoon"] += 1
        elif 17 <= hour < 21: timing["evening"] += 1
        else: timing["night"] += 1
        
        if m.timestamp.weekday() >= 5: timing["weekend"] += 1
        else: timing["weekday"] += 1

    # Delays (Reply to other person)
    delays = []
    for i in range(1, len(messages)):
        if messages[i].sender == target_person and messages[i-1].sender != target_person:
            delay = (messages[i].timestamp - messages[i-1].timestamp).total_seconds()
            if delay > 0 and delay < 86400: # Ignore replies after 24h as they might be new conversations
                delays.append(delay)
                
    avg_delay = round(statistics.mean(delays), 1) if delays else 0
    fastest_delay = round(min(delays), 1) if delays else 0
    slowest_delay = round(max(delays), 1) if delays else 0

    # Punctuation & Repeated chars
    punct_counts = Counter()
    repeated_chars = Counter()
    for m in target_msgs:
        for p in PUNCT_CLUSTERS:
            matches = re.findall(p, m.content)
            for match in matches:
                punct_counts[match[0]*3] += 1 # Normalize to 3 chars for display
        
        for match in REPEATED_CHAR_PATTERN.finditer(m.content):
            repeated_chars[match.group(0)] += 1

    return {
        "total_messages": total,
        "words": {
            "average": avg_words,
            "median": median_words,
            "p90": p90_words,
            "longest": longest_words,
            "shortest": shortest_words,
            "variance": variance_words,
            "std_dev": stddev_words
        },
        "timing": {
            "morning_pct": round(timing["morning"] / total * 100, 1),
            "afternoon_pct": round(timing["afternoon"] / total * 100, 1),
            "evening_pct": round(timing["evening"] / total * 100, 1),
            "night_pct": round(timing["night"] / total * 100, 1),
            "weekend_pct": round(timing["weekend"] / total * 100, 1),
            "weekday_pct": round(timing["weekday"] / total * 100, 1)
        },
        "delays": {
            "average_seconds": avg_delay,
            "fastest_seconds": fastest_delay,
            "slowest_seconds": slowest_delay
        },
        "quirks": {
            "punctuation_clusters": dict(punct_counts.most_common(5)),
            "repeated_letters": dict(repeated_chars.most_common(5))
        }
    }
