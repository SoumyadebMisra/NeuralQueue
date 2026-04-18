import redis.asyncio as redis
from core.config import settings

class RedisService:
    def __init__(self):
        self.redis_client = None

    async def connect(self):
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

    async def push_to_stream(self, stream_name: str, data: dict):
        client = await self.connect()
        return await client.xadd(stream_name, data)

    async def create_consumer_group(self, stream_name: str, group_name: str):
        client = await self.connect()
        try:
            await client.xgroup_create(stream_name, group_name, id="0", mkstream=True)
            print(f"Created consumer group {group_name} for stream {stream_name}")
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP Consumer Group name already exists" not in str(e):
                raise e

    async def read_from_group(self, group_name: str, consumer_name: str, streams: dict, count: int = 1, block: int = 2000):
        client = await self.connect()
        return await client.xreadgroup(
            groupname=group_name,
            consumername=consumer_name,
            streams=streams,
            count=count,
            block=block
        )

    async def acknowledge_message(self, stream_name: str, group_name: str, message_id: str):
        client = await self.connect()
        await client.xack(stream_name, group_name, message_id)


redis_service = RedisService()
