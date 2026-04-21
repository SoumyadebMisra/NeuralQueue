import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from backend.service.redis_service import redis_service
from backend.core.config import settings

async def verify_upstash():
    print(f"Connecting to Upstash at {settings.REDIS_HOST}...")
    try:
        client = await redis_service.connect()
        pong = await client.ping()
        print(f"Connection Successful! Ping: {pong}")
        
        # Test stream
        stream_id = await redis_service.push_to_stream("test_connection", {"msg": "hello from NeuralQueue"})
        print(f"Stream Push Successful! ID: {stream_id}")
        
        # Clean up
        await redis_service.delete_message("test_connection", stream_id)
        print("Cleanup Successful!")
        
        await redis_service.disconnect()
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_upstash())
