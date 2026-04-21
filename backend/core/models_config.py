from typing import List, Dict, Any

SUPPORTED_MODELS = [
    {
        "id": "gpt-4o-mini",
        "name": "GPT-4o Mini",
        "provider": "OpenAI",
        "weight": 0.2,
        "description": "Fast and efficient for simple tasks"
    },
    {
        "id": "gemini/gemini-3.1-flash-lite-preview",
        "name": "Gemini 3.1 Flash Lite (Preview)",
        "provider": "Google",
        "weight": 0.2,
        "description": "Latest ultra-fast experimental model"
    },
    {
        "id": "gemini/gemini-2.5-flash-preview-09-2025",
        "name": "Gemini 2.5 Flash (Preview)",
        "provider": "Google",
        "weight": 0.3,
        "description": "Next-gen balanced performance"
    },
    {
        "id": "gemini/gemini-2.0-flash",
        "name": "Gemini 2.0 Flash",
        "provider": "Google",
        "weight": 0.3,
        "description": "High performance stable model"
    },
    {
        "id": "gemini/gemini-1.5-pro-latest",
        "name": "Gemini 1.5 Pro (Latest)",
        "provider": "Google",
        "weight": 0.8,
        "description": "Deep reasoning with massive context"
    },
    {
        "id": "gemini/gemini-pro",
        "name": "Gemini Pro",
        "provider": "Google",
        "weight": 0.5,
        "description": "Balanced stable model"
    },
    {
        "id": "gemini/gemini-flash-lite-latest",
        "name": "Gemini Flash Lite (Latest)",
        "provider": "Google",
        "weight": 0.1,
        "description": "Optimized for extreme latency"
    },
    {
        "id": "gemini/gemini-flash-latest",
        "name": "Gemini Flash (Latest)",
        "provider": "Google",
        "weight": 0.2,
        "description": "Fast stable model"
    }
]

def get_model_ids() -> List[str]:
    return [m["id"] for m in SUPPORTED_MODELS]

def get_model_info(model_id: str) -> Dict[str, Any]:
    for m in SUPPORTED_MODELS:
        if m["id"] == model_id:
            return m
    return {}
