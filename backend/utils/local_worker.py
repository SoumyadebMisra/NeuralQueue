import asyncio
import httpx
import shutil
import os
from typing import Optional
from backend.core.config import settings

class LocalWorkerManager:
    def __init__(self, port: int = 11434):
        self.port = port
        self.base_url = f"http://localhost:{port}"
        self.process: Optional[asyncio.subprocess.Process] = None
        self.status = "offline" # offline, starting, online, error

    async def get_status(self) -> str:
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    self.status = "online"
                    return "online"
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        
        if self.process and self.process.returncode is None:
            self.status = "starting"
            return "starting"
            
        self.status = "offline"
        return "offline"

    async def ensure_running(self):
        status = await self.get_status()
        if status == "online":
            return
        if status == "starting":
            return

        ollama_path = settings.OLLAMA_BINARY_PATH or shutil.which("ollama")
        
        if not ollama_path:
            potential_paths = [
                "/usr/local/bin/ollama", 
                "/Applications/Ollama.app/Contents/Resources/bin/ollama",
                "/opt/homebrew/bin/ollama"
            ]
            for p in potential_paths:
                if os.path.exists(p):
                    ollama_path = p
                    break
        
        if not ollama_path:
            self.status = "error"
            print("[local-worker] Ollama binary not found. Please install it or set OLLAMA_BINARY_PATH.")
            return

        print(f"[local-worker] Starting Ollama from {ollama_path}")
        self.status = "starting"
        
        try:
            # Configure for parallel execution
            env = os.environ.copy()
            env["OLLAMA_NUM_PARALLEL"] = "4"
            env["OLLAMA_MAX_LOADED_MODELS"] = "2"
            
            self.process = await asyncio.create_subprocess_exec(
                ollama_path, "serve",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            for i in range(10):
                await asyncio.sleep(1.5)
                status = await self.get_status()
                if status == "online":
                    print(f"[local-worker] Ready (concurrency enabled)")
                    return
            
            print("[local-worker] Initialization timeout.")
            self.status = "error"
        except Exception as e:
            print(f"[local-worker] Launch failed: {e}")
            self.status = "error"

    async def stop(self):
        if self.process and self.process.returncode is None:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception as e:
                print(f"[local-worker] Shutdown error: {e}")
                self.process.kill()
        self.status = "offline"

local_worker_manager = LocalWorkerManager()
