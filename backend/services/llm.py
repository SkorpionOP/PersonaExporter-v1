"""
LLM — Reduced to 20% role.
Only infers what machines cannot compute:
  - Emotional response patterns
  - Humor style
  - Conflict style
  - Comfort style

Round 3: humor_style, conflict_style, comfort_style now return structured objects
with description, confidence (0-100), and evidence string.
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
    """
    The ONLY LLM call in the entire pipeline.

    Sends hard measured facts as context.
    Asks LLM to infer ONLY the 4 things machines cannot compute.
    Each of the 3 single-sentence fields now includes confidence (0-100)
    and a brief evidence string so the prompt can display them transparently.
    Does NOT ask it to write a prompt. Does NOT ask it to summarize.
    """
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

REAL CONVERSATION SAMPLE (last 200 messages from {target_person}):
{conversation_text[:16000]}
"""

    prompt = f"""
You are a behavioral extractor. Your job is to observe ONLY.

Do NOT summarize. Do NOT describe personality in adjectives.
Do NOT write a system prompt. Return ONLY valid JSON.

Based on the facts and conversation sample above, infer ONLY these 4 things for "{target_person}".

For humor_style, conflict_style, and comfort_style — return an object with:
  - "description": one cold factual sentence (no adjectives like "warm" or "empathetic")
  - "confidence": integer 0-100 representing how certain you are based on evidence
  - "evidence": a brief phrase citing what you observed (e.g. "48 teasing exchanges, 0 dark humor")

{{
  "emotional_response_patterns": [
    {{"when": "user shares sad news", "response_steps": ["step 1", "step 2", "step 3"]}},
    {{"when": "user shares good news", "response_steps": ["step 1", "step 2"]}},
    {{"when": "user is angry", "response_steps": ["step 1", "step 2"]}}
  ],
  "humor_style": {{
    "description": "one cold factual sentence",
    "confidence": 84,
    "evidence": "48 teasing interactions detected, 0 dark humor"
  }},
  "conflict_style": {{
    "description": "one cold factual sentence",
    "confidence": 71,
    "evidence": "12 conflict-adjacent exchanges observed"
  }},
  "comfort_style": {{
    "description": "one cold factual sentence",
    "confidence": 90,
    "evidence": "23 comfort scenarios found"
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
        # Fallback matches the new schema so downstream code never breaks
        return {
            "emotional_response_patterns": [],
            "humor_style": {
                "description": "Could not infer.",
                "confidence": 0,
                "evidence": str(e),
            },
            "conflict_style": {
                "description": "Could not infer.",
                "confidence": 0,
                "evidence": str(e),
            },
            "comfort_style": {
                "description": "Could not infer.",
                "confidence": 0,
                "evidence": str(e),
            },
            "error": str(e)
        }
