"""
Behavior Engine — Round 3.
- Time-gap validated trigger matching (fixes the "rice" bug)
- Scenario Library bucketed by intent
- Response Modes with probabilities (no LLM)
- Conversation Pacing (burst analysis)
"""
import random
import re
from collections import Counter, defaultdict
from datetime import timedelta
from typing import List, Optional
from models.domain import Message

# ─── Scenario / Trigger config ───────────────────────────────────────────────

SCENARIO_KEYWORDS: dict[str, list[str]] = {
    "greeting": ["hi", "hey", "hello", "hii", "heyy", "morning", "gm", "good morning", "sup", "yo"],
    "goodbye":  ["bye", "gn", "good night", "goodnight", "gonna sleep", "sleep na", "going now", "ttyl", "cya"],
    "missing":  ["i miss u", "miss you", "miss u", "i miss you"],
    "comfort":  ["i'm sad", "im sad", "i cried", "crying", "feeling down", "i failed", "i'm upset", "im upset", "im hurt", "i'm hurt"],
    "excited":  ["i won", "i got", "i passed", "we won", "i did it", "finally", "look at this", "omg", "bestie"],
    "teasing":  ["haha", "got u", "got you", "caught u", "caught you", "imagine", "embarrassing"],
    "gaming":   ["ff", "mlbb", "rank", "skin", "game", "play", "drop", "coa", "free fire", "mobile legend"],
    "late reply": ["sorry late", "just woke", "was busy", "fell asleep", "i was"],
    "advice":   ["what should i", "should i", "help me", "what do u think", "what do you think"],
    "checking in": ["how are u", "u ok", "u good", "u ate", "did u eat", "have u eaten"],
    "sleep reminder": ["go sleep", "sleep na", "rest na", "u should sleep", "sleep already"],
    "apology":  ["i'm sorry", "im sorry", "my bad", "sorry for", "i apologize"],
    "celebration": ["happy birthday", "congrats", "congratulations", "well done", "proud of u"],
}

# ─── Response mode keyword/pattern config ────────────────────────────────────

MODE_PATTERNS: dict[str, list[str]] = {
    "playful":      [r"\bhaha\b", r"\blol\b", r"\blmao\b", r"😂", r"🤣", r"\bjk\b", r"\bkidding\b", r"\bgot u\b", r"\bcaught\b"],
    "affectionate": [r"\bsayang\b", r"\blove\b", r"\bmiss\b", r"🩵", r"❤", r"🥹", r"\bbaby\b", r"\bbabe\b", r"\bhugs?\b", r"💋"],
    "dry":          [r"^ok\.?$", r"^oh\.?$", r"^yeah\.?$", r"^lol\.?$", r"^💀$", r"^🗿$", r"^k$", r"^sure$", r"^nah$"],
    "teasing":      [r"\bimagine\b", r"\bur so\b", r"\byou're so\b", r"caught", r"💀", r"😭.*pls", r"\bnot u\b"],
    "informative":  [],  # fallback: long messages with no mode match
}

# ─── Trigger extraction ───────────────────────────────────────────────────────

MAX_TIME_GAP = timedelta(seconds=120)
MAX_INTERVENING_MESSAGES = 2


def _is_valid_reply(
    messages: List[Message],
    trigger_idx: int,
    target_person: str,
) -> Optional[Message]:
    """
    Finds a valid reply from target_person to messages[trigger_idx].
    Valid = target replies within MAX_INTERVENING_MESSAGES messages AND MAX_TIME_GAP seconds.
    """
    trigger_msg = messages[trigger_idx]
    intervening = 0
    for j in range(trigger_idx + 1, min(trigger_idx + MAX_INTERVENING_MESSAGES + 2, len(messages))):
        reply = messages[j]
        if reply.sender == target_person and reply.content != "<Media omitted>":
            time_gap = (reply.timestamp - trigger_msg.timestamp).total_seconds()
            if 0 <= time_gap <= MAX_TIME_GAP.total_seconds():
                return reply
            # Within message proximity but too long — still accept if ≤1 intervening msg
            if intervening <= 1:
                return reply
        elif reply.sender != target_person:
            intervening += 1
            if intervening > MAX_INTERVENING_MESSAGES:
                break
    return None


