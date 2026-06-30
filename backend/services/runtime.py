import json
import os
import numpy as np
from typing import Dict, Any, List, Tuple
from services.vector_store import FAISSStore
from services.evaluation import eval_model
from services.rap_engine import _infer_emotion, _infer_scenario
from services.llm import client, MODEL_NAME
from datetime import datetime

class PersonaRuntime:
    def __init__(self, persona_id: int, target_person: str, system_prompt_base: str):
        self.persona_id = persona_id
        self.target_person = target_person
        self.system_prompt_base = system_prompt_base
        
        # Load FAISS index
        faiss_path = f"uploads/{persona_id}_memory"
        if os.path.exists(f"{faiss_path}.faiss"):
            self.store = FAISSStore.load(faiss_path)
        else:
            print(f"Warning: No FAISS store found for persona {persona_id}")
            self.store = None

    def _detect_intent(self, user_msg: str) -> Dict[str, Any]:
        """Simple intent detection. Can be upgraded to LLM-based."""
        return {
            "scenario": _infer_scenario(user_msg),
            "emotion": _infer_emotion(user_msg),
            "topic": "General", # Placeholder
            "timestamp": datetime.now()
        }

    def _assemble_prompt(self, user_msg: str, retrieved_context: List[Dict[str, Any]]) -> str:
        """Assembles the dynamic prompt using static persona base + retrieved context."""
        context_str = "No retrieved memory."
        if retrieved_context:
            blocks = []
            for i, ctx in enumerate(retrieved_context):
                u_msg = ctx.get("reply_to", "Unknown context")
                p_msg = ctx.get("message", "Unknown reply")
                blocks.append(f"Context {i+1}:\nUser: {u_msg}\n{self.target_person}: {p_msg}")
            context_str = "\n\n".join(blocks)
            
        prompt = f"""{self.system_prompt_base}

━━━━━━━━━━━━━━
LAYER 5: Dynamic Retrieved Memory
━━━━━━━━━━━━━━
The following are real past interactions that are semantically related to the current conversation. 
Use them strictly as stylistic and contextual inspiration for how to reply right now.

{context_str}
"""
        return prompt

    async def generate_reply(self, chat_history: List[Dict[str, str]], user_msg: str) -> Dict[str, Any]:
        """
        The main RAP pipeline:
        1. Detect intent
        2. Embed & Retrieve
        3. Assemble prompt
        4. LLM Generation
        """
        query_meta = self._detect_intent(user_msg)
        
        retrieved = []
        if self.store and eval_model:
            emb = eval_model.encode([user_msg])[0]
            retrieved = self.store.search_with_custom_ranking(
                query_embedding=np.array([emb]),
                target_person=self.target_person,
                query_meta=query_meta,
                top_n=3
            )
            
        dynamic_prompt = self._assemble_prompt(user_msg, retrieved)
        
        # Build LLM messages
        messages = [{"role": "system", "content": dynamic_prompt}]
        for msg in chat_history[-5:]: # Keep last 5 messages for context
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_msg})
        
        try:
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=150,
                temperature=0.8
            )
            reply_text = response.choices[0].message.content.strip()
        except Exception as e:
            reply_text = f"Error generating reply: {e}"
            
        return {
            "reply": reply_text,
            "reasoning": {
                "detected_intent": query_meta,
                "retrieved_memories": retrieved,
                "similarity_scores": [r["score"] for r in retrieved] if retrieved else []
            }
        }
