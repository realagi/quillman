import time
import asyncio
import websockets
import os
import requests
import wave

endpoint = "erik-dunteman--quillman-proto-web-dev.modal.run"

import os
import json
from pathlib import Path

# We have three sample audio files in the test-audio folder that we'll transcribe
files = os.listdir("test-audio")
files.sort()

# we're simulating a user speaking into a microphone
user_finish_time = None
def user_input_generator():
    first = True
    for wav in files:
        wav = "test-audio" / Path(wav)
        print(wav)
        with open(wav, "rb") as f:
            yield f.read()

    # used for understanding time of pipeline
    print("User finished speaking, waiting...")
    global user_finish_time
    user_finish_time = time.time()

async def main():
    print("Starting client script")

    # Step 1: GET /prewarm endpoint
    try:
        print("Prewarming models...")
        response = requests.get(f"https://{endpoint}/prewarm")
        response.raise_for_status()
        print("Prewarm request successful")
    except requests.exceptions.RequestException as e:
        print(f"Prewarm request failed: {e}")
        return

    # Step 2: WebSocket connection to /pipeline endpoint
    try:
        async with websockets.connect(f"wss://{endpoint}/pipeline") as websocket:
            print("WebSocket connection established")
            
            for wav in user_input_generator():
                s = time.time()
                await websocket.send(wav)
                print(f"Sent WAV chunk in {time.time() - s}s")

            history = [
                {"role": "user", "content": "Hello, how are you?"},
                {"role": "assistant", "content": "I'm doing well, thank you for asking!"},
            ]
            await websocket.send(f"<HISTORY>{json.dumps(history)}".encode())

            await websocket.send(b"<END>")
                
            print("Waiting for responses...")
            i = 0
            while True:
                response = await websocket.recv()
                if i == 0:
                    print(f"Time since end of user speech to FIRST TTS CHUNK: {time.time() - user_finish_time}s")

                if not isinstance(response, bytes):
                    raise TypeError("Expected bytes from websocket, got {type(response)}")
                
                with open(f"output_{i}.wav", "wb") as f:
                    f.write(response)

                i += 1

    except websockets.exceptions.WebSocketException as e:
        print(f"WebSocket connection failed: {e}")

    # merge all the wavs into one
    os.system("ffmpeg -f concat -i output_*.wav -c copy output.wav")

if __name__ == "__main__":
    asyncio.run(main())