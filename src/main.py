import argparse
import asyncio
import base64
import json
import os
from dataclasses import dataclass
from enum import Enum

import cv2
import pygame as pg
import websockets


class ServerStatus(Enum):
    START = "start"
    AUTHENTICATED = "Authenticated"
    COUNTING = "Counting"
    END = "end"


@dataclass
class ServerResponse:
    status: ServerStatus
    name: str
    count: int

    @classmethod
    def from_json(cls, json_data: str):
        data = json.loads(json_data)
        return cls(
            status=ServerStatus(data["status"]),
            name=data.get("name", "Unknown"),
            count=data.get("count", 0),
        )


TEXT_COLOR = (255, 255, 255)
BACKGROUND_COLOR = (0, 0, 0)

pg.init()
pg.mixer.init()

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


async def websocket_session(queue: asyncio.Queue[ServerResponse], uri: str):
    async with websockets.connect(uri) as websocket:
        cap = cv2.VideoCapture(0)
        while True:
            # カメラから画像を撮りサーバーに送り続ける
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture image")
                break

            # 画像をBase64エンコードして送信
            _, buffer = cv2.imencode(".jpg", frame)
            encoded_image = base64.b64encode(buffer).decode("utf-8")
            await websocket.send(encoded_image)
            response = ServerResponse.from_json(await websocket.recv())
            print(f"Received: {response}")
            queue.put_nowait(response)
            if response.status == ServerStatus.END:
                break
            # 0.2秒待機
            await asyncio.sleep(0.2)

        cap.release()


def draw_text(
    surface: pg.Surface,
    text: str,
    pos: tuple[int, int],
    font: pg.font.Font,
    color: tuple[int, int, int] = TEXT_COLOR,
    background: tuple[int, int, int] = None,
):
    text_surface = font.render(text, True, color, background)
    surface.blit(text_surface, pos)


class GamePhase(Enum):
    WAITING = "waiting"
    RUNNING = "running"
    RESULT = "result"


async def main(args):
    phase = GamePhase.WAITING
    last_response = None
    running = True
    queue = asyncio.Queue()

    websocket_task = None
    while running:
        # イベント処理
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    running = False
                elif event.key == pg.K_RETURN:
                    if phase == GamePhase.WAITING:
                        phase = GamePhase.RUNNING
                        websocket_task = asyncio.create_task(
                            websocket_session(queue, args.uri)
                        )
                        print("ゲーム開始")
                    elif phase == GamePhase.RESULT:
                        phase = GamePhase.WAITING
                        last_response = None
                        print("ゲームをリセット")

        # queueからのメッセージ処理
        try:
            response = queue.get_nowait()
            # レスポンスが存在し、前回のレスポンスと異なる場合に処理
            if response and (last_response is None or response != last_response):
                if response.status == ServerStatus.START:
                    print("サーバーからのスタートメッセージを受信")
                    sounds["entry"].play()
                elif response.status == ServerStatus.AUTHENTICATED:
                    print(f"認証成功: {response.name}")
                    sounds["entry"].play()
                elif response.status == ServerStatus.COUNTING:
                    print(f"カウント中: {response.name}, カウント: {response.count}")
                    if response.count != last_response.count if last_response else None:
                        sounds["count"].play()
                elif response.status == ServerStatus.END:
                    print(f"ゲーム終了: {response.name}, カウント: {response.count}")
                last_response = response
        except asyncio.QueueEmpty:
            pass

        # 描画処理
        screen.fill(BACKGROUND_COLOR)
        if phase == GamePhase.WAITING:
            draw_text(screen, "待機中...", (150, 150), fonts[100])
            draw_text(screen, "Enterでスタート！！", (150, 400), fonts[100])

        elif phase == GamePhase.RUNNING:
            if last_response is None:
                draw_text(screen, "カメラを起動中...", (150, 150), fonts[100])

            elif last_response.status == ServerStatus.START:
                draw_text(screen, "顔認証中、、、、", (150, 150), fonts[100])
                screen.blit(images["auth"], (1100, 500))

            elif last_response.status == ServerStatus.AUTHENTICATED:
                name = last_response.name
                draw_text(screen, f"{name}さん、こんにちは！", (150, 150), fonts[100])
                draw_text(screen, "バーを持ってね〜！", (150, 400), fonts[150])
                screen.blit(images["guide"], (1100, 500))

            elif last_response.status == ServerStatus.COUNTING:
                name = last_response.name
                count = last_response.count
                if count == 0:
                    draw_text(
                        screen, f"{name}さん、スタート！！！", (150, 150), fonts[100]
                    )
                else:
                    draw_text(
                        screen, f"{name}さん、{count}回！！", (150, 150), fonts[100]
                    )

                if count < 5:
                    screen.blit(images["ok"], (1200, 550))
                elif count < 10:
                    screen.blit(images["good"], (1100, 500))
                else:
                    screen.blit(images["great"], (1100, 500))

            elif last_response.status == ServerStatus.END:
                phase = GamePhase.RESULT
                print("ゲーム終了")

        elif phase == GamePhase.RESULT:
            name = last_response.name
            count = last_response.count
            draw_text(screen, f"結果", (150, 150), fonts[100])
            draw_text(screen, f"{name}さん、{count}回！！", (150, 400), fonts[150])
            if count < 5:
                screen.blit(images["ok"], (1200, 550))
            elif count < 10:
                screen.blit(images["good"], (1100, 500))
            else:
                screen.blit(images["great"], (1100, 500))

            print(f"name: {last_response.name}, Count: {last_response.count}")

        pg.display.flip()
        await asyncio.sleep(0.2)

    print("終了します")
    if websocket_task:
        websocket_task.cancel()
    pg.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebSocket Client for Kensuiou")
    parser.add_argument(
        "--uri", type=str, default="ws://localhost:8765", help="WebSocket URI"
    )
    args = parser.parse_args()
    asyncio.run(main(args))
