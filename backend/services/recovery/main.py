import asyncio
import os
from uuid import UUID
from backend.models.enums import TaskStatus
from backend.repository.task_repository import TaskRepository
from backend.service.redis_service import redis_service
from backend.utils.get_db import async_session_maker

RECOVERY_INTERVAL = 30
STUCK_THRESHOLD = 300  # tasks PROCESSING for >5 min are considered stuck

async def recovery_loop():
    print(f"[recovery] standalone service started (sweep every {RECOVERY_INTERVAL}s, stuck threshold {STUCK_THRESHOLD}s)")

    while True:
        try:
            async with async_session_maker() as db:
                repo = TaskRepository(db)
                stuck_tasks = await repo.get_stuck_tasks(STUCK_THRESHOLD)

                for task in stuck_tasks:
                    old_worker = task.locked_by or "unknown"
                    print(f"[recovery] task {str(task.id)[:8]} stuck in PROCESSING "
                          f"(worker: {old_worker}), resetting to QUEUED")

                    task.status = TaskStatus.QUEUED
                    task.locked_by = None
                    task.started_at = None
                    await db.commit()

                    # Re-enqueue for the scheduler to re-score
                    await redis_service.push_to_stream(f"tasks:{task.priority.value}", {
                        "task_id": str(task.id),
                        "task_type": str(task.task_type.value),
                        "priority": str(task.priority.value),
                        "gpu_budget": str(task.gpu_budget),
                        "model": task.model
                    })

                    await redis_service.publish_event("task_events", {
                        "type": "task_retrying",
                        "task_id": str(task.id),
                        "retry": task.retries,
                    })

                if stuck_tasks:
                    print(f"[recovery] reset {len(stuck_tasks)} stuck task(s)")

            await asyncio.sleep(RECOVERY_INTERVAL)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[recovery] error: {e}")
            await asyncio.sleep(RECOVERY_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(recovery_loop())
    except KeyboardInterrupt:
        print("\n[recovery] stopped.")
