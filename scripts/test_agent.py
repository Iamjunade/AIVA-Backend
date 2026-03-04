import asyncio
import websockets
import json

async def main():
    headers = {"Authorization": "Bearer aiva-dev-token-2026"}
    async with websockets.connect('ws://127.0.0.1:8765', extra_headers=headers) as ws:
        # First wait for the connected response
        print("Connected Response:", await ws.recv())
        await ws.send('TEST_ASK: What is the weather in London right now? Please use your Google Search tool.')
        # Wait for answer
        result = await ws.recv()
        print("AIVA Answer:", result)

if __name__ == "__main__":
    asyncio.run(main())
