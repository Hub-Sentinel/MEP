import json
import os
from typing import Dict, Any

class ReputationManager:
    """
    L2 Reputation Tracker: Stored locally on the user's Clawdbot.
    Tracks which Provider Nodes are good, and which are 'slacking' (磨洋工).
    """
    def __init__(self, storage_path="reputation.json"):
        self.storage_path = storage_path
        self.scores: Dict[str, Dict[str, Any]] = self._load()
        
    def _load(self) -> Dict[str, Dict[str, Any]]:
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        return {}
        
    def _save(self):
        with open(self.storage_path, 'w') as f:
            json.dump(self.scores, f, indent=2)

    def get_score(self, provider_id: str) -> float:
        """Returns score between 0.0 (Worst) and 1.0 (Best). Default is 0.5."""
        return self.scores.get(provider_id, {}).get("score", 0.5)

    def evaluate_result(self, provider_id: str, result_payload: str) -> float:
        """
        Mock evaluation logic. 
        In production, this could be:
        1. Simple length/keyword check.
        2. A lightweight local LLM verification (e.g., Llama.cpp).
        """
        quality = 0.5
        
        # Extremely basic heuristics for the prototype
        if len(result_payload.strip()) == 0:
            quality = 0.0  # Empty response = slacking!
        elif "Error" in result_payload or "Failed" in result_payload:
            quality = 0.2  # Bad response
        elif len(result_payload) > 50:
            quality = 0.9  # Looks like a solid response!
            
        return self.update_score(provider_id, quality)

    def update_score(self, provider_id: str, quality_score: float) -> float:
        """Moving average reputation."""
        if provider_id not in self.scores:
            self.scores[provider_id] = {"score": 0.5, "tasks": 0}
            
        current = self.scores[provider_id]
        total_score = current["score"] * current["tasks"]
        
        current["tasks"] += 1
        current["score"] = (total_score + quality_score) / current["tasks"]
        
        self._save()
        print(f"[Reputation] Node {provider_id} updated. New Score: {current['score']:.2f} (Total Tasks: {current['tasks']})")
        return current["score"]