def extract_trigger_responses(messages: List[Message], target_person: str) -> list:
    """
    For each scenario category, finds REAL, time-validated (trigger → reply) pairs.
    Fixes the proximity bug where unrelated messages were returned.
    """
    results = []

    for scenario_label, trigger_phrases in SCENARIO_KEYWORDS.items():
        collected = []
        for i, msg in enumerate(messages):
            if msg.sender == target_person:
                continue  # trigger must come from the OTHER person
            msg_lower = msg.content.lower()
            if any(phrase in msg_lower for phrase in trigger_phrases):
                reply = _is_valid_reply(messages, i, target_person)
                if reply and reply.content not in collected:
                    collected.append({
                        "trigger": msg.content[:120],
                        "response": reply.content[:120],
                    })
            if len(collected) >= 8:
                break

        if collected:
            results.append({
                "scenario": scenario_label,
                "examples": collected[:8],
            })

    return results


# ─── Scenario Library ─────────────────────────────────────────────────────────

def build_scenario_library(messages: List[Message], target_person: str) -> dict:
    """
    Groups validated (trigger→reply) pairs into labeled scenario buckets.
    Returns a dict of scenario_label → list of real (user, assistant) pairs.
    """
    library: dict[str, list] = defaultdict(list)

    for i, msg in enumerate(messages):
        if msg.sender == target_person:
            continue
        msg_lower = msg.content.lower()

        for scenario_label, trigger_phrases in SCENARIO_KEYWORDS.items():
            if any(phrase in msg_lower for phrase in trigger_phrases):
                if len(library[scenario_label]) >= 10:
                    continue
                reply = _is_valid_reply(messages, i, target_person)
                if reply:
                    library[scenario_label].append({
                        "user": msg.content[:120],
                        "assistant": reply.content[:120],
                    })
                break  # Only count each trigger message once

    return dict(library)


# ─── General real conversation pairs ─────────────────────────────────────────

def sample_real_conversations(messages: List[Message], target_person: str, n: int = 30) -> list:
    """
    Real (other→target_person) pairs with time-gap validation.
    """
    pairs = []
    for i, msg in enumerate(messages):
        if msg.sender == target_person or msg.content == "<Media omitted>":
            continue
        reply = _is_valid_reply(messages, i, target_person)
        if reply:
            pairs.append({"user": msg.content[:120], "assistant": reply.content[:120]})

    return random.sample(pairs, min(n, len(pairs))) if len(pairs) > n else pairs


# ─── Response Modes ───────────────────────────────────────────────────────────

def compute_response_modes(messages: List[Message], target_person: str) -> dict:
    """
    Classifies each of target_person's messages into a response mode.
    Returns probabilities for each mode — all deterministic, no LLM.
    """
    target_msgs = [m for m in messages
                   if m.sender == target_person and m.content != "<Media omitted>"]
    if not target_msgs:
        return {}

    mode_counts = Counter({"playful": 0, "affectionate": 0, "dry": 0, "teasing": 0, "informative": 0})

    for msg in target_msgs:
        text = msg.content
        matched = False
        for mode, patterns in MODE_PATTERNS.items():
            if not patterns:
                continue
            if any(re.search(p, text, re.IGNORECASE) for p in patterns):
                mode_counts[mode] += 1
                matched = True
                break
        if not matched and len(text.split()) >= 5:
            mode_counts["informative"] += 1

    total = sum(mode_counts.values()) or 1
    return {
        mode: {
            "probability": round(count / total, 3),
            "probability_pct": round(count / total * 100, 1),
            "count": count,
        }
        for mode, count in mode_counts.most_common()
        if count > 0
    }


# ─── Conversation Pacing ──────────────────────────────────────────────────────

def compute_pacing(messages: List[Message], target_person: str) -> dict:
    """
    Analyzes burst patterns — how many consecutive messages target_person sends.
    """
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
