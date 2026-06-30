import json
from typing import Dict, Any
from services.llm import client, MODEL_NAME

async def generate_coaching_advice(persona_data: Dict[str, Any], target_person: str) -> Dict[str, Any]:
    """
    Asks the LLM to provide actionable advice on how to communicate with the persona.
    """
    
    # Extract minimal useful data to avoid massive prompts
    llm_inf = persona_data.get("llm_inferences", {})
    ts = persona_data.get("target_stats", {})
    constraints = persona_data.get("constraints", [])
    
    prompt = f"""You are an expert communication coach analyzing a behavioral profile for a person named {target_person}.
    
Based on their communication DNA, provide actionable advice on how someone should text them.

[Behavioral Profile]
- Style Drift: {llm_inf.get('style_drift_over_time', 'Unknown')}
- Emotion Handling: {json.dumps(llm_inf.get('emotional_response_patterns', []))}
- Humor Style: {json.dumps(llm_inf.get('humor_style', {}))}
- Conflict Style: {json.dumps(llm_inf.get('conflict_style', {}))}
- Hard Constraints (Things they hate): {json.dumps(constraints)}
- Average Words per message: {ts.get('avg_words_per_message', '?')}

Format your response exactly as valid JSON matching this schema:
{{
    "dos": [
        "Do this specific thing based on their profile..."
    ],
    "donts": [
        "Never do this specific thing based on their profile..."
    ],
    "conflict_resolution": "A paragraph explaining how to approach arguments or disagreements with them.",
    "overall_vibe": "A one-sentence summary of how to treat them."
}}
Ensure exactly 3 Do's and 3 Don'ts. Output ONLY JSON, with no markdown formatting.
"""

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        return json.loads(content)
    except Exception as e:
        print(f"Coaching Engine Error: {e}")
        return {
            "dos": ["Be yourself", "Listen actively", "Match their pacing"],
            "donts": ["Don't spam messages", "Don't ignore their boundaries", "Don't fake their style"],
            "conflict_resolution": "Give them space and approach logically.",
            "overall_vibe": "Respect their communication rhythm."
        }
