"""
Vocabulary Engine — 100% deterministic. No LLM.
Uses Counter + stopword removal (English-only stopwords so Indonesian
signature words like 'sayang', 'aku', 'kamu' are preserved as vocabulary).

Round 3 additions:
  - categorize_vocabulary(): buckets top words into semantic categories
  - detect_quirks(): finds abbreviations + letter-stretch patterns
"""
import re
from collections import Counter
from typing import List
from models.domain import Message

# Conservative English-only stopwords. Intentionally NOT including Indonesian
# so signature words like 'sayang', 'bro', 'aku', 'kamu' are preserved.
EN_STOPWORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you",
    "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself",
    "she", "her", "hers", "herself", "it", "its", "itself", "they", "them",
    "their", "theirs", "themselves", "what", "which", "who", "whom", "this",
    "that", "these", "those", "am", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "having", "do", "does", "did", "doing",
    "a", "an", "the", "and", "but", "if", "or", "because", "as", "until",
    "while", "of", "at", "by", "for", "with", "about", "against", "between",
    "into", "through", "during", "before", "after", "above", "below", "to",
    "from", "up", "down", "in", "out", "on", "off", "over", "under", "again",
    "further", "then", "once", "here", "there", "when", "where", "why", "how",
    "all", "both", "each", "few", "more", "most", "other", "some", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "s", "t", "can", "will", "just", "don", "should", "now", "d", "m", "o",
    "re", "ve", "y", "ain", "aren", "couldn", "didn", "doesn", "hadn", "hasn",
    "haven", "isn", "ma", "mightn", "mustn", "needn", "shan", "shouldn",
    "wasn", "weren", "won", "wouldn", "get", "got", "like", "also", "even",
    "well", "back", "one", "two", "three", "four", "five", "know", "think",
    "would", "could", "want", "gonna", "gotta",
}

PUNCT_RE = re.compile(r"[^\w\s'😭😂🥺💀🩵🎀🐣]")
EMOJI_RE = re.compile("[\U00010000-\U0010ffff]", flags=re.UNICODE)

# ─── Vocabulary categories ────────────────────────────────────────────────────

VOCAB_CATEGORIES: dict[str, list[str]] = {
    "pet_names":     ["sayang", "babe", "baby", "love", "hubby", "wifey", "dear", "darling"],
    "gaming":        ["ff", "mlbb", "rank", "skin", "game", "coa", "drop", "frag", "push", "tower"],
    "emotion":       ["miss", "love", "sleep", "eat", "tired", "happy", "sad", "cry", "hate", "excited"],
    "slang":         ["nahh", "otayy", "welp", "hmmm", "ngl", "imo", "fr", "rn", "lowkey", "highkey", "periodt", "slay", "bestie"],
    "abbreviations": ["u", "ur", "rn", "tmrw", "idk", "imo", "ngl", "cuz", "coz", "smh", "brb", "omw", "lmk", "wdym", "yk"],
}

# ─── Quirks detection ─────────────────────────────────────────────────────────

# Abbreviation words that signal informal typing style
ABBREVIATION_SET: set[str] = {
    "u", "ur", "r", "rn", "tmrw", "tmr", "idk", "imo", "ngl", "cuz", "coz",
    "smh", "brb", "omw", "lmk", "wdym", "yk", "fr", "tbh", "btw", "irl",
    "imo", "fyi", "omg", "wtf", "lol", "lmao", "dm", "hmu",
}

# Letter-stretch: same letter repeated 3+ times (ohhh, heyyy, noooo, otayyy)
LETTER_STRETCH_RE = re.compile(r"([a-z])\1{2,}", re.IGNORECASE)


