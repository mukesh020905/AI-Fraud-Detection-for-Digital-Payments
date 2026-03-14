import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://localhost:8000/ws"
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                print(f"Received Transaction: {data.get('TransactionID')} | Risk: {data.get('RiskLevel')}")
    except Exception as e:
        print(f"WebSocket Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_ws())
    except KeyboardInterrupt:
        pass
