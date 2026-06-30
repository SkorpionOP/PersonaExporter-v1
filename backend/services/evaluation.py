import asyncio
import random
import numpy as np
import emoji
from typing import List, Dict, Tuple
from models.domain import Message
from services.scenario_engine import _is_valid_reply
from services.llm import client, MODEL_NAME

try:
    from sentence_transformers import SentenceTransformer
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    eval_model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
except ImportError:
    eval_model = None

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

def _get_response_mode(text: str) -> str:
    if '?' in text: return "Question"
    if len(text.split()) < 5: return "Acknowledgement/Short"
    if len(text.split()) > 20: return "Explanation/Long"
    return "Statement/Normal"

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
    
    # 4. Semantic Similarity (Embeddings)
    semantic_sim = 0
    if eval_model:
        emb1 = eval_model.encode(actual)
        emb2 = eval_model.encode(generated)
        sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-9)
        semantic_sim = max(0, min(100, sim * 100))
        
    # 5. Emoji Scoring
    act_emojis = [c for c in actual if c in emoji.EMOJI_DATA]
    gen_emojis = [c for c in generated if c in emoji.EMOJI_DATA]
    
    emoji_presence = 100 if bool(act_emojis) == bool(gen_emojis) else 0
    
    count_diff = abs(len(act_emojis) - len(gen_emojis))
    max_count = max(len(act_emojis), len(gen_emojis), 1)
    emoji_count_sim = max(0, 100 - (count_diff / max_count * 100))
    
    act_emoji_set = set(act_emojis)
    gen_emoji_set = set(gen_emojis)
    e_intersect = act_emoji_set.intersection(gen_emoji_set)
    e_union = act_emoji_set.union(gen_emoji_set)
    emoji_choice_sim = (len(e_intersect) / len(e_union) * 100) if e_union else 100
    if not act_emojis and not gen_emojis:
        emoji_choice_sim = 100 # Both correctly used none
        
    emoji_overall = (emoji_presence + emoji_count_sim + emoji_choice_sim) / 3

    # 6. Response Mode Accuracy
    act_mode = _get_response_mode(actual)
    gen_mode = _get_response_mode(generated)
    mode_sim = 100 if act_mode == gen_mode else 0

    return {
        "length_sim": len_sim,
        "vocab_sim": vocab_sim,
        "format_sim": format_sim,
        "semantic_sim": semantic_sim,
        "emoji_sim": emoji_overall,
        "mode_sim": mode_sim,
        "overall": (len_sim + vocab_sim + format_sim + semantic_sim + emoji_overall + mode_sim) / 6
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
    total_semantic_sim = 0
    total_emoji_sim = 0
    total_mode_sim = 0
    total_overall = 0
    
    results = []
    for pair, generated in zip(holdout_pairs, generated_replies):
        sim = _compute_similarity(pair["actual_reply"], generated)
        total_len_sim += sim["length_sim"]
        total_vocab_sim += sim["vocab_sim"]
        total_format_sim += sim["format_sim"]
        total_semantic_sim += sim["semantic_sim"]
        total_emoji_sim += sim["emoji_sim"]
        total_mode_sim += sim["mode_sim"]
        total_overall += sim["overall"]
        
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
        "semantic_similarity_pct": round(total_semantic_sim / n, 1),
        "emoji_similarity_pct": round(total_emoji_sim / n, 1),
        "response_mode_accuracy_pct": round(total_mode_sim / n, 1),
        "overall_score_pct": round(total_overall / n, 1)
    }
    
    return {
        "final_scores": final_scores,
        "evaluations": results
    }
