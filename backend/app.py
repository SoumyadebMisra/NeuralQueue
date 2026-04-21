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
WORKER_CONCURRENCY_LOCAL = 4
WORKER_CONCURRENCY_CLOUD = 20


def is_local_model(model: str) -> bool:
    m = model.lower()
    return any(x in m for x in ["ollama", "llama", "mistral", "local"])


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
                    model_name = candidate["data"].get("model", "")
                    ready_stream = "tasks:ready:local" if is_local_model(model_name) else "tasks:ready:cloud"
                    
                    await redis_service.push_to_stream(ready_stream, candidate["data"])
                    await redis_service.delete_message(candidate["stream"], candidate["message_id"])
                    task_id = candidate["data"].get("task_id", "?")
                    print(f"[scheduler] dispatched {task_id[:8]} to {ready_stream} (score: {candidate['score']:.1f})")

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
        
        # Load attachments for context
        # We use a session-managed fetch 
        from sqlalchemy import select
        from backend.models.attachment import Attachment
        res = await repo.db.execute(select(Attachment).where(Attachment.task_id == task.id))
        attachments = res.scalars().all()
        
        context_str = ""
        for att in attachments:
            if att.extracted_text:
                context_str += f"\n\n--- Content from {att.file_name} ---\n{att.extracted_text}\n"

        base_prompt = task.input_text or task.name
        final_prompt = f"Context from attached sources:\n{context_str}\n\nUser Request: {base_prompt}" if context_str else base_prompt

        completion_kwargs = {
            "model": model_id,
            "messages": [{"role": "user", "content": final_prompt}],
            "api_key": api_key,
            "api_base": api_base,
            "stream": True
        }

        if api_base and "localhost" in api_base:
            # Enforce parallelism in the local engine request
            completion_kwargs["extra_body"] = {
                "options": {
                    "num_parallel": 4,
                    "num_thread": 8
                }
            }
        
        if "gemini" in model_id:
            if not api_key:
                raise Exception("Gemini API Key is missing. Update in Settings.")
            
            import httpx
            pure_model = task.model.split("/")[-1]
            target_model = pure_model
            
            url_to_use = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:streamGenerateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": final_prompt}]}],
                "generationConfig": {"temperature": 0.7}
            }
            
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", url_to_use, json=payload, timeout=60.0) as resp:
                    if resp.status_code != 200:
                        # Fallback if v1beta fails for some reason
                        if resp.status_code == 400 or resp.status_code == 404:
                             url_v1 = url_to_use.replace("/v1beta/", "/v1/")
                             async with client.stream("POST", url_v1, json=payload, timeout=60.0) as resp2:
                                 if resp2.status_code != 200:
                                     err_body = await resp2.aread()
                                     raise Exception(f"Gemini API Error ({resp2.status_code}): {err_body.decode()}")
                                 resp = resp2 # Use the v1 response
                        else:
                            err_body = await resp.aread()
                            raise Exception(f"Gemini API Error ({resp.status_code}): {err_body.decode()}")
                    if resp.status_code != 200:
                        err_body = await resp.aread()
                        raise Exception(f"Gemini API Error ({resp.status_code}): {err_body.decode()}")
                    full_output = ""
                    decoder = json.JSONDecoder()
                    buffer = ""
                    ttft = None
                    token_count = 0
                    
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
                                        if chunk_text:
                                            if ttft is None:
                                                ttft = (time.time() - start_time) * 1000
                                            token_count += len(chunk_text.split()) or 1 # Simple word count as token proxy
                                            
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
                    
                    duration = time.time() - start_time
                    latency_ms = int(duration * 1000)
                    tps = token_count / duration if duration > 0 else 0
                    
                    await repo.update(task, {
                        "status": TaskStatus.COMPLETED,
                        "output_text": full_output,
                        "completed_at": datetime.now(UTC),
                        "latency_ms": latency_ms
                    })
                    
                    await redis_service.publish_event("task_events", {
                        "type": "task_completed",
                        "task_id": str(task.id),
                        "output_text": full_output,
                        "metrics": {
                            "ttft_ms": round(ttft, 2) if ttft else None,
                            "tps": round(tps, 2),
                            "latency_ms": latency_ms,
                            "provider": "google/gemini"
                        }
                    })
                    return # Task complete

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
    duration = time.time() - start_time
    tps = token_count / duration if duration > 0 else 0
    provider = "local/ollama" if "localhost" in (api_base or "") else "cloud/litellm"
    
    task.completed_at = datetime.now(UTC)
    task.latency_ms = latency
    await db.commit()

    await redis_service.publish_event("task_events", {
        "type": "task_completed", 
        "task_id": task_id, 
        "metrics": {
            "ttft_ms": round(ttft, 2) if ttft else None,
            "tps": round(tps, 2),
            "latency_ms": round(latency, 2),
            "provider": provider
        }
    })
    print(f"[worker] completed {task_id[:8]}... in {latency:.0f}ms (TPS: {tps:.1f})")


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

            for stream_name, stream_messages in messages:
                for message_id, message_data in stream_messages:
                    task_id = message_data.get("task_id")
                    
                    # Spawn task in background
                    async def run_and_ack(tid, msg_id, sn):
                        try:
                            async with async_session_maker() as db:
                                try:
                                    await process_single_task(tid, db)
                                    await redis_service.acknowledge_message(sn, WORKER_GROUP, msg_id)
                                except Exception as e:
                                    print(f"[worker] error on {tid}: {e}")
                                    await handle_failure(tid, db, message_data)
                                    await redis_service.acknowledge_message(sn, WORKER_GROUP, msg_id)
                        finally:
                            # Always release the slot regardless of outcome
                            semaphore.release()
                                
                    asyncio.create_task(run_and_ack(task_id, message_id, stream_actual))

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[worker] loop error on {worker_name}: {e}")
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
        # Local Worker Fleet
        asyncio.create_task(worker_loop("worker-local-1", "tasks:ready:local", WORKER_CONCURRENCY_LOCAL)),
        # Cloud Worker Fleet
        asyncio.create_task(worker_loop("worker-cloud-1", "tasks:ready:cloud", WORKER_CONCURRENCY_CLOUD)),
        asyncio.create_task(worker_loop("worker-cloud-2", "tasks:ready:cloud", WORKER_CONCURRENCY_CLOUD)),
    ]
    print(f"[app] orchestrator running (Local-Cap: {WORKER_CONCURRENCY_LOCAL}, Cloud-Cap: {WORKER_CONCURRENCY_CLOUD * 2})")
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