"""
Formatting Engine — 100% deterministic. No LLM.
Uses regex to derive concrete formatting rules from real message patterns.
"""
import re
from collections import Counter
from typing import List
from models.domain import Message


REPEATED_CHAR_RE = re.compile(r'([a-zA-Z])\1{2,}')  # nooo, heyyyy
ELLIPSIS_RE = re.compile(r'\.{2,}')
MULTI_EXCLAIM_RE = re.compile(r'!{2,}')
MULTI_QUESTION_RE = re.compile(r'\?{2,}')
CAPS_WORD_RE = re.compile(r'\b[A-Z]{3,}\b')
NO_PERIOD_RE = re.compile(r'[a-zA-Z]$')           # msg ends without punctuation
SPLIT_THOUGHT_RE = re.compile(r'^[a-z].{0,30}$')  # short lowercase fragment


def extract_formatting(messages: List[Message], target_person: str, stats: dict) -> dict:
    """
    Derives concrete, evidence-backed formatting rules from raw message patterns.
    Every rule includes a confidence score and occurrence count.
    """
    target_msgs = [m for m in messages
                   if m.sender == target_person and m.content != "<Media omitted>"]
    total = len(target_msgs)
    if total == 0:
        return {}

    repeated_char_count = 0
    ellipsis_count = 0
    multi_exclaim_count = 0
    multi_question_count = 0
    caps_word_msgs = 0
    no_period_count = 0
    split_thought_count = 0
    examples = {
        "repeated_chars": [],
        "ellipsis": [],
        "all_caps": [],
    }

    for msg in target_msgs:
        text = msg.content
        if REPEATED_CHAR_RE.search(text):
            repeated_char_count += 1
            if len(examples["repeated_chars"]) < 5:
                examples["repeated_chars"].append(text[:60])
        if ELLIPSIS_RE.search(text):
            ellipsis_count += 1
            if len(examples["ellipsis"]) < 5:
                examples["ellipsis"].append(text[:60])
        if MULTI_EXCLAIM_RE.search(text):
            multi_exclaim_count += 1
        if MULTI_QUESTION_RE.search(text):
            multi_question_count += 1
        if CAPS_WORD_RE.search(text):
            caps_word_msgs += 1
            if len(examples["all_caps"]) < 5:
                examples["all_caps"].append(text[:60])
        if NO_PERIOD_RE.search(text):
            no_period_count += 1
        if SPLIT_THOUGHT_RE.match(text):
            split_thought_count += 1

    rules = []

    if stats.get("lowercase_rate", 0) > 0.75:
        rules.append({
            "rule": "Writes in lowercase",
            "confidence": round(stats["lowercase_rate"] * 100, 1),
            "evidence": f"{int(stats['lowercase_rate']*total)} of {total} messages"
        })
    if repeated_char_count / total > 0.10:
        rules.append({
            "rule": "Stretches letters for emphasis (e.g. noooo, heyyyy)",
            "confidence": round(repeated_char_count / total * 100, 1),
            "evidence": f"{repeated_char_count} occurrences",
            "examples": examples["repeated_chars"]
        })
    if ellipsis_count / total > 0.05:
        rules.append({
            "rule": "Uses '...' instead of commas or pauses",
            "confidence": round(ellipsis_count / total * 100, 1),
            "evidence": f"{ellipsis_count} occurrences",
            "examples": examples["ellipsis"]
        })
    if no_period_count / total > 0.70:
        rules.append({
            "rule": "Almost never ends messages with a period",
            "confidence": round(no_period_count / total * 100, 1),
            "evidence": f"{no_period_count} of {total} messages have no closing period"
        })
    if split_thought_count / total > 0.20:
        rules.append({
            "rule": "Splits long thoughts into multiple short messages",
            "confidence": round(split_thought_count / total * 100, 1),
            "evidence": f"{split_thought_count} short fragment messages detected"
        })
    if caps_word_msgs / total > 0.05:
        rules.append({
            "rule": "Uses ALL CAPS for emphasis or excitement",
            "confidence": round(caps_word_msgs / total * 100, 1),
            "evidence": f"{caps_word_msgs} messages",
            "examples": examples["all_caps"]
        })
    if multi_exclaim_count / total > 0.05:
        rules.append({
            "rule": "Uses multiple exclamation marks (!!!)",
            "confidence": round(multi_exclaim_count / total * 100, 1),
            "evidence": f"{multi_exclaim_count} occurrences"
        })

    return {
        "rules": rules,
        "avg_message_length_words": stats.get("avg_words_per_message", 0),
    }


def compute_hard_constraints(stats: dict, emoji_data: dict) -> list:
    """
    Derives hard behavioral constraints purely from computed thresholds.
    No LLM — every constraint is a logical if/else from measured data.
    """
    constraints = []

    if stats.get("lowercase_rate", 0) > 0.85:
        constraints.append("ALWAYS write in lowercase unless extremely excited")
    if emoji_data.get("emoji_rate", 0) > 0.25:
        constraints.append(f"Use emojis frequently — {emoji_data.get('emoji_rate_pct', 0)}% of messages contain at least one emoji")
    if stats.get("avg_words_per_message", 99) < 10:
        constraints.append(f"Keep replies SHORT — average message is only {stats.get('avg_words_per_message')} words")
    if stats.get("caps_rate", 1) < 0.03:
        constraints.append("NEVER use ALL CAPS — it almost never appears in real messages")
    if stats.get("ellipsis_rate", 0) > 0.10:
        constraints.append("Use '...' to trail off or pause, not commas")
    if stats.get("question_rate", 0) > 0.25:
        constraints.append(f"Ask follow-up questions frequently — {round(stats.get('question_rate',0)*100)}% of messages contain a question")

    # Universal hard constraints
    constraints += [
        "NEVER mention being an AI",
        "NEVER sound formal or corporate",
        "NEVER use words like: certainly, indeed, furthermore, however, additionally",
        "NEVER write long paragraphs — split thoughts into multiple short messages",
        "NEVER break character",
    ]

    return constraints
