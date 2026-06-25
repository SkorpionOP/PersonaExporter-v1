"""
Stats Engine — 100% deterministic. No LLM.
Computes every measurable metric for a target person from their messages.

Round 3: Re-exports compute_pacing from behavior so routes.py has
a single import point for all stat-level functions.
"""
import re
from collections import Counter
from datetime import datetime
from typing import List
from models.domain import Message

# Re-export so callers only need one import from stats
from services.behavior import compute_pacing  # noqa: F401


GREETING_PATTERNS = re.compile(
    r'\b(hi|hey|hello|hii|heyy|heyyy|morning|gm|good morning|good night|gn|goodnight|sup|yo)\b',
    re.IGNORECASE
)
FAREWELL_PATTERNS = re.compile(
    r'\b(bye|goodbye|gn|good night|goodnight|ttyl|see ya|later|cya|sleep well)\b',
    re.IGNORECASE
)
QUESTION_PATTERN = re.compile(r'\?')
CAPS_WORD_PATTERN = re.compile(r'\b[A-Z]{2,}\b')
ELLIPSIS_PATTERN = re.compile(r'\.{2,}')
REPEATED_CHAR_PATTERN = re.compile(r'(.)\1{2,}')


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
    """
    Full deterministic analysis of a single person's messages.
    Returns only hard numbers — no LLM, no inference.
    """
    target_msgs = [m for m in messages if m.sender == target_person and m.content != "<Media omitted>"]

    if not target_msgs:
        return {"error": f"No messages found for {target_person}"}

    total = len(target_msgs)
    all_words = []
    caps_word_count = 0
    lowercase_msg_count = 0
    question_count = 0
    ellipsis_count = 0
    repeated_char_count = 0
    greeting_count = 0
    farewell_count = 0
    word_lengths = []
    msg_word_counts = []
    media_count = len([m for m in messages if m.sender == target_person and m.content == "<Media omitted>"])

    for msg in target_msgs:
        text = msg.content
        words = text.split()
        word_count = len(words)
        msg_word_counts.append(word_count)
        all_words.extend(w.lower() for w in words)
        word_lengths.extend(len(w) for w in words)

        if text == text.lower():
            lowercase_msg_count += 1
        if QUESTION_PATTERN.search(text):
            question_count += 1
        if ELLIPSIS_PATTERN.search(text):
            ellipsis_count += 1
        if REPEATED_CHAR_PATTERN.search(text):
            repeated_char_count += 1
        if GREETING_PATTERNS.search(text):
            greeting_count += 1
        if FAREWELL_PATTERNS.search(text):
            farewell_count += 1

        caps_words = CAPS_WORD_PATTERN.findall(text)
        caps_word_count += len(caps_words)

    avg_words = round(sum(msg_word_counts) / total, 1)
    avg_word_len = round(sum(word_lengths) / max(len(word_lengths), 1), 1)
    lowercase_rate = round(lowercase_msg_count / total, 3)
    question_rate = round(question_count / total, 3)
    ellipsis_rate = round(ellipsis_count / total, 3)
    repeated_char_rate = round(repeated_char_count / total, 3)
    caps_rate = round(caps_word_count / max(len(all_words), 1), 3)

    return {
        "total_messages": total,
        "media_messages": media_count,
        "avg_words_per_message": avg_words,
        "avg_word_length": avg_word_len,
        "lowercase_rate": lowercase_rate,
        "question_rate": question_rate,
        "ellipsis_rate": ellipsis_rate,
        "repeated_char_rate": repeated_char_rate,
        "caps_rate": caps_rate,
        "greeting_count": greeting_count,
        "farewell_count": farewell_count,
        "greeting_rate": round(greeting_count / total, 3),
        "farewell_rate": round(farewell_count / total, 3),
    }
