"""
Topic Engine
Calculates the Topic Graph including percentages, confidence, average reply length, and weighted transition probabilities.
"""
from typing import List
from collections import Counter, defaultdict
from models.domain import Message
import statistics

TOPIC_KEYWORDS = {
    "Gaming": ["ff", "mlbb", "rank", "skin", "game", "play", "drop", "coa", "free fire", "mobile legend"],
    "Technology": ["code", "software", "hardware", "computer science", "cyber security", "bug", "app", "pc", "laptop", "server", "tech", "program"],
    "Learning": ["what is", "how to", "study", "exam", "assignment", "homework", "learn", "college", "class", "lecture"],
    "Daily Life": ["went to", "bought", "store", "bus", "car", "traffic", "weather", "rain", "sun", "hot", "cold"],
    "Food": ["eat", "ate", "food", "hungry", "dinner", "lunch", "breakfast", "cook", "restaurant", "drink"],
    "Sleep": ["sleep", "tired", "wake", "woke", "bed", "nap", "yawn", "dream"],
    "Anime": ["anime", "manga", "episode", "season", "naruto", "one piece", "watching", "weeb", "otaku"],
    "Career": ["work", "job", "office", "interview", "boss", "salary", "shift", "cashier", "manager", "meeting"],
}

def analyze_topics(messages: List[Message], target_person: str) -> dict:
    target_msgs = [m for m in messages if m.sender == target_person and m.content != "<Media omitted>"]
    if not target_msgs:
        return {}

    topic_counts = Counter()
    topic_lengths = defaultdict(list)
    topic_words = defaultdict(Counter)
    topic_snippets = defaultdict(list)
    
    transitions = defaultdict(Counter)
    last_topic = None

    for msg in target_msgs:
        text = msg.content.lower()
        words = text.split()
        
        current_topics = []
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                current_topics.append(topic)
                topic_counts[topic] += 1
                topic_lengths[topic].append(len(words))
                if len(topic_snippets[topic]) < 3:
                    topic_snippets[topic].append(msg.content[:100])
                for w in words:
                    if len(w) > 3: 
                        topic_words[topic][w] += 1
        
        if current_topics:
            primary_topic = current_topics[0]
            if last_topic and last_topic != primary_topic:
                transitions[last_topic][primary_topic] += 1
            last_topic = primary_topic

    total_matches = sum(topic_counts.values()) or 1
    
    graph = {}
    for topic, count in topic_counts.most_common():
        transitions_for_topic = transitions.get(topic, {})
        total_transitions = sum(transitions_for_topic.values()) or 1
        weighted_transitions = {
            t: f"{round(c / total_transitions * 100)}%" 
            for t, c in transitions_for_topic.most_common(3)
        }
        
        confidence = min(99, max(20, round(count * 3.5))) # Arbitrary scaling for confidence
        
        graph[topic] = {
            "percentage": round(count / total_matches * 100, 1),
            "confidence": confidence,
            "evidence_count": count,
            "average_reply_length": round(statistics.mean(topic_lengths[topic]), 1) if topic_lengths[topic] else 0,
            "most_common_words": [w[0] for w in topic_words[topic].most_common(5)],
            "weighted_transitions": weighted_transitions,
            "examples": topic_snippets[topic]
        }
        
    return graph
