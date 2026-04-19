from typing import Dict
import litellm

# Model intensity weights (1.0 = baseline, e.g. gpt-4o)
MODEL_WEIGHTS: Dict[str, float] = {
    "gpt-4o-mini": 0.2,
    "gpt-4o": 1.0,
    "gpt-4": 1.5,
    "claude-3-haiku": 0.3,
    "claude-3-5-sonnet": 1.0,
    "gemini": 0.4,
    "llama3": 1.2,
    "mistral": 0.8,
}

def predict_gpu_budget(model: str, prompt: str) -> int:
    """
    Predicts the GPU resource requirement (Scale) for a task.
    Returns an integer from 1 to 16.
    """
    # 1. Base weight based on model architecture
    base_weight = 0.5 # Default
    model_lower = model.lower()
    
    for key, weight in MODEL_WEIGHTS.items():
        if key in model_lower:
            base_weight = weight
            break
            
    # 2. Complexity based on prompt length (token counting simulation)
    # litellm.token_counter provides a rough estimate
    try:
        token_count = litellm.token_counter(model="gpt-3.5-turbo", text=prompt)
    except:
        token_count = len(prompt.split()) * 1.3 # Fallback
        
    # Formula: (Base Weight * 4) + (Tokens / 400)
    # Small tasks (e.g. gpt-4o-mini, short prompt) -> ~1-2
    # Medium tasks (e.g. gpt-4o, med prompt) -> ~4-6
    # Large tasks (e.g. llama3, long prompt) -> ~8-16
    
    predicted_scale = (base_weight * 5) + (token_count / 300)
    
    # Constrain between 1 and 16
    final_budget = max(1, min(16, int(predicted_scale)))
    
    return final_budget
