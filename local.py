import os
import websockets
import asyncio
import base64
import cv2
import json
# 送信する画像が保存されているディレクトリ
image_dir = "captured_images"

async def send_images():
    async with websockets.connect("ws://localhost:8765") as websocket:

        while True :
            #　カメラから画像を撮りサーバーに送り続ける
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture image")
                break

            # 画像をBase64エンコードして送信
            _, buffer = cv2.imencode(".jpg", frame)
            encoded_image = base64.b64encode(buffer).decode("utf-8")
            await websocket.send(encoded_image)
            response = await websocket.recv()
            response_data = json.loads(response)
            if response_data.get("status") == "end":
               print(f"name: {response_data.get('name')}, Count: {response_data.get('count')}")
               break
                
        cap.release()   

if __name__ == "__main__":
    asyncio.run(send_images())