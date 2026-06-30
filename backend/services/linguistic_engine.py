"""
Linguistic Engine
Analyzes writing style, lexical richness, and message structure.
"""
from typing import List
from collections import Counter
from models.domain import Message
from datetime import datetime
import statistics
import emoji
import re

def analyze_linguistics(messages: List[Message], target_person: str) -> dict:
    target_msgs = [m for m in messages if m.sender == target_person and m.content != "<Media omitted>"]
    if not target_msgs:
        return {"error": "No messages found"}

    sentence_lengths = []
    paragraph_lengths = []
    clauses_counts = []
    
    emoji_placement = {"start": 0, "middle": 0, "end": 0, "solo": 0}
    question_placement = {"start": 0, "middle": 0, "end": 0, "solo": 0}
    
    one_word_replies = 0
    fragments = 0
    total_line_breaks = 0
    multi_paragraph_msgs = 0
    total_emojis = 0
    total_questions = 0

    all_words = []
    days_active = set()

    for msg in target_msgs:
        text = msg.content
        words = text.split()
        days_active.add(msg.timestamp.date())
        
        if len(words) == 1:
            one_word_replies += 1
            
        all_words.extend([w.lower().strip(".,!?\"'") for w in words])

        total_line_breaks += text.count('\n')
        paragraphs = text.split('\n')
        paragraph_lengths.append(len(paragraphs))
        if len(paragraphs) > 1:
            multi_paragraph_msgs += 1
            
        for p in paragraphs:
            sentences = re.split(r'[.!?]+', p)
            sentences = [s.strip() for s in sentences if s.strip()]
            for s in sentences:
                s_words = s.split()
                sentence_lengths.append(len(s_words))
                if len(s_words) < 3:
                    fragments += 1
                # Estimate clauses by splitting on conjunctions and commas
                clauses = re.split(r',|\band\b|\bbut\b|\bbecause\b|\bso\b', s, flags=re.IGNORECASE)
                clauses_counts.append(len([c for c in clauses if c.strip()]))

        emojis_found = [c for c in text if c in emoji.EMOJI_DATA]
        total_emojis += len(emojis_found)
        if emojis_found:
            if len(words) == 0:
                emoji_placement["solo"] += 1
            else:
                first_char_emoji = text[0] in emoji.EMOJI_DATA
                last_char_emoji = text[-1] in emoji.EMOJI_DATA
                if first_char_emoji and last_char_emoji and len(emojis_found) == len(text.replace(" ", "")):
                    emoji_placement["solo"] += 1
                elif first_char_emoji:
                    emoji_placement["start"] += 1
                elif last_char_emoji:
                    emoji_placement["end"] += 1
                else:
                    emoji_placement["middle"] += 1

        qs = text.count('?')
        total_questions += qs
        if qs > 0:
            if text.strip() == '?':
                question_placement["solo"] += 1
            elif text.strip().startswith('?'):
                question_placement["start"] += 1
            elif text.strip().endswith('?'):
                question_placement["end"] += 1
            else:
                question_placement["middle"] += 1

    total = len(target_msgs)
    unique_words = len(set(all_words))
    total_word_count = len(all_words)
    ttr = round(unique_words / total_word_count, 3) if total_word_count > 0 else 0
    repetition_score = round((1 - ttr) * 100, 1)

    return {
        "sentence_metrics": {
            "average_length": round(statistics.mean(sentence_lengths), 1) if sentence_lengths else 0,
            "average_clauses": round(statistics.mean(clauses_counts), 1) if clauses_counts else 0,
            "fragments_pct": round(fragments / max(len(sentence_lengths), 1) * 100, 1),
            "one_word_replies_pct": round(one_word_replies / total * 100, 1),
        },
        "structure_metrics": {
            "paragraph_frequency_pct": round(multi_paragraph_msgs / total * 100, 1),
            "total_line_breaks": total_line_breaks,
            "emojis_per_message": round(total_emojis / total, 2),
            "questions_per_message": round(total_questions / total, 2),
        },
        "lexical_richness": {
            "unique_words": unique_words,
            "type_token_ratio": ttr,
            "repetition_score": repetition_score,
            "average_new_words_per_day": round(unique_words / max(len(days_active), 1), 1)
        },
        "emoji_placement": {k: round(v / max(sum(emoji_placement.values()), 1) * 100, 1) for k, v in emoji_placement.items()},
        "question_placement": {k: round(v / max(sum(question_placement.values()), 1) * 100, 1) for k, v in question_placement.items()},
    }
