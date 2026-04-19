import asyncio
import httpx
import os
from dotenv import load_dotenv

async def list_models():
    # Load from the backend .env
    load_dotenv("backend/.env")
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("Error: GEMINI_API_KEY not found in backend/.env")
        return

    print(f"Testing API Key: {api_key[:5]}...{api_key[-5:]}")
    
    async with httpx.AsyncClient() as client:
        # Try both v1 and v1beta to see what's available
        for version in ["v1", "v1beta"]:
            url = f"https://generativelanguage.googleapis.com/{version}/models?key={api_key}"
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    print(f"\n--- Available Models ({version}) ---")
                    for m in models:
                        print(f" - {m['name']}")
                else:
                    print(f"\nError fetching {version}: {resp.status_code} - {resp.text}")
            except Exception as e:
                print(f"Exception for {version}: {str(e)}")

if __name__ == "__main__":
    asyncio.run(list_models())
