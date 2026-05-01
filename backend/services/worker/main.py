import asyncio
import os
import time
from uuid import UUID
from datetime import datetime, UTC

from backend.service.redis_service import redis_service
from backend.utils.get_db import async_session_maker
from backend.repository.task_repository import TaskRepository
from backend.repository.user_repository import UserRepository
from backend.models.enums import TaskStatus
from backend.core.models_config import get_model_info
import litellm

WORKER_GROUP = "neuralqueue_workers"
MAX_RETRIES = 3
WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "20"))
WORKER_NAME = os.getenv("WORKER_NAME", f"worker-{os.getpid()}")


async def process_single_task(task_id: str, db):
    repo = TaskRepository(db)
    user_repo = UserRepository(db)
    
    task = await repo.get(UUID(task_id))
    if not task:
        return

    user = await user_repo.get(task.user_id)
    if not user:
        return

    await redis_service.publish_event("task_events", {
        "type": "task_processing", "task_id": task_id,
    })

    print(f"[{WORKER_NAME}] starting AI task {task_id[:8]}... with model {task.model}")
    start_time = time.time()
    
    try:
        # Determine provider and credentials
        api_key = None
        provider = get_model_info(task.model).get("provider", "").lower()
        
        # Fallback for unrecognized or old model IDs
        if not provider:
            m = task.model.lower()
            if "gpt" in m: provider = "openai"
            elif "claude" in m: provider = "anthropic"
            elif "gemini" in m: provider = "google"
        
        if provider == "openai":
            api_key = user.openai_api_key
        elif provider == "anthropic":
            api_key = user.anthropic_api_key
        elif provider == "google":
            api_key = user.gemini_api_key
            if not task.model.startswith("gemini/"):
                task.model = f"gemini/{task.model}"
        
        if not api_key:
            raise ValueError(f"Credentials missing for provider '{provider}' of model {task.model}. Update settings.")

        # Prepare context from attachments
        from sqlalchemy import select
        from backend.models.attachment import Attachment
        res = await repo.db.execute(select(Attachment).where(Attachment.task_id == task.id))
        attachments = res.scalars().all()
        
        context_str = ""
        for att in attachments:
            if att.extracted_text:
                context_str += f"\n\n--- Source: {att.file_name} ---\n{att.extracted_text}\n"

        base_prompt = task.input_text or task.name
        final_prompt = f"Context:\n{context_str}\n\nUser Request: {base_prompt}" if context_str else base_prompt

        target_model = task.model
        
        # Ensure correct prefix for gemini models if not already present (for legacy tasks)
        if "gemini" in target_model.lower() and "gemini/" not in target_model:
            target_model = f"gemini/{target_model}"

        completion_kwargs = {
            "model": target_model,
            "messages": [{"role": "user", "content": final_prompt}],
            "api_key": api_key,
            "stream": True,
            "custom_llm_provider": "gemini" if "gemini" in target_model.lower() else None
        }

        # Execute via LiteLLM
        response = await litellm.acompletion(**completion_kwargs)
        
        full_text = ""
        ttft = None
        token_count = 0
        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                if ttft is None:
                    ttft = (time.time() - start_time) * 1000
                token_count += len(content.split()) or 1
                
                full_text += content
                await redis_service.publish_event("task_events", {
                    "type": "task_chunk",
                    "task_id": str(task.id),
                    "chunk": content
                })
        
        duration = time.time() - start_time
        latency_ms = int(duration * 1000)

        await repo.update(task, {
            "status": TaskStatus.COMPLETED,
            "output_text": full_text,
            "completed_at": datetime.now(UTC),
            "latency_ms": latency_ms
        })
        
        await redis_service.publish_event("task_events", {
            "type": "task_completed",
            "task_id": str(task.id),
            "status": "completed",
            "ttft_ms": round(ttft, 2) if ttft else None,
            "latency_ms": latency_ms,
            "tps": round(token_count / duration, 2) if duration > 0 else 0
        })
        print(f"[{WORKER_NAME}] completed {task_id[:8]}... in {latency_ms}ms")

    except Exception as e:
        print(f"[{WORKER_NAME}] task failed ({task_id}): {e}")
        await repo.update(task, {
            "status": TaskStatus.FAILED,
            "output_text": f"Error: {str(e)}"
        })
        await redis_service.publish_event("task_events", {
            "type": "task_failed",
            "task_id": task_id,
            "error": str(e)
        })


async def handle_failure(task_id: str, db, message_data: dict):
    repo = TaskRepository(db)
    task = await repo.get(UUID(task_id))
    if not task:
        return

    task.retries += 1
    task.status = TaskStatus.FAILED
    await db.commit()

    if task.retries >= MAX_RETRIES:
        await redis_service.push_to_dlq({
            "task_id": task_id, "retries": str(task.retries),
            "failed_at": datetime.now(UTC).isoformat(),
        })
        await redis_service.publish_event("task_events", {
            "type": "task_dead_lettered", "task_id": task_id,
        })
    else:
        await redis_service.push_to_stream(f"tasks:{task.priority.value}", message_data)
        await redis_service.publish_event("task_events", {
            "type": "task_retrying", "task_id": task_id, "retry": task.retries,
        })


async def worker_loop(worker_name: str, stream_name: str, concurrency: int):
    await redis_service.create_consumer_group(stream_name, WORKER_GROUP)
    streams = {stream_name: ">"}
    semaphore = asyncio.Semaphore(concurrency)

    print(f"[{worker_name}] standalone service listening on {stream_name} (concurrency: {concurrency})")

    while True:
        try:
            # Backpressure: Wait for a free concurrency slot before fetching next task
            await semaphore.acquire()
            
            messages = await redis_service.read_from_group(
                group_name=WORKER_GROUP, consumer_name=worker_name,
                streams=streams, count=1, block=2000,
            )
            
            if not messages:
                semaphore.release()
                continue

            for s_name, stream_messages in messages:
                for message_id, message_data in stream_messages:
                    task_id = message_data.get("task_id")
                    
                    async def run_and_ack(tid, msg_id, sn, owner=worker_name):
                        try:
                            async with async_session_maker() as db:
                                repo = TaskRepository(db)
                                claimed = await repo.try_claim_task(UUID(tid), owner)

                                if not claimed:
                                    print(f"[{owner}] task {tid[:8]} already claimed, acking stream message")
                                    await redis_service.acknowledge_message(sn, WORKER_GROUP, msg_id)
                                    return

                                try:
                                    await process_single_task(tid, db)
                                    await redis_service.acknowledge_message(sn, WORKER_GROUP, msg_id)
                                except Exception as e:
                                    print(f"[{owner}] task failed ({tid}): {e}")
                                    await handle_failure(tid, db, message_data)
                                    await redis_service.acknowledge_message(sn, WORKER_GROUP, msg_id)
                        finally:
                            semaphore.release()
                                
                    asyncio.create_task(run_and_ack(task_id, message_id, s_name))

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[{worker_name}] loop error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(worker_loop(WORKER_NAME, "tasks:ready", WORKER_CONCURRENCY))
    except KeyboardInterrupt:
        print(f"\n[{WORKER_NAME}] stopped.")
