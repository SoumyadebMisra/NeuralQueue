import asyncio
import json
import random
import time
from uuid import UUID
from datetime import datetime, UTC
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.controller.user_controller import router as user_router
from backend.controller.task_controller import router as task_router
from backend.core.config import settings
from backend.service.ws_manager import ws_manager
from backend.service.redis_service import redis_service
from backend.utils.get_db import async_session_maker
from backend.repository.task_repository import TaskRepository
from backend.repository.user_repository import UserRepository
from backend.models.user import User
from backend.models.enums import TaskStatus
from backend.core.models_config import get_model_info
import litellm
PRIORITIES = ["critical", "high", "medium", "low"]
PRIORITY_WEIGHTS = {"critical": 100, "high": 60, "medium": 30, "low": 10}
SCHEDULER_GROUP = "scheduler_group"
WORKER_GROUP = "neuralqueue_workers"
MAX_RETRIES = 3
WORKER_CONCURRENCY = 20


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


async def process_single_task(task_id: str, db):
    repo = TaskRepository(db)
    user_repo = UserRepository(db)
    
    task = await repo.get(UUID(task_id))
    if not task:
        return

    user = await user_repo.get(task.user_id)
    if not user:
        return

    task.status = TaskStatus.PROCESSING
    task.started_at = datetime.now(UTC)
    await db.commit()

    await redis_service.publish_event("task_events", {
        "type": "task_processing", "task_id": task_id,
    })

    print(f"[worker] starting AI task {task_id[:8]}... with model {task.model}")
    start_time = time.time()
    
    try:
        # Determine provider and credentials
        api_key = None
        api_base = None
        model_info = get_model_info(task.model)
        provider = model_info.get("provider", "").lower()
        
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
        print(f"[worker] completed {task_id[:8]}... in {latency_ms}ms")

    except Exception as e:
        print(f"[worker] task failed ({task_id}): {e}")
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

    print(f"[worker] {worker_name} listening on {stream_name} (concurrency: {concurrency})")

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
                    
                    async def run_and_ack(tid, msg_id, sn):
                        try:
                            async with async_session_maker() as db:
                                try:
                                    await process_single_task(tid, db)
                                    await redis_service.acknowledge_message(sn, WORKER_GROUP, msg_id)
                                except Exception as e:
                                    print(f"[worker] task failed ({tid}): {e}")
                                    await handle_failure(tid, db, message_data)
                                    await redis_service.acknowledge_message(sn, WORKER_GROUP, msg_id)
                        finally:
                            semaphore.release()
                                
                    asyncio.create_task(run_and_ack(task_id, message_id, s_name))

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[worker] loop error on {worker_name}: {e}")
            await asyncio.sleep(5)


async def redis_event_listener():
    pubsub = await redis_service.subscribe("task_events")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                event = json.loads(message["data"])
                await ws_manager.broadcast(event)
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe("task_events")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[app] starting scheduler + workers...")
    tasks = [
        asyncio.create_task(redis_event_listener()),
        asyncio.create_task(scheduler_loop()),
        # Scalable Cloud Worker Fleet
        asyncio.create_task(worker_loop("worker-1", "tasks:ready", WORKER_CONCURRENCY)),
        asyncio.create_task(worker_loop("worker-2", "tasks:ready", WORKER_CONCURRENCY)),
        asyncio.create_task(worker_loop("worker-3", "tasks:ready", WORKER_CONCURRENCY)),
        asyncio.create_task(worker_loop("worker-4", "tasks:ready", WORKER_CONCURRENCY)),
    ]
    print(f"[app] orchestrator running (Capacity: {WORKER_CONCURRENCY * 4})")
    yield
    print("[app] stopping tasks...")
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await redis_service.disconnect()


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description="Backend for high-performance AI workload orchestration",
        version=settings.VERSION,
        redirect_slashes=False,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(user_router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
    application.include_router(task_router, prefix=f"{settings.API_V1_STR}/tasks", tags=["Tasks"])

    return application


app = create_application()


@app.get("/", tags=["Health"])
async def health_check():
    return {
        "status": "online",
        "message": "NeuralQueue API is running",
        "version": settings.VERSION
    }


@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)