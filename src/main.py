import os
import websockets
import asyncio
import base64
import cv2
import json
import pygame

# 送信する画像が保存されているディレクトリ


pygame.init()
pygame.mixer.init()
pygame.mouse.set_visible(False)

# リサイズ可能なウィンドウを作成
screen = pygame.display.set_mode((1920, 1080), pygame.RESIZABLE)
pygame.display.set_caption("kensuiou")
font = pygame.font.Font("assets/fonts/ZenMaruGothic-Medium.ttf", 100)
font_large = pygame.font.Font("assets/fonts/ZenMaruGothic-Medium.ttf", 300)
text_color = (255, 255, 255)  # 白色
background_color = (0, 0, 0)  # 黒色
sound_entry = pygame.mixer.Sound("assets/sounds/entry.wav")
sound_count = pygame.mixer.Sound("assets/sounds/coin.mp3")
img1 = pygame.image.load("assets/aquatan/IMG_4887.png")
img1 = pygame.transform.scale(img1, (500, 500)) 
img1 = pygame.transform.flip(img1, True, False) 
img2 = pygame.image.load("assets/aquatan/IMG_4889.png")
img2 = pygame.transform.scale(img2, (500, 500)) 
img3 = pygame.image.load("assets/aquatan/IMG_4892.png")
img3 = pygame.transform.scale(img3, (500, 500)) 
img4 = pygame.image.load("assets/aquatan/IMG_4886.png")
img4 = pygame.transform.scale(img4, (600, 600)) 
img4 = pygame.transform.flip(img4, True, False) 
img5 = pygame.image.load("assets/aquatan/IMG_4888.png")
img5 = pygame.transform.scale(img5, (500, 500))
img5 = pygame.transform.flip(img5, True, False)
img6 = pygame.image.load("assets/aquatan/IMG_4891.png")
img6 = pygame.transform.scale(img6, (500, 500))
img6 = pygame.transform.flip(img6, True, False)

async def send_images():
    async with websockets.connect("ws://192.168.100.101:8765") as websocket:
        entry_flg = True  # エントリー音を鳴らすフラグ
        previous_count = 0  # 前回のカウントを保持する変数
        sound_entry.play()
        cap = cv2.VideoCapture(0)
        while True :
            #　カメラから画像を撮りサーバーに送り続ける
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
                screen.blit(img1, (1100, 500))
                pygame.display.flip()

            elif response_data.get("status") == "Authenticated":

                if entry_flg:
                    sound_entry.play()
                    entry_flg = False
                name = response_data.get("name")
                text = font.render(f"{name}さん、こんにちは！", True, text_color)
                screen.blit(text, (150, 150))
                text = font.render(f"バーを持ってね〜！", True, text_color)
                screen.blit(text, (150, 400))
                screen.blit(img2, (1100, 500))
                pygame.display.flip()

            elif response_data.get("status") == "Counting":
                name = response_data.get("name")
                count = response_data.get("count")
                if previous_count != count:
                    sound_count.play()
                previous_count = count 
                if count == 0:
                    text = font_large.render(f"スタート！！！", True, text_color)
                else :
                    text = font_large.render(f" {count}回！！", True, text_color)
                    

                if count<10:
                    screen.blit(img3, (1300, 550))
                else:
                    screen.blit(img4, (1100, 500))

                screen.blit(text, (200, 150))
                pygame.display.flip()
                    
            if response_data.get("status") == "end":
                name = response_data.get("name")
                count = response_data.get("count")
                text = font.render(f"結果", True, text_color)
                screen.blit(text, (150, 150))
                text = font.render(f"{name}さん、{count}回！！", True, text_color)
                screen.blit(text, (150, 400))
                if count < 5:
                    screen.blit(img5, (1200, 550))
                elif count < 10:
                    screen.blit(img6, (1100, 500))
                else:
                    screen.blit(img4, (1100, 500))
               
                print(f"name: {response_data.get('name')}, Count: {response_data.get('count')}")
                # 7秒後に終了
                pygame.display.flip()
                await asyncio.sleep(7)
                screen.fill(background_color)
            
                break
                
        cap.release()   



def main():
    pygame.display.flip()
    try:
        while True:

            text = font.render("待機中...", True, text_color)
            screen.blit(text, (150, 150))
            text = font.render(f"Enterでスタート！！", True, text_color)
            screen.blit(text, (150, 400))
            pygame.display.flip()

            # 入力をリセット
            for event in pygame.event.get():
                pass
            
            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:  # ウィンドウの閉じるボタン
                        running = False

                    # キーが押されたとき
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_RETURN:  # Enterキー
                            running = False
                            print("Enterキーが押されました！")
            print("スタート")
            asyncio.run(send_images())
            print("再起動中...")
            pygame.display.flip()

    except KeyboardInterrupt:
        print("exit")

    print("終了します")
    pygame.quit()

if __name__ == "__main__":
    main()
    

    