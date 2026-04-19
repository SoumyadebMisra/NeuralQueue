import redis.asyncio as redis_async
import redis.exceptions as redis_exceptions
import json

from backend.core.config import settings


class RedisService:
    def __init__(self):
        self.redis_client = None
        self.pubsub = None

    async def connect(self):
        if not self.redis_client:
            self.redis_client = await redis_async.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client

    async def disconnect(self):
        if self.pubsub:
            await self.pubsub.close()
            self.pubsub = None
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
        except redis_exceptions.ResponseError as e:
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

    async def get_stream_length(self, stream_name: str) -> int:
        client = await self.connect()
        try:
            return await client.xlen(stream_name)
        except Exception:
            return 0

    async def read_stream(self, stream_name: str, count: int = 50):
        client = await self.connect()
        return await client.xrange(stream_name, count=count)

    async def delete_message(self, stream_name: str, message_id: str):
        client = await self.connect()
        await client.xdel(stream_name, message_id)

    async def get_pending_messages(self, stream_name: str, group_name: str, min_idle_ms: int = 30000, count: int = 10):
        client = await self.connect()
        try:
            result = await client.xautoclaim(
                stream_name, group_name, "recovery-worker",
                min_idle_time=min_idle_ms, start_id="0-0", count=count
            )
            return result
        except Exception:
            return None

    async def push_to_dlq(self, task_data: dict):
        client = await self.connect()
        await client.xadd("tasks:failed", task_data)

    async def publish_event(self, channel: str, event: dict):
        client = await self.connect()
        await client.publish(channel, json.dumps(event))

    async def subscribe(self, channel: str):
        client = await self.connect()
        self.pubsub = client.pubsub()
        await self.pubsub.subscribe(channel)
        return self.pubsub


redis_service = RedisService()
