import asyncio
from backend.service.redis_service import redis_service

async def worker():
    await redis_service.connect()
    
    priorities = ["high", "medium", "low"]
    streams = {f"tasks:{p}": ">" for p in priorities}
    group_name = "worker_group"

    for stream in streams:
        await redis_service.create_consumer_group(stream, group_name)

    print(f"Worker live. Listening on: {list(streams.keys())}")

    while True:
        results = await redis_service.read_from_group(
            group_name=group_name,
            consumer_name="worker_1",
            streams=streams,
            count=1,
            block=2000
        )

        if results:
            for stream_name, messages in results:
                for msg_id, data in messages:
                    print(f"[{stream_name}] Processing Task ID: {data['task_id']}")
                    await redis_service.acknowledge_message(stream_name, group_name, msg_id)

if __name__ == "__main__":
    asyncio.run(worker())