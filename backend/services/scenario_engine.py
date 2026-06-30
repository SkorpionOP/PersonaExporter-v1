"""
Scenario Engine
Extracts expansive scenario libraries mapping specific intents to real conversational examples using semantic similarity.
"""
from typing import List, Optional
from collections import defaultdict
from models.domain import Message
from datetime import timedelta
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    import torch
    # Load lightweight model for semantic matching
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
except ImportError:
    model = None

SCENARIO_KEYWORDS = {
    "Greeting":   ["hi", "hey", "hello", "hii", "heyy", "morning", "gm", "good morning", "sup", "yo"],
    "Goodbye":    ["bye", "gn", "good night", "goodnight", "gonna sleep", "sleep na", "going now", "ttyl", "cya"],
    "Gaming":     ["ff", "mlbb", "rank", "skin", "game", "play", "drop", "coa", "free fire", "mobile legend"],
    "Comfort":    ["i'm sad", "im sad", "i cried", "crying", "feeling down", "i failed", "i'm upset", "im upset", "im hurt", "i'm hurt"],
    "Excited":    ["i won", "i got", "i passed", "we won", "i did it", "finally", "look at this", "omg", "bestie"],
    "Late Reply": ["sorry late", "just woke", "was busy", "fell asleep", "i was"],
    "Apology":    ["i'm sorry", "im sorry", "my bad", "sorry for", "i apologize"],
    "Flirting":   ["ur cute", "you're cute", "handsome", "pretty", "love you", "miss you", "sayang", "babe", "baby", "hug", "kiss"],
    "Food":       ["eat", "ate", "food", "hungry", "dinner", "lunch", "breakfast", "cook", "restaurant", "drink"],
    "Anime":      ["anime", "manga", "episode", "season", "naruto", "one piece", "watching", "weeb", "otaku"],
    "Technology": ["code", "software", "hardware", "computer science", "cyber security", "bug", "app", "pc", "laptop", "server", "tech", "program"],
}

MAX_TIME_GAP = timedelta(seconds=120)
MAX_INTERVENING_MESSAGES = 2
SEMANTIC_THRESHOLD = 0.15 # Minimum cosine similarity to consider it a valid connected response

def _is_valid_reply(messages: List[Message], trigger_idx: int, target_person: str) -> Optional[Message]:
    trigger_msg = messages[trigger_idx]
    intervening = 0
    for j in range(trigger_idx + 1, min(trigger_idx + MAX_INTERVENING_MESSAGES + 2, len(messages))):
        reply = messages[j]
        if reply.sender == target_person and reply.content != "<Media omitted>":
            time_gap = (reply.timestamp - trigger_msg.timestamp).total_seconds()
            
            # Semantic Similarity Check
            if model:
                emb1 = model.encode(trigger_msg.content)
                emb2 = model.encode(reply.content)
                sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-9)
                if sim < SEMANTIC_THRESHOLD:
                    continue

            if 0 <= time_gap <= MAX_TIME_GAP.total_seconds():
                return reply
            if intervening <= 1:
                return reply
        elif reply.sender != target_person:
            intervening += 1
            if intervening > MAX_INTERVENING_MESSAGES:
                break
    return None

def extract_scenario_library(messages: List[Message], target_person: str) -> dict:
    """
    Builds a large library of real user->assistant pairs for defined intents.
    Returns up to 30 examples per category to provide massive context to LLMs.
    """
    library = defaultdict(list)
    
    for i, msg in enumerate(messages):
        if msg.sender == target_person:
            continue
        msg_lower = msg.content.lower()

        for scenario_label, trigger_phrases in SCENARIO_KEYWORDS.items():
            if any(phrase in msg_lower for phrase in trigger_phrases):
                if len(library[scenario_label]) >= 30:
                    continue
                reply = _is_valid_reply(messages, i, target_person)
                if reply:
                    library[scenario_label].append({
                        "user": msg.content[:150],
                        "assistant": reply.content[:150],
                    })
                break
                
    return dict(library)
