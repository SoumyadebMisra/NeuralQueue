import asyncio
import time

from backend.service.redis_service import redis_service

PRIORITY_WEIGHTS = {
    "critical": 100,
    "high": 60,
    "medium": 30,
    "low": 10,
}

PRIORITIES = ["critical", "high", "medium", "low"]
GROUP_NAME = "scheduler_group"
SCHEDULER_INTERVAL = 2


def calculate_score(task_data: dict, message_id: str) -> float:
    priority = task_data.get("priority", "low")
    gpu_budget = int(task_data.get("gpu_budget", 1))

    priority_weight = PRIORITY_WEIGHTS.get(priority, 10)

    timestamp_ms = int(message_id.split("-")[0])
    age_seconds = (time.time() * 1000 - timestamp_ms) / 1000
    age_bonus = min(age_seconds * 0.5, 40)

    size_penalty = gpu_budget * 3

    return priority_weight + age_bonus - size_penalty


async def run_scheduler():
    print("WP-SJF Scheduler starting...")

    for p in PRIORITIES:
        await redis_service.create_consumer_group(f"tasks:{p}", GROUP_NAME)

    await redis_service.create_consumer_group("tasks:ready", "neuralqueue_workers")

    print("Scheduler is running. Scoring tasks every 2 seconds.\n")

    while True:
        try:
            candidates = []

            for priority in PRIORITIES:
                stream_name = f"tasks:{priority}"
                messages = await redis_service.read_stream(stream_name, count=50)
                for message_id, message_data in messages:
                    candidates.append({
                        "stream": stream_name,
                        "message_id": message_id,
                        "data": message_data,
                        "score": calculate_score(message_data, message_id),
                    })

            if not candidates:
                await asyncio.sleep(SCHEDULER_INTERVAL)
                continue

            candidates.sort(key=lambda c: c["score"], reverse=True)

            batch_size = min(len(candidates), 5)
            dispatched = candidates[:batch_size]

            for candidate in dispatched:
                await redis_service.push_to_stream("tasks:ready", candidate["data"])
                await redis_service.delete_message(candidate["stream"], candidate["message_id"])

                task_id = candidate["data"].get("task_id", "?")
                print(f"  Dispatched task {task_id[:8]}... (score: {candidate['score']:.1f})")

                await redis_service.publish_event("task_events", {
                    "type": "task_scheduled",
                    "task_id": candidate["data"].get("task_id"),
                    "score": round(candidate["score"], 2),
                })

            await asyncio.sleep(SCHEDULER_INTERVAL)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Scheduler error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(run_scheduler())
    except KeyboardInterrupt:
        print("\nScheduler stopped.")
