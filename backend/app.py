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
from backend.utils.local_worker import local_worker_manager
import litellm

PRIORITIES = ["critical", "high", "medium", "low"]
PRIORITY_WEIGHTS = {"critical": 100, "high": 60, "medium": 30, "low": 10}
SCHEDULER_GROUP = "scheduler_group"
WORKER_GROUP = "neuralqueue_workers"
MAX_RETRIES = 3


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
                for candidate in candidates[:5]:
                    await redis_service.push_to_stream("tasks:ready", candidate["data"])
                    await redis_service.delete_message(candidate["stream"], candidate["message_id"])
                    task_id = candidate["data"].get("task_id", "?")
                    print(f"[scheduler] dispatched {task_id[:8]}... (score: {candidate['score']:.1f})")

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
        model_id = task.model.lower()
        
        if "gpt" in model_id:
            api_key = user.openai_api_key
        elif "claude" in model_id:
            api_key = user.anthropic_api_key
        elif "gemini" in model_id:
            api_key = user.gemini_api_key
            # LiteLLM routes to Google AI Studio with gemini/ prefix.
            # If it's still failing, we ensure the model name is exactly what AI Studio expects.
            if not task.model.startswith("gemini/"):
                task.model = f"gemini/{task.model}"
        elif any(x in model_id for x in ["ollama", "llama", "mistral"]):
            # Trigger lazy startup for local worker
            await local_worker_manager.ensure_running()
            api_base = "http://localhost:11434"
            # Remove "ollama/" prefix if present for the actual call
            if model_id.startswith("ollama/"):
                task.model = task.model[7:]
            
            if not task.model.startswith("ollama/"):
                task.model = f"ollama/{task.model}"
        
        if not api_key and not api_base:
            raise ValueError(f"No credentials or local base configured for {task.model}. Please update your settings.")

        # Real AI dispatch with STREAMING
        # For Gemini, LiteLLM uses the 'gemini/' prefix to route to Google AI Studio.
        # We ensure api_key is passed correctly and force the provider to avoid Vertex.
        
        completion_kwargs = {
            "model": task.model,
            "messages": [{"role": "user", "content": task.input_text or task.name}],
            "api_key": api_key,
            "api_base": api_base,
            "stream": True
        }
        
        if "gemini" in model_id:
            if not api_key:
                raise Exception("Gemini API Key is missing. Update in Settings.")
            
            import httpx
            pure_model = task.model.split("/")[-1]
            # Since we now use precision-verified names from the frontend, 
            # we can pass them directly to the API endpoints.
            target_model = pure_model
            
            # Try v1 first, then fallback to v1beta 
            url = f"https://generativelanguage.googleapis.com/v1/models/{target_model}:streamGenerateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": task.input_text or task.name}]}],
                "generationConfig": {"temperature": 0.7}
            }
            
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, timeout=60.0) # Dummy for initial check? No, use stream.
                url_to_use = url
                if resp.status_code == 404:
                    url_to_use = url.replace("/v1/", "/v1beta/")
                
                async with client.stream("POST", url_to_use, json=payload, timeout=60.0) as resp:
                    if resp.status_code != 200:
                        err_body = await resp.aread()
                        raise Exception(f"Gemini API Error ({resp.status_code}): {err_body.decode()}")
                    full_output = ""
                    decoder = json.JSONDecoder()
                    buffer = ""
                    
                    # Google AI Studio returns an array of JSON objects over time, often pretty-printed
                    async for chunk in resp.aiter_text():
                        buffer += chunk
                        buffer = buffer.lstrip().lstrip("[").lstrip(",").lstrip()
                        
                        while buffer:
                            try:
                                # Attempt to decode a complete JSON object from the front of the buffer
                                obj, index = decoder.raw_decode(buffer)
                                buffer = buffer[index:].lstrip().lstrip(",").lstrip()
                                
                                if "candidates" in obj:
                                    parts = obj["candidates"][0].get("content", {}).get("parts", [])
                                    if parts and "text" in parts[0]:
                                        chunk_text = parts[0]["text"]
                                        full_output += chunk_text
                                        await redis_service.publish_event("task_events", {
                                            "type": "task_chunk",
                                            "task_id": str(task.id),
                                            "chunk": chunk_text,
                                        })
                            except json.JSONDecodeError:
                                # Partial JSON in buffer, wait for more data
                                break
                            except Exception as e:
                                print(f"[worker] Unexpected Gemini processing error: {e}")
                                break
                    
                    await repo.update(task, {
                        "status": TaskStatus.COMPLETED,
                        "output_text": full_output,
                        "completed_at": datetime.now(UTC),
                        "latency_ms": int((time.time() - start_time) * 1000)
                    })
                    
                    await redis_service.publish_event("task_events", {
                        "type": "task_completed",
                        "task_id": str(task.id),
                        "output_text": full_output
                    })
                    return # Task complete

        response = await litellm.acompletion(**completion_kwargs)
        
        full_text = ""
        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                full_text += content
                await redis_service.publish_event("task_events", {
                    "type": "task_chunk",
                    "task_id": task_id,
                    "chunk": content
                })
        
        task.output_text = full_text
        task.status = TaskStatus.COMPLETED
        print(f"[worker] AI streaming call successful for {task_id[:8]}")

    except Exception as e:
        print(f"[worker] AI dispatch failed: {e}")
        task.output_text = f"Error: {str(e)}"
        raise e 

    latency = (time.time() - start_time) * 1000
    task.completed_at = datetime.now(UTC)
    task.latency_ms = latency
    await db.commit()

    await redis_service.publish_event("task_events", {
        "type": "task_completed", "task_id": task_id, "latency_ms": round(latency, 2),
    })
    print(f"[worker] completed {task_id[:8]}... in {latency:.0f}ms")


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


async def worker_loop(worker_name: str):
    await redis_service.create_consumer_group("tasks:ready", WORKER_GROUP)
    streams = {"tasks:ready": ">"}

    while True:
        try:
            messages = await redis_service.read_from_group(
                group_name=WORKER_GROUP, consumer_name=worker_name,
                streams=streams, count=1, block=2000,
            )
            if not messages:
                continue

            for stream_name, stream_messages in messages:
                for message_id, message_data in stream_messages:
                    task_id = message_data.get("task_id")
                    async with async_session_maker() as db:
                        try:
                            await process_single_task(task_id, db)
                            await redis_service.acknowledge_message(stream_name, WORKER_GROUP, message_id)
                        except Exception as e:
                            print(f"[worker] error on {task_id}: {e}")
                            await handle_failure(task_id, db, message_data)
                            await redis_service.acknowledge_message(stream_name, WORKER_GROUP, message_id)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[worker] loop error: {e}")
            await asyncio.sleep(5)


async def monitor_local_worker():
    while True:
        status = await local_worker_manager.get_status()
        await redis_service.publish_event("task_events", {
            "type": "local_worker_status",
            "status": status
        })
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
        asyncio.create_task(monitor_local_worker()),
        asyncio.create_task(scheduler_loop()),
        asyncio.create_task(worker_loop("worker-1")),
        asyncio.create_task(worker_loop("worker-2")),
    ]
    print("[app] scheduler + 2 workers + local worker monitor running")
    yield
    print("[app] stopping tasks...")
    for t in tasks:
        t.cancel()
    await local_worker_manager.stop()
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