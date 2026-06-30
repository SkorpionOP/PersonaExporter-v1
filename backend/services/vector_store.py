import faiss
import numpy as np
import json
import os
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from datetime import datetime

class FAISSStore:
    def __init__(self, dimension: int = 384): # 384 for all-MiniLM-L6-v2
        self.dimension = dimension
        # L2 distance index is standard, but inner product is better for cosine sim if normalized
        self.index = faiss.IndexFlatIP(dimension) 
        self.metadata_store: Dict[int, Dict[str, Any]] = {}
        self._current_id = 0
        
    def add_texts(self, embeddings: np.ndarray, metadatas: List[Dict[str, Any]]):
        """Adds normalized embeddings and their associated metadata to the store."""
        if len(embeddings) != len(metadatas):
            raise ValueError("Embeddings and metadatas length mismatch")
            
        if len(embeddings) == 0:
            return

        # Ensure embeddings are normalized for IndexFlatIP (Cosine Similarity)
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        
        for meta in metadatas:
            self.metadata_store[self._current_id] = meta
            self._current_id += 1

    def search_with_custom_ranking(
        self, 
        query_embedding: np.ndarray, 
        target_person: str,
        query_meta: Dict[str, Any], 
        k: int = 50,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top K candidates via FAISS, then reranks them using the custom formula:
        0.45 Semantic Similarity + 0.20 Same Scenario + 0.15 Same Topic + 0.10 Same Emotion + 0.10 Recency
        Returns the top N results.
        """
        if self._current_id == 0:
            return []
            
        faiss.normalize_L2(query_embedding)
        
        # We retrieve K candidates from FAISS (fast)
        actual_k = min(k, self._current_id)
        similarities, indices = self.index.search(query_embedding, actual_k)
        
        results = []
        # Rerank
        for i in range(actual_k):
            idx = indices[0][i]
            semantic_sim = similarities[0][i] # Already cosine sim because IP + normalized
            
            # Bound it between 0 and 1 just in case
            semantic_sim = float(max(0.0, min(1.0, semantic_sim)))
            
            meta = self.metadata_store[idx]
            
            # We only want to retrieve examples of how the target person replies
            if meta.get("speaker") != target_person:
                continue
                
            # Score Components
            scenario_score = 1.0 if meta.get("scenario") and meta.get("scenario") == query_meta.get("scenario") else 0.0
            topic_score = 1.0 if meta.get("topic") and meta.get("topic") == query_meta.get("topic") else 0.0
            emotion_score = 1.0 if meta.get("emotion") and meta.get("emotion") == query_meta.get("emotion") else 0.0
            
            # Recency score (simulated - if timestamps are close)
            recency_score = 0.0
            q_time = query_meta.get("timestamp")
            m_time = meta.get("timestamp")
            if q_time and m_time:
                # E.g. within 2 days gets 1.0, scales down
                diff_days = abs((q_time - m_time).days)
                if diff_days == 0: recency_score = 1.0
                elif diff_days < 7: recency_score = 0.5
                elif diff_days < 30: recency_score = 0.2
            
            # Custom Formula
            final_score = (0.45 * semantic_sim) + (0.20 * scenario_score) + (0.15 * topic_score) + (0.10 * emotion_score) + (0.10 * recency_score)
            
            results.append({
                "score": final_score,
                "semantic_sim": semantic_sim,
                "message": meta.get("content"),
                "scenario": meta.get("scenario"),
                "topic": meta.get("topic"),
                "emotion": meta.get("emotion"),
                "reply_to": meta.get("reply_to_content")
            })
            
        # Sort by final score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_n]

    def save(self, base_path: str):
        """Saves the FAISS index and metadata to disk."""
        os.makedirs(os.path.dirname(base_path), exist_ok=True)
        faiss.write_index(self.index, f"{base_path}.faiss")
        
        # Serialize datetime objects if present
        def default_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError("Type not serializable")
            
        with open(f"{base_path}_meta.json", "w") as f:
            json.dump(self.metadata_store, f, default=default_serializer)
            
    @classmethod
    def load(cls, base_path: str, dimension: int = 384) -> 'FAISSStore':
        """Loads a FAISS index and metadata from disk."""
        store = cls(dimension)
        store.index = faiss.read_index(f"{base_path}.faiss")
        with open(f"{base_path}_meta.json", "r") as f:
            meta_raw = json.load(f)
            # JSON keys are always strings, convert back to int
            store.metadata_store = {int(k): v for k, v in meta_raw.items()}
            store._current_id = max(store.metadata_store.keys()) + 1 if store.metadata_store else 0
        return store
