import asyncio
import asyncpg

async def test_pw(pw):
    try:
        conn = await asyncpg.connect(user='soumya', password=pw, database='neuralqueue', host='localhost', port=5433)
        print(f"Success with password: {pw}")
        await conn.close()
        return True
    except Exception as e:
        print(f"Failed with pw {pw}: {e}")
        return False

async def main():
    for pw in ['Sm@pg0802', 'Sm%40pg0802', 'Sm%%40pg0802', 'postgres']:
        if await test_pw(pw):
            break

asyncio.run(main())
