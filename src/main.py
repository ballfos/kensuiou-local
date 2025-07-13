import argparse
import asyncio
import base64
import json
import os

import cv2
import pygame as pg
import websockets

# 送信する画像が保存されているディレクトリ

pg.init()
pg.mixer.init()
pg.mouse.set_visible(False)

# リサイズ可能なウィンドウを作成
screen = pg.display.set_mode((1920, 1080), pg.RESIZABLE)
pg.display.set_caption("kensuiou")
font_path = pg.font.match_font("Noto Sans CJK JP")
fonts = {
    100: pg.font.Font(font_path, 100),
    150: pg.font.Font(font_path, 150),
    200: pg.font.Font(font_path, 200),
    250: pg.font.Font(font_path, 250),
    300: pg.font.Font(font_path, 300),
}
text_color = (255, 255, 255)  # 白色
background_color = (0, 0, 0)  # 黒色
sounds = {
    "entry": pg.mixer.Sound("assets/sounds/entry.wav"),
    "count": pg.mixer.Sound("assets/sounds/coin.mp3"),
}
images = {
    "auth": pg.image.load("assets/images/IMG_4887.png"),
    "guide": pg.image.load("assets/images/IMG_4889.png"),
    "ok": pg.image.load("assets/images/IMG_4886.png"),
    "good": pg.image.load("assets/images/IMG_4888.png"),
    "great": pg.image.load("assets/images/IMG_4891.png"),
}


async def websocket_session(uri: str):
    async with websockets.connect(uri) as websocket:
        entry_flg = True  # エントリー音を鳴らすフラグ
        previous_count = 0  # 前回のカウントを保持する変数
        sounds["entry"].play()

        cap = cv2.VideoCapture(0)
        while True:
            # 　カメラから画像を撮りサーバーに送り続ける
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
                text = fonts[100].render("顔認証中、、、、", True, text_color)
                screen.blit(text, (150, 150))
                screen.blit(images["auth"], (1100, 500))
                pg.display.flip()

            elif response_data.get("status") == "Authenticated":

                if entry_flg:
                    sounds["entry"].play()
                    entry_flg = False
                name = response_data.get("name")
                text = fonts[100].render(f"{name}さん、こんにちは！", True, text_color)
                screen.blit(text, (150, 150))
                text = fonts[150].render(f"バーを持ってね〜！", True, text_color)
                screen.blit(text, (150, 400))
                screen.blit(images["guide"], (1100, 500))
                pg.display.flip()

            elif response_data.get("status") == "Counting":
                name = response_data.get("name")
                count = response_data.get("count")
                if previous_count != count:
                    sounds["count"].play()
                previous_count = count
                if count == 0:
                    text = fonts[100].render(f"スタート！！！", True, text_color)
                else:
                    text = fonts[250].render(f" {count}回！！", True, text_color)

                if count < 5:
                    screen.blit(images["ok"], (1200, 550))
                elif count < 10:
                    screen.blit(images["good"], (1100, 500))
                else:
                    screen.blit(images["great"], (1100, 500))

                screen.blit(text, (150, 150))
                pg.display.flip()

            if response_data.get("status") == "end":
                name = response_data.get("name")
                count = response_data.get("count")
                text = fonts[100].render(f"結果", True, text_color)
                screen.blit(text, (150, 150))
                text = fonts[150].render(f"{name}さん、{count}回！！", True, text_color)
                screen.blit(text, (150, 400))
                if count < 5:
                    screen.blit(images["ok"], (1200, 550))
                elif count < 10:
                    screen.blit(images["good"], (1100, 500))
                else:
                    screen.blit(images["great"], (1100, 500))

                print(
                    f"name: {response_data.get('name')}, Count: {response_data.get('count')}"
                )
                # 7秒後に終了
                pg.display.flip()
                await asyncio.sleep(7)
                screen.fill(background_color)

                break
            # 0.1秒待機
            await asyncio.sleep(0.1)

        cap.release()


def main(args):
    pg.display.flip()
    try:
        running = True
        while running:

            text = fonts[100].render("待機中...", True, text_color)
            screen.blit(text, (150, 150))
            text = fonts[100].render(f"Enterでスタート！！", True, text_color)
            screen.blit(text, (150, 400))
            pg.display.flip()

            # 入力をリセット
            for event in pg.event.get():
                pass

            waiting = True
            while waiting:
                for event in pg.event.get():
                    if event.type == pg.QUIT:  # ウィンドウの閉じるボタン
                        running = False
                        waiting = False

                    # キーが押されたとき
                    if event.type == pg.KEYDOWN:
                        if event.key == pg.K_RETURN:  # Enterキー
                            waiting = False
                            break
            if not running:
                break
            print("スタート")
            asyncio.run(websocket_session(args.uri))
            print("再起動中...")
            pg.display.flip()

    except KeyboardInterrupt:
        print("exit")

    print("終了します")
    pg.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebSocket Client for Kensuiou")
    parser.add_argument(
        "--uri", type=str, default="ws://localhost:8765", help="WebSocket URI"
    )
    args = parser.parse_args()
    main(args)
