import asyncio
import argparse
import random
import time
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from utils.get_db import async_session_maker
from repository.task_repository import TaskRepository
from models.enums import TaskStatus
from service.redis_service import redis_service

PRIORITIES = ["critical", "high", "medium", "low"]
GROUP_NAME = "neuralqueue_workers"

async def setup_redis_groups():
    for priority in PRIORITIES:
        stream_name = f"tasks:{priority}"
        await redis_service.create_consumer_group(stream_name, GROUP_NAME)

async def process_task(task_id: str, db: AsyncSession):
    repo = TaskRepository(db)
    
    task_uuid = UUID(task_id)
    task = await repo.get(task_uuid)
    if not task:
        print(f"[-] Task {task_id} not found in DB! Skipping.")
        return

    print(f"\n[>] Starting Task {task_id} (Priority: {task.priority.value}, Type: {task.task_type.value})")
    
    task.status = TaskStatus.PROCESSING
    task.started_at = datetime.utcnow()
    await db.commit()
    
    start_time = time.time()
    sleep_time = task.gpu_budget * random.uniform(0.8, 1.2)
    print(f"    ... Simulating GPU workload for {sleep_time:.2f} seconds ...")
    await asyncio.sleep(sleep_time)
    
    latency = (time.time() - start_time) * 1000
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.utcnow()
    task.latency_ms = latency
    await db.commit()
    
    print(f"[✓] Task {task_id} completed in {latency:.0f}ms")


async def worker_loop(worker_name: str):
    print(f"Started NeuralQueue Worker: {worker_name}")
    await setup_redis_groups()
    
    streams = {f"tasks:{p}": ">" for p in PRIORITIES}
    
    print(f"Listening to streams: {list(streams.keys())} ...\n")
    
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
                            print(f"[!] Error processing task {task_id}: {e}")
                            
        except asyncio.CancelledError:
            print(f"Stopping Worker {worker_name} safely...")
            break
        except Exception as e:
            print(f"Unexpected Error in worker loop: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NeuralQueue Backend Worker CLI")
    parser.add_argument("--name", type=str, default=f"worker-{random.randint(1000, 9999)}", help="Unique name for this worker node.")
    args = parser.parse_args()
    
    try:
        asyncio.run(worker_loop(args.name))
    except KeyboardInterrupt:
        print("\nShutdown requested by user. Exiting.")
