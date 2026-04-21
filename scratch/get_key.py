import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

async def main():
    db_url = "postgresql+asyncpg://soumya:Sm%40pg0802@localhost:5433/neuralqueue"
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT gemini_api_key FROM user_account LIMIT 1"))
        row = result.fetchone()
        if row and row[0]:
            print(f"KEY_FOUND:{row[0]}")
        else:
            print("KEY_NOT_FOUND")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
