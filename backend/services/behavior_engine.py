"""
Behavior Engine
Analyzes conversation graphs, message types, pacing patterns, and communication signatures.
"""
import re
from collections import Counter, defaultdict
from datetime import timedelta
from typing import List
from models.domain import Message

# Strict Message Types
MODE_PATTERNS: dict[str, list[str]] = {
    "Acknowledgement": [r"^ok", r"^oh", r"^ah", r"^yeah", r"^yes", r"^no", r"^yaa", r"^ohhh", r"^ahh", r"^hmm", r"^yep", r"^nah", r"^k$"],
    "Question":        [r"\?"],
    "Joke":            [r"💀", r"🗿", r"lmfao", r"😭", r"\bhaha", r"\blol", r"\blmao", r"😂", r"🤣", r"\bjk\b"],
    "Story":           [r"so i", r"then i", r"and then", r"guess what", r"yesterday", r"today i"],
    "Advice":          [r"you should", r"don't do", r"maybe you", r"try to", r"better to", r"it's okay", r"don't worry"],
    "Explanation":     [r"because", r"actually", r"meaning", r"it means", r"so basically", r"the thing is", r"for example"],
    "Flirting":        [r"\bsayang\b", r"\bbaby\b", r"\bbabe\b", r"handsome", r"pretty", r"cute", r"💋", r"\blove\b", r"\bmiss\b", r"🩵", r"❤"],
}

def _classify_message(text: str) -> str:
    """Classifies a single message into its primary type."""
    text_lower = text.lower()
    for mode, patterns in MODE_PATTERNS.items():
        if any(re.search(p, text_lower, re.IGNORECASE) for p in patterns):
            return mode
    if len(text.split()) > 6:
        return "Opinion"
    return "Statement"

def compute_message_types(messages: List[Message], target_person: str) -> dict:
    target_msgs = [m for m in messages if m.sender == target_person and m.content != "<Media omitted>"]
    if not target_msgs:
        return {}

    type_counts = Counter()
    for msg in target_msgs:
        mtype = _classify_message(msg.content)
        type_counts[mtype] += 1

    total = sum(type_counts.values()) or 1
    return {
        mtype: f"{round(count / total * 100)}%"
        for mtype, count in type_counts.most_common()
    }

def compute_communication_signature(messages: List[Message], target_person: str) -> list:
    """
    Finds the most common sequence of message types sent in a single burst.
    e.g., ["Acknowledgement", "Statement", "Emoji/Joke"]
    """
    burst_sequences = []
    current_burst = []

    for msg in messages:
        if msg.sender == target_person and msg.content != "<Media omitted>":
            current_burst.append(_classify_message(msg.content))
        else:
            if len(current_burst) > 1:
                burst_sequences.append(tuple(current_burst))
            current_burst = []
            
    if len(current_burst) > 1:
        burst_sequences.append(tuple(current_burst))

    if not burst_sequences:
        return ["Statement"]

    sequence_counts = Counter(burst_sequences)
    most_common_seq = sequence_counts.most_common(1)[0][0]
    return list(most_common_seq)

def compute_pacing(messages: List[Message], target_person: str) -> dict:
    if not messages:
        return {}

    bursts = []
    current_burst = 0

    for msg in messages:
        if msg.sender == target_person and msg.content != "<Media omitted>":
            current_burst += 1
        else:
            if current_burst > 0:
                bursts.append(current_burst)
                current_burst = 0
    if current_burst > 0:
        bursts.append(current_burst)

    if not bursts:
        return {}

    total_bursts = len(bursts)
    avg_burst = round(sum(bursts) / total_bursts, 1)
    solo_rate = round(bursts.count(1) / total_bursts, 3)
    multi_rate = round(1 - solo_rate, 3)
    max_burst = max(bursts)

    burst_dist = Counter(min(b, 5) for b in bursts)

    return {
        "avg_consecutive_messages": avg_burst,
        "single_message_rate": solo_rate,
        "single_message_rate_pct": round(solo_rate * 100, 1),
        "multi_message_burst_rate_pct": round(multi_rate * 100, 1),
        "max_burst_observed": max_burst,
        "burst_distribution": {
            f"{k}_messages": round(v / total_bursts * 100, 1)
            for k, v in sorted(burst_dist.items())
        },
    }

def compute_conversation_graph(messages: List[Message]) -> dict:
    if not messages:
        return {}

    stats = {
        "topic_initiator": Counter(), 
        "reply_initiator": Counter(), 
        "closer": Counter(),          
        "extender": Counter()         
    }

    LONG_SILENCE = timedelta(minutes=60).total_seconds()
    SHORT_SILENCE = timedelta(minutes=5).total_seconds()

    stats["topic_initiator"][messages[0].sender] += 1

    for i in range(1, len(messages)):
        prev = messages[i-1]
        curr = messages[i]
        gap = (curr.timestamp - prev.timestamp).total_seconds()

        if gap > LONG_SILENCE:
            stats["topic_initiator"][curr.sender] += 1
            stats["closer"][prev.sender] += 1
        elif gap > SHORT_SILENCE:
            stats["reply_initiator"][curr.sender] += 1
        else:
            if curr.sender != prev.sender:
                stats["extender"][curr.sender] += 1
                
    if len(messages) > 0:
        stats["closer"][messages[-1].sender] += 1

    return {k: dict(v) for k, v in stats.items()}
