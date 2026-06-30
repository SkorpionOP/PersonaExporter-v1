import numpy as np
from typing import List, Dict, Any
from models.domain import Message
from services.vector_store import FAISSStore
from services.scenario_engine import SCENARIO_KEYWORDS

# Simple heuristics for extracting metadata per message to avoid massive LLM calls per message
def _infer_emotion(text: str) -> str:
    text = text.lower()
    if any(w in text for w in ["sad", "cry", "hurt", "depressed", "upset"]): return "Negative"
    if any(w in text for w in ["happy", "yay", "excited", "love", "great"]): return "Positive"
    if any(w in text for w in ["angry", "mad", "hate", "wtf"]): return "Angry"
    return "Neutral"

def _infer_scenario(text: str) -> str:
    text = text.lower()
    for scenario, keywords in SCENARIO_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return scenario
    return "General"

def build_persona_memory_store(messages: List[Message], eval_model) -> FAISSStore:
    """
    Builds the FAISS vector store with embedded messages and rich metadata.
    """
    store = FAISSStore()
    
    if not eval_model:
        print("Warning: SentenceTransformer not loaded. RAP Engine disabled.")
        return store

    batch_size = 64
    current_batch_texts = []
    current_batch_meta = []
    
    for i, msg in enumerate(messages):
        # We want to store what people say and link it to what they were replying to
        reply_to_content = ""
        if i > 0:
            reply_to_content = messages[i-1].content
            
        meta = {
            "speaker": msg.sender,
            "timestamp": msg.timestamp,
            "content": msg.content,
            "reply_to_content": reply_to_content,
            "scenario": _infer_scenario(msg.content),
            "emotion": _infer_emotion(msg.content),
            "topic": "General" # Ideally pulled from a more robust topic model
        }
        
        current_batch_texts.append(msg.content)
        current_batch_meta.append(meta)
        
        if len(current_batch_texts) >= batch_size:
            embeddings = eval_model.encode(current_batch_texts)
            store.add_texts(embeddings, current_batch_meta)
            current_batch_texts = []
            current_batch_meta = []
            
    # Remainder
    if current_batch_texts:
        embeddings = eval_model.encode(current_batch_texts)
        store.add_texts(embeddings, current_batch_meta)
        
    return store
