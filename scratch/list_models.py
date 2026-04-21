import os
import asyncio
from backend.core.config import settings

# Attempt to list models using LiteLLM
import litellm

async def list_gemini_models():
    api_key = os.getenv("GEMINI_API_KEY") or "AIza..." # Use a dummy or real one
    # In this context we want to see what LiteLLM thinks
    print("Checking LiteLLM Gemini models...")
    try:
        # We don't have a direct list_models for gemini in litellm that works without keys
        # but we can check the litellm model list
        gemini_models = [m for m in litellm.model_list if "gemini" in m]
        print(f"LiteLLM known gemini models: {gemini_models[:10]}...")
        
        # Real check
        print("\nAttempting to list models from API...")
        import httpx
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={settings.GEMINI_API_KEY}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                for m in models:
                    print(f"- {m['name']} (supports: {m.get('supportedGenerationMethods')})")
            else:
                print(f"Failed to list models: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(list_gemini_models())
