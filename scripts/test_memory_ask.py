import asyncio
import websockets
import json

AIVA_WS_URL = "ws://127.0.0.1:8765"
AUTH_TOKEN = "aiva-dev-token-2026"
QUESTION = "What did you see me looking at a few seconds ago? Describe the history."

async def test_ask():
    try:
        async with websockets.connect(
            AIVA_WS_URL,
            additional_headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        ) as websocket:
            print("Connected.")
            # Send question
            payload = f"TEST_ASK:{QUESTION}"
            await websocket.send(payload)
            print(f"Sent: {payload}")
            
            # Wait for response
            while True:
                resp = await websocket.recv()
                data = json.loads(resp)
                if data.get("type") == "test_answer":
                    print("\n--- AIVA Response ---")
                    print(data.get("answer"))
                    break
                elif data.get("type") == "connected":
                    continue
                else:
                    print(f"Other msg: {data}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    asyncio.run(test_ask())
