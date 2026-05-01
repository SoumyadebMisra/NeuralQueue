import asyncio
import time
from backend.service.redis_service import redis_service

PRIORITIES = ["critical", "high", "medium", "low"]
PRIORITY_WEIGHTS = {"critical": 100, "high": 60, "medium": 30, "low": 10}
SCHEDULER_GROUP = "scheduler_group"
WORKER_GROUP = "neuralqueue_workers"


def calculate_score(task_data: dict, message_id: str) -> float:
    priority = task_data.get("priority", "low")
    gpu_budget = int(task_data.get("gpu_budget", 1))
    priority_weight = PRIORITY_WEIGHTS.get(priority, 10)

    timestamp_ms = int(message_id.split("-")[0])
    age_seconds = (time.time() * 1000 - timestamp_ms) / 1000
    age_bonus = min(age_seconds * 0.5, 40)
    size_penalty = gpu_budget * 3

    return priority_weight + age_bonus - size_penalty


async def scheduler_loop():
    print("[scheduler] starting standalone service...")
    for p in PRIORITIES:
        await redis_service.create_consumer_group(f"tasks:{p}", SCHEDULER_GROUP)
    await redis_service.create_consumer_group("tasks:ready", WORKER_GROUP)

    while True:
        try:
            candidates = []
            for priority in PRIORITIES:
                stream = f"tasks:{priority}"
                await redis_service.create_consumer_group(stream, SCHEDULER_GROUP) # Ensure group exists
                messages = await redis_service.read_stream(stream, count=50)
                for msg_id, msg_data in messages:
                    candidates.append({
                        "stream": stream,
                        "message_id": msg_id,
                        "data": msg_data,
                        "score": calculate_score(msg_data, msg_id),
                    })

            if candidates:
                candidates.sort(key=lambda c: c["score"], reverse=True)
                for candidate in candidates[:10]:
                    ready_stream = "tasks:ready"
                    
                    await redis_service.push_to_stream(ready_stream, candidate["data"])
                    await redis_service.delete_message(candidate["stream"], candidate["message_id"])
                    task_id = candidate["data"].get("task_id", "?")
                    print(f"[scheduler] dispatched {task_id[:8]} to {ready_stream}")

            await asyncio.sleep(2)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[scheduler] error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(scheduler_loop())
    except KeyboardInterrupt:
        print("\n[scheduler] stopped.")
