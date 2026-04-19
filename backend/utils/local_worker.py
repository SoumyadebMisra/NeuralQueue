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
        if status == "online" or status == "starting":
            return

        # Check if ollama exists
        ollama_path = settings.OLLAMA_BINARY_PATH or shutil.which("ollama")
        
        if not ollama_path:
            # Common MacOS path fallback
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
            print(f"[local-worker] CRITICAL: ollama binary not found. Please install from https://ollama.com or set OLLAMA_BINARY_PATH in your .env")
            return

        print(f"[local-worker] starting ollama serve from {ollama_path}...")
        self.status = "starting"
        
        try:
            self.process = await asyncio.create_subprocess_exec(
                ollama_path, "serve",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Poll for readiness (Wait up to 15 seconds)
            for i in range(15):
                await asyncio.sleep(1)
                status = await self.get_status()
                if status == "online":
                    print(f"[local-worker] ollama is ready after {i+1} seconds")
                    return
                print(f"[local-worker] waiting for ollama... (attempt {i+1}/15)")
            
            print("[local-worker] timeout waiting for ollama to become responsive")
            self.status = "error"
        except Exception as e:
            print(f"[local-worker] failed to start: {e}")
            self.status = "error"

    async def stop(self):
        if self.process and self.process.returncode is None:
            print("[local-worker] shutting down ollama...")
            try:
                self.process.terminate()
                await self.process.wait()
                print("[local-worker] ollama stopped")
            except Exception as e:
                print(f"[local-worker] shutdown error: {e}")
                self.process.kill()
        self.status = "offline"

local_worker_manager = LocalWorkerManager()
