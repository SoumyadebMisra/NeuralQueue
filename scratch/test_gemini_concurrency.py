import asyncio
import httpx
import litellm
import time
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")

async def call_gemini(name: str, api_key: str):
    print(f"[{name}] Starting call to Gemini via raw HTTPX...")
    start = time.time()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:streamGenerateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": "Write a 500 word story about a brave penguin."}]}],
        "generationConfig": {"temperature": 0.7}
    }
    
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, json=payload, timeout=60.0) as resp:
                if resp.status_code != 200:
                    print(f"[{name}] Error: {resp.status_code}")
                    return
                
                chunks = 0
                async for chunk in resp.aiter_text():
                    chunks += 1
                    if chunks % 10 == 0:
                        print(f"[{name}] Received chunk {chunks}")
        
        end = time.time()
        print(f"[{name}] Finished Gemini in {end - start:.2f}s")
    except Exception as e:
        print(f"[{name}] Error: {e}")

async def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found in .env")
        return

    print("Testing concurrent calls to Gemini...")
    await asyncio.gather(
        call_gemini("Gemini-1", api_key),
        call_gemini("Gemini-2", api_key)
    )

if __name__ == "__main__":
    asyncio.run(main())
