import asyncio
import argparse
import random
import time
from uuid import UUID
from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.utils.get_db import async_session_maker
from backend.repository.task_repository import TaskRepository
from backend.models.enums import TaskStatus
from backend.models.user import User  # noqa: F401
from backend.service.redis_service import redis_service

GROUP_NAME = "neuralqueue_workers"
MAX_RETRIES = 3


async def publish_task_event(event_type: str, task_id: str, extra: dict = None):
    event = {"type": event_type, "task_id": task_id}
    if extra:
        event.update(extra)
    await redis_service.publish_event("task_events", event)


async def process_task(task_id: str, db: AsyncSession):
    repo = TaskRepository(db)

    task_uuid = UUID(task_id)
    task = await repo.get(task_uuid)
    if not task:
        print(f"[-] Task {task_id} not found in DB. Skipping.")
        return

    print(f"\n[>] Processing {task_id[:8]}... (priority: {task.priority.value}, gpu: {task.gpu_budget})")

    task.status = TaskStatus.PROCESSING
    task.started_at = datetime.now(UTC)
    await db.commit()

    await publish_task_event("task_processing", task_id)

    start_time = time.time()
    sleep_time = task.gpu_budget * random.uniform(0.8, 1.2)
    await asyncio.sleep(sleep_time)

    latency = (time.time() - start_time) * 1000
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.now(UTC)
    task.latency_ms = latency
    await db.commit()

    await publish_task_event("task_completed", task_id, {
        "latency_ms": round(latency, 2),
    })

    print(f"[+] Completed {task_id[:8]}... in {latency:.0f}ms")


async def handle_failure(task_id: str, db: AsyncSession, message_data: dict):
    repo = TaskRepository(db)
    task = await repo.get(UUID(task_id))
    if not task:
        return

    task.retries += 1
    task.status = TaskStatus.FAILED
    await db.commit()

    if task.retries >= MAX_RETRIES:
        await redis_service.push_to_dlq({
            "task_id": task_id,
            "retries": str(task.retries),
            "failed_at": datetime.now(UTC).isoformat(),
        })
        await publish_task_event("task_dead_lettered", task_id, {"retries": task.retries})
        print(f"[X] Task {task_id[:8]}... moved to DLQ after {task.retries} retries")
    else:
        await redis_service.push_to_stream(f"tasks:{task.priority.value}", message_data)
        await publish_task_event("task_retrying", task_id, {"retry": task.retries})
        print(f"[!] Retrying {task_id[:8]}... (attempt {task.retries}/{MAX_RETRIES})")


async def worker_loop(worker_name: str):
    print(f"Worker [{worker_name}] starting...")

    await redis_service.create_consumer_group("tasks:ready", GROUP_NAME)

    streams = {"tasks:ready": ">"}
    print(f"Worker [{worker_name}] listening on tasks:ready\n")

    while True:
        try:
            messages = await redis_service.read_from_group(
                group_name=GROUP_NAME,
                consumer_name=worker_name,
                streams=streams,
                count=1,
                block=2000
            )

            if not messages:
                continue

            for stream_name, stream_messages in messages:
                for message_id, message_data in stream_messages:
                    task_id = message_data.get("task_id")

                    async with async_session_maker() as db:
                        try:
                            await process_task(task_id, db)
                            await redis_service.acknowledge_message(stream_name, GROUP_NAME, message_id)
                        except Exception as e:
                            print(f"[!] Error on task {task_id}: {e}")
                            await handle_failure(task_id, db, message_data)
                            await redis_service.acknowledge_message(stream_name, GROUP_NAME, message_id)

        except asyncio.CancelledError:
            print(f"Worker [{worker_name}] shutting down.")
            break
        except Exception as e:
            print(f"Worker loop error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NeuralQueue Worker")
    parser.add_argument("--name", type=str, default=f"worker-{random.randint(1000, 9999)}")
    args = parser.parse_args()

    try:
        asyncio.run(worker_loop(args.name))
    except KeyboardInterrupt:
        print("\nWorker stopped.")
