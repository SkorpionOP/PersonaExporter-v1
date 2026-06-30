"""
LLM Engine
Infers behaviors that machines cannot compute:
  - Question style, Conversation energy, Conversation role, Rhythm, Topic memory
  - Contradictions, Conversation Fingerprint, Style Drift, Emotional Triggers
ALL inferences use a strict Evidence Block schema.
"""
import json
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url='http://localhost:11434/v1',
    api_key='ollama'
)
MODEL_NAME = "qwen2.5:1.5b"

async def infer_behavior_patterns(
    conversation_text: str,
    target_person: str,
    hard_stats: dict,
) -> dict:
    top_words = [w["word"] for w in hard_stats.get("vocab", {}).get("top_words", [])[:15]]
    top_emojis = [e["emoji"] for e in hard_stats.get("emojis", {}).get("top_emojis", [])[:5]]

    context = f"""
MEASURED FACTS about {target_person} (do NOT reinvent these — they are already computed):
- Average words per message: {hard_stats.get("stats", {}).get("avg_words_per_message", "?")}
- Lowercase rate: {round(hard_stats.get("stats", {}).get("lowercase_rate", 0) * 100, 1)}%
- Emoji rate: {hard_stats.get("emojis", {}).get("emoji_rate_pct", "?")}%
- Question rate: {round(hard_stats.get("stats", {}).get("question_rate", 0) * 100, 1)}%
- Top 15 words used: {top_words}
- Top emojis: {top_emojis}

REAL CONVERSATION SAMPLES (Start, Middle, and Latest messages from {target_person}):
{conversation_text[:16000]}
"""

    prompt = f"""
You are a behavioral extractor. Your job is to observe ONLY.
Do NOT summarize. Do NOT describe personality in adjectives.
Do NOT write a system prompt. Return ONLY valid JSON.

Based on the facts and conversation sample above, infer ONLY these behaviors for "{target_person}".
EVERY inference MUST include an "evidence_block" with "confidence" (0-100), "detected" (brief observation count), and "examples" (list of 1-2 short quotes).

{{
  "contradictions": [
    {{"behavior": "Usually reserved", "but": "Very expressive after midnight", "evidence_block": {{"confidence": 88, "detected": "Late night chats", "examples": []}}}}
  ],
  "conversation_fingerprint": {{
    "reactive": 9, "curiosity": 8, "humor": 4, "warmth": 6, "directness": 8, "verbosity": 2, "initiative": 3, "playfulness": 5
  }},
  "style_drift": {{
    "first_third": "Formal", "middle_third": "Comfortable", "latest_third": "Playful",
    "evidence_block": {{"confidence": 92, "detected": "Evolution across dataset", "examples": []}}
  }},
  "emotional_triggers": {{
    "playful_when": ["Gaming", "Anime", "Memes"],
    "serious_when": ["Work", "Family"],
    "evidence_block": {{"confidence": 85, "detected": "Topic correlations", "examples": []}}
  }},
  "question_style": {{
    "patterns": ["Uses clarification questions", "Rarely asks multiple questions"],
    "often_replies_with": ["Really?", "Ohhh?", "How?"],
    "evidence_block": {{"confidence": 96, "detected": "18 question exchanges", "examples": ["Is what?"]}}
  }},
  "conversation_energy": {{
    "traits": ["Mostly reactive", "Frequently acknowledges", "Often mirrors user's topic"],
    "evidence_block": {{"confidence": 91, "detected": "Overall pattern", "examples": []}}
  }},
  "conversation_role": {{
    "primary": "Listener", "secondary": "Question Asker", "tertiary": "Learner",
    "evidence_block": {{"confidence": 85, "detected": "Role dynamics", "examples": []}}
  }},
  "conversation_rhythm": {{
    "typical_rhythm": ["User", "Short acknowledgement", "Clarification question", "Small opinion", "Ends"],
    "evidence_block": {{"confidence": 88, "detected": "30 multi-turn exchanges", "examples": []}}
  }},
  "comfort_style": {{
    "observed_sequence": ["User sad", "Short validation", "Short reassurance", "Humor", "Topic shift"],
    "evidence_block": {{"confidence": 90, "detected": "23 comfort conversations", "examples": []}}
  }}
}}

Return ONLY JSON. No explanations.
"""

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a behavioral data extractor. Always return valid JSON."},
                {"role": "user", "content": context + prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"LLM inference failed: {e}")
        return {
            "error": str(e)
        }
