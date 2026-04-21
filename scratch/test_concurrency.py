import asyncio
import litellm
import time

async def call_ollama(name: str, model: str):
    print(f"[{name}] Starting call with {model}...")
    start = time.time()
    response = await litellm.acompletion(
        model=model,
        messages=[{"role": "user", "content": "Write a short poem about space."}],
        api_base="http://localhost:11434",
        stream=True,
        extra_body={
            "options": {
                "num_parallel": 4,
                "num_thread": 8
            }
        }
    )
    
    chunks = 0
    async for chunk in response:
        content = chunk.choices[0].delta.content
        if content:
            chunks += 1
            if chunks % 10 == 0:
                print(f"[{name}] Received chunk {chunks}")
    
    end = time.time()
    print(f"[{name}] Finished in {end - start:.2f}s")

async def main():
    print("Testing concurrent calls to different models...")
    await asyncio.gather(
        call_ollama("Llama3", model="ollama/llama3"),
        call_ollama("Mistral", model="ollama/mistral")
    )

if __name__ == "__main__":
    asyncio.run(main())
