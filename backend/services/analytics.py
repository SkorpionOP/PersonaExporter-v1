from typing import Dict, Any

def compare_personas(p1: Dict[str, Any], p2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares two persona data payloads and returns deltas and similarities.
    """
    ts1 = p1.get("target_stats", {})
    ts2 = p2.get("target_stats", {})
    
    # 1. Delta Stats
    deltas = {
        "avg_words_per_message": round(ts1.get("avg_words_per_message", 0) - ts2.get("avg_words_per_message", 0), 2),
        "emoji_rate_pct": round(p1.get("emojis", {}).get("emoji_rate_pct", 0) - p2.get("emojis", {}).get("emoji_rate_pct", 0), 2),
        "question_rate_pct": round((ts1.get("question_rate", 0) - ts2.get("question_rate", 0)) * 100, 2),
    }
    
    # 2. Vocabulary Overlap
    vocab1 = p1.get("vocab", {}).get("top_words", [])
    vocab2 = p2.get("vocab", {}).get("top_words", [])
    
    v1_set = {w["word"] for w in vocab1[:50]}
    v2_set = {w["word"] for w in vocab2[:50]}
    
    overlap = v1_set.intersection(v2_set)
    union = v1_set.union(v2_set)
    vocab_similarity = round((len(overlap) / len(union) * 100) if union else 0, 1)
    
    # 3. Pacing Comparison
    pacing1 = p1.get("pacing", {})
    pacing2 = p2.get("pacing", {})
    
    return {
        "deltas": deltas,
        "vocabulary": {
            "similarity_pct": vocab_similarity,
            "shared_words": list(overlap)[:15]
        },
        "pacing": {
            "p1_avg_burst": pacing1.get("avg_consecutive_messages", 0),
            "p2_avg_burst": pacing2.get("avg_consecutive_messages", 0),
            "p1_single_msg_rate": pacing1.get("single_message_rate_pct", 0),
            "p2_single_msg_rate": pacing2.get("single_message_rate_pct", 0),
        }
    }
