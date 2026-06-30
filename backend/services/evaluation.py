import asyncio
import random
from typing import List, Dict, Tuple
from models.domain import Message
from services.scenario_engine import _is_valid_reply
from services.llm import client, MODEL_NAME

# Limit to avoid crashing local Ollama instances
MAX_EVAL_PAIRS = 25
SEM_LIMIT = 3

def extract_holdout_set(messages: List[Message], target_person: str, count: int = MAX_EVAL_PAIRS) -> Tuple[List[Message], List[Dict]]:
    """
    Extracts a random set of `count` pairs of (user message, target reply).
    Removes these target replies from the original message list to prevent data leakage.
    """
    holdout_pairs = []
    valid_pairs = []
    
    for i, msg in enumerate(messages):
        if msg.sender != target_person:
            reply = _is_valid_reply(messages, i, target_person)
            if reply:
                valid_pairs.append((msg, reply))
                
    num_to_sample = min(count, len(valid_pairs))
    sampled_pairs = random.sample(valid_pairs, num_to_sample)
    
    replies_to_remove = set()
    for user_msg, reply_msg in sampled_pairs:
        holdout_pairs.append({
            "user_msg": user_msg.content,
            "actual_reply": reply_msg.content,
            "reply_timestamp": reply_msg.timestamp
        })
        replies_to_remove.add((reply_msg.timestamp, reply_msg.sender, reply_msg.content))
        
    new_messages = []
    for msg in messages:
        ident = (msg.timestamp, msg.sender, msg.content)
        if ident not in replies_to_remove:
            new_messages.append(msg)
            
    return new_messages, holdout_pairs

async def _simulate_reply(system_prompt: str, user_msg: str, semaphore: asyncio.Semaphore) -> str:
    async with semaphore:
        try:
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ],
                max_tokens=150,
                temperature=0.8
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Eval LLM simulation failed: {e}")
            return ""

def _compute_similarity(actual: str, generated: str) -> dict:
    actual_lower = actual.lower()
    generated_lower = generated.lower()
    
    # 1. Length similarity (0-100)
    len_diff = abs(len(actual) - len(generated))
    max_len = max(len(actual), len(generated), 1)
    len_sim = max(0, 100 - (len_diff / max_len * 100))
    
    # 2. Vocabulary overlap (Jaccard similarity of words)
    actual_words = set(actual_lower.split())
    gen_words = set(generated_lower.split())
    intersection = actual_words.intersection(gen_words)
    union = actual_words.union(gen_words)
    vocab_sim = (len(intersection) / len(union) * 100) if union else 100
    
    # 3. Formatting/Tone (Simplified - do they both use punctuation? lowercase?)
    act_lower_only = actual == actual_lower
    gen_lower_only = generated == generated_lower
    format_sim = 100 if act_lower_only == gen_lower_only else 50
    
    return {
        "length_sim": len_sim,
        "vocab_sim": vocab_sim,
        "format_sim": format_sim,
        "overall": (len_sim + vocab_sim + format_sim) / 3
    }

async def evaluate_persona(system_prompt: str, holdout_pairs: List[Dict]) -> dict:
    """
    Runs the LLM against the holdout pairs and scores the results.
    """
    if not holdout_pairs:
        return {"error": "No holdout pairs available for evaluation."}

    semaphore = asyncio.Semaphore(SEM_LIMIT)
    tasks = []
    
    for pair in holdout_pairs:
        tasks.append(_simulate_reply(system_prompt, pair["user_msg"], semaphore))
        
    generated_replies = await asyncio.gather(*tasks)
    
    total_len_sim = 0
    total_vocab_sim = 0
    total_format_sim = 0
    
    results = []
    for pair, generated in zip(holdout_pairs, generated_replies):
        sim = _compute_similarity(pair["actual_reply"], generated)
        total_len_sim += sim["length_sim"]
        total_vocab_sim += sim["vocab_sim"]
        total_format_sim += sim["format_sim"]
        
        results.append({
            "user_msg": pair["user_msg"],
            "actual_reply": pair["actual_reply"],
            "generated_reply": generated,
            "scores": sim
        })
        
    n = len(holdout_pairs)
    final_scores = {
        "length_similarity_pct": round(total_len_sim / n, 1),
        "vocabulary_similarity_pct": round(total_vocab_sim / n, 1),
        "formatting_similarity_pct": round(total_format_sim / n, 1),
        "overall_score_pct": round((total_len_sim + total_vocab_sim + total_format_sim) / (3 * n), 1)
    }
    
    return {
        "final_scores": final_scores,
        "evaluations": results
    }