def extract_vocabulary(messages: List[Message], target_person: str, top_n: int = 40) -> dict:
    """
    Returns the most frequently used words and signature phrases for target_person.
    Words are counted from real messages. No LLM involved.
    """
    word_counts: Counter = Counter()
    bigram_counts: Counter = Counter()

    target_msgs = [m for m in messages
                   if m.sender == target_person and m.content != "<Media omitted>"]

    for msg in target_msgs:
        # Strip punctuation but keep apostrophes and emoji
        text = PUNCT_RE.sub(" ", msg.content.lower())
        words = [w.strip("'") for w in text.split() if len(w) > 1]

        # Count individual words
        for word in words:
            if word not in EN_STOPWORDS:
                word_counts[word] += 1

        # Count bigrams (signature phrases)
        for i in range(len(words) - 1):
            a, b = words[i], words[i+1]
            if a not in EN_STOPWORDS and b not in EN_STOPWORDS:
                bigram_counts[f"{a} {b}"] += 1

    top_words = [{"word": w, "count": c} for w, c in word_counts.most_common(top_n)]
    top_bigrams = [{"phrase": p, "count": c} for p, c in bigram_counts.most_common(15)]

    # Words that NEVER appear (sampled from common formal vocabulary to build constraints)
    formal_words = ["certainly", "therefore", "indeed", "however", "furthermore",
                    "additionally", "consequently", "accordingly", "nevertheless", "nonetheless"]
    never_used = [w for w in formal_words if word_counts.get(w, 0) == 0]

    return {
        "top_words": top_words,
        "top_bigrams": top_bigrams,
        "never_used_formal_words": never_used,
        "total_unique_words": len(word_counts),
    }


def categorize_vocabulary(messages: List[Message], target_person: str) -> dict:
    """
    Buckets the target person's top words into semantic categories.
    Returns {category_name: [words_found_in_messages]}.
    Only includes categories where at least one word was actually used.
    """
    target_msgs = [m for m in messages
                   if m.sender == target_person and m.content != "<Media omitted>"]

    # Build a set of all unique words used by target person
    used_words: set[str] = set()
    for msg in target_msgs:
        text = PUNCT_RE.sub(" ", msg.content.lower())
        words = [w.strip("'") for w in text.split() if len(w) > 1]
        used_words.update(words)

    result: dict[str, list[str]] = {}
    for category, word_list in VOCAB_CATEGORIES.items():
        matched = [w for w in word_list if w in used_words]
        if matched:
            result[category] = matched

    return result


def detect_quirks(messages: List[Message], target_person: str) -> dict:
    """
    Finds informal typing quirks in the target person's actual messages:
    - Abbreviations actually used (u, ur, rn, idk, etc.)
    - Letter-stretch patterns (otayyy, nahhh, hmmm) via regex

    Returns:
        {
            "abbreviations_used": ["u", "ur", "idk", ...],
            "letter_stretches": ["hmmm", "otayyy", "nahh", ...],
            "abbreviation_count": 142,
            "letter_stretch_count": 38,
        }
    """
    target_msgs = [m for m in messages
                   if m.sender == target_person and m.content != "<Media omitted>"]

    abbrev_counter: Counter = Counter()
    stretch_counter: Counter = Counter()

    for msg in target_msgs:
        text_lower = msg.content.lower()
        # Tokenise simply — we want raw tokens to catch 'u', 'ur', etc.
        tokens = re.findall(r"[a-z']+", text_lower)
        for tok in tokens:
            if tok in ABBREVIATION_SET:
                abbrev_counter[tok] += 1

        # Find all stretch instances (ohhh, heyyy, …) — normalise to lowercase
        for match in LETTER_STRETCH_RE.finditer(text_lower):
            word = match.group(0)
            if len(word) >= 3:  # minimum 3-char stretch to avoid false positives
                stretch_counter[word] += 1

    # Return top abbreviations + stretches actually observed
    abbreviations_used = [w for w, _ in abbrev_counter.most_common(20)]
    letter_stretches = [w for w, _ in stretch_counter.most_common(20)]

    return {
        "abbreviations_used": abbreviations_used,
        "letter_stretches": letter_stretches,
        "abbreviation_count": sum(abbrev_counter.values()),
        "letter_stretch_count": sum(stretch_counter.values()),
    }
