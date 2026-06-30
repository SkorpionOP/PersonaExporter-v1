"""
Vocab Engine
Extracts words, categories, slang, abbreviations, and spellings.
"""
import re
from collections import Counter
from typing import List
from models.domain import Message

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

TOP_WORD_STOPWORDS = EN_STOPWORDS | {
    "im", "i'm", "dont", "don't", "thats", "that's", "good", "yes", "ok", "okay", 
    "yeah", "no", "just", "like", "really", "get", "got", "know", "think", "u", "ur", "go"
}

GLUE_WORDS = {
    "ok", "okay", "okayy", "oh", "ohh", "ohhh", "ah", "ahh", "yaa", "yeah", "yes", "yep", 
    "no", "noo", "nooo", "nah", "eum", "tell", "understand", "me", "meee", "im", "dont", 
    "lol", "lmao", "haha", "pls", "please", "sorry", "thanks", "thx", "btw", "omg", "idk", 
    "ik", "rn", "fr", "ngl", "tbh", "hm", "hmm", "hmmm", "see", "wait", "let", "go", "say"
}

PUNCT_RE = re.compile(r"[^\w\s'😭😂🥺💀🩵🎀🐣]")

VOCAB_CATEGORIES: dict[str, list[str]] = {
    "pet_names":     ["sayang", "babe", "baby", "love", "hubby", "wifey", "dear", "darling"],
    "gaming":        ["ff", "mlbb", "rank", "skin", "game", "coa", "drop", "frag", "push", "tower"],
    "emotion":       ["miss", "love", "sleep", "eat", "tired", "happy", "sad", "cry", "hate", "excited"],
    "slang":         ["nahh", "otayy", "welp", "hmmm", "ngl", "imo", "fr", "rn", "lowkey", "highkey", "periodt", "slay", "bestie"],
    "abbreviations": ["u", "ur", "rn", "tmrw", "idk", "imo", "ngl", "cuz", "coz", "smh", "brb", "omw", "lmk", "wdym", "yk"],
    "technology":    ["code", "software", "hardware", "computer science", "cyber security", "bug", "app", "pc", "laptop", "server"],
    "food":          ["eat", "ate", "food", "hungry", "dinner", "lunch", "breakfast", "cook", "restaurant", "drink"],
    "work":          ["work", "job", "office", "interview", "boss", "salary", "shift", "cashier", "manager"],
    "school":        ["study", "exam", "assignment", "homework", "learn", "college", "class", "lecture", "teacher", "professor"],
    "family":        ["mom", "dad", "sister", "brother", "grandma", "grandpa", "aunt", "uncle", "cousin"],
    "religion":      ["pray", "god", "church", "mosque", "temple", "amen", "bless", "sin", "faith"],
    "memes":         ["doge", "pepe", "chad", "sigma", "skibidi", "rizz", "gyatt", "based", "cringe"],
    "misspellings":  ["definetly", "recieve", "seperate", "untill", "wierd", "alot", "tommorow"],
}

PREFERRED_SPELLINGS_SETS = [
    {"because", "bc", "cuz", "cause"},
    {"you", "u"},
    {"your", "ur"},
    {"please", "pls", "plz"},
    {"tomorrow", "tmrw", "tmr"},
    {"right now", "rn"}
]

LETTER_STRETCH_RE = re.compile(r"([a-z])\1{2,}", re.IGNORECASE)

def extract_vocabulary(messages: List[Message], target_person: str, top_n: int = 40) -> dict:
    word_counts: Counter = Counter()
    bigram_counts: Counter = Counter()
    target_msgs = [m for m in messages if m.sender == target_person and m.content != "<Media omitted>"]

    for msg in target_msgs:
        text = PUNCT_RE.sub(" ", msg.content.lower())
        words = [w.strip("'") for w in text.split() if len(w) > 1]

        for word in words:
            if word not in TOP_WORD_STOPWORDS:
                word_counts[word] += 1

        for i in range(len(words) - 1):
            a, b = words[i], words[i+1]
            if a not in EN_STOPWORDS and b not in EN_STOPWORDS:
                is_glue = (a in GLUE_WORDS) or (b in GLUE_WORDS) or (len(a) > 2 and a[-1] == a[-2] == a[-3]) or (len(b) > 2 and b[-1] == b[-2] == b[-3])
                if is_glue:
                    bigram_counts[f"{a} {b}"] += 1

    top_words = [{"word": w, "count": c} for w, c in word_counts.most_common(top_n)]
    top_bigrams = [{"phrase": p, "count": c} for p, c in bigram_counts.most_common(15)]
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
    target_msgs = [m for m in messages if m.sender == target_person and m.content != "<Media omitted>"]
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
    target_msgs = [m for m in messages if m.sender == target_person and m.content != "<Media omitted>"]
    abbrev_counter: Counter = Counter()
    stretch_counter: Counter = Counter()
    preferred_spellings = {}

    for msg in target_msgs:
        text_lower = msg.content.lower()
        tokens = re.findall(r"[a-z']+", text_lower)
        for tok in tokens:
            if tok in VOCAB_CATEGORIES["abbreviations"]:
                abbrev_counter[tok] += 1
                
        for match in LETTER_STRETCH_RE.finditer(text_lower):
            word = match.group(0)
            if len(word) >= 3:
                stretch_counter[word] += 1

    # Preferred spellings logic
    all_words = []
    for msg in target_msgs:
        all_words.extend(re.findall(r"[a-z']+", msg.content.lower()))
    word_freq = Counter(all_words)
    
    for spell_set in PREFERRED_SPELLINGS_SETS:
        best_match = None
        best_count = -1
        for variant in spell_set:
            if word_freq[variant] > best_count:
                best_match = variant
                best_count = word_freq[variant]
        if best_count > 0:
            preferred_spellings["/".join(spell_set)] = best_match

    return {
        "abbreviations_used": [w for w, _ in abbrev_counter.most_common(20)],
        "letter_stretches": [w for w, _ in stretch_counter.most_common(20)],
        "abbreviation_count": sum(abbrev_counter.values()),
        "letter_stretch_count": sum(stretch_counter.values()),
        "preferred_spellings": preferred_spellings
    }
