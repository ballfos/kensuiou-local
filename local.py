import os
import websockets
import asyncio
import base64
import cv2
import json
import pygame

# 送信する画像が保存されているディレクトリ

os.environ['SDL_VIDEO_WINDOW_POS'] = "0, -1080"  # 外部モニターの左上座標
pygame.init()
pygame.mixer.init()

# フルスクリーンモードのウィンドウを作成
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("kensuiou")
font = pygame.font.Font("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 100)
text_color = (255, 255, 255)  # 白色
background_color = (0, 0, 0)  # 黒色
sound = pygame.mixer.Sound("coin.mp3")


async def send_images():
    async with websockets.connect("ws://localhost:8765") as websocket:
        previous_count = 0  # 前回のカウントを保持する変数

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

            screen.fill(background_color)

            if response_data.get("status") == "start":
                text = font.render("顔認証中、、、、", True, text_color)
                screen.blit(text, (150, 150))
                pygame.display.flip()

            elif response_data.get("status") == "Authenticated":
                name = response_data.get("name")
                text = font.render(f"{name}さん、こんにちは！", True, text_color)
                screen.blit(text, (150, 150))
                text = font.render(f"バーを持ってください！", True, text_color)
                screen.blit(text, (150, 400))
                pygame.display.flip()

            elif response_data.get("status") == "Counting":
                name = response_data.get("name")
                count = response_data.get("count")
                if previous_count != count:
                    sound.play()
                previous_count = count 
                if count == 0:
                    text = font.render(f"スタート！！！", True, text_color)
                else :

                    text = font.render(f" {count}回！！", True, text_color)
                screen.blit(text, (150, 150))
                pygame.display.flip()
                    
            if response_data.get("status") == "end":
                name = response_data.get("name")
                count = response_data.get("count")
                text = font.render(f"結果", True, text_color)
                screen.blit(text, (150, 150))
                text = font.render(f"{name}さん、{count}回！！", True, text_color)
                screen.blit(text, (150, 400))
               
                print(f"name: {response_data.get('name')}, Count: {response_data.get('count')}")
                # 10秒後に終了
                pygame.display.flip()
                await asyncio.sleep(10)
                

                break
                
        cap.release()   

if __name__ == "__main__":
    asyncio.run(send_images())
    