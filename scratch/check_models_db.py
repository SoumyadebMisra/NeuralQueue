import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import httpx
import os
from dotenv import load_dotenv

async def check_models():
    load_dotenv("backend/.env")
    db_url = os.getenv("DATABASE_URL")
    
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get the first user's Gemini key
        result = await session.execute(text("SELECT gemini_api_key FROM user_account LIMIT 1"))
        api_key = result.scalar()
        
    if not api_key:
        print("Error: No Gemini API Key found in database user_account table.")
        return

    print(f"Testing API Key from DB: {api_key[:5]}...{api_key[-5:]}")
    
    async with httpx.AsyncClient() as client:
        # Check v1, v1beta, and v1alpha
        for version in ["v1", "v1beta", "v1alpha"]:
            url = f"https://generativelanguage.googleapis.com/{version}/models?key={api_key}"
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    print(f"\n--- Available Models ({version}) ---")
                    for m in models:
                        # Only show gemini models to reduce noise
                        if "gemini" in m['name'].lower():
                            print(f" - {m['name']}")
                else:
                    print(f"\nError fetching {version}: {resp.status_code}")
            except Exception as e:
                print(f"Exception for {version}: {str(e)}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_models())
