import argparse
import asyncio
import base64
import json
from dataclasses import dataclass
from enum import Enum

import cv2
import pygame as pg
import websockets


class ServerStatus(Enum):
    START = "start"
    RECOGNIZED = "Authenticated"
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
SCREEN_SIZE = (1920, 1080)
RESULT_DURATION = 7000
FPS = 5

pg.init()
pg.mixer.init()

# リサイズ可能なウィンドウを作成

screen = pg.display.set_mode(SCREEN_SIZE, pg.RESIZABLE)
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
    "wait": pg.image.load("assets/images/wait.png"),
    "setup": pg.image.load("assets/images/setup.png"),
    "guide": pg.image.load("assets/images/guide.png"),
    "ng": pg.image.load("assets/images/ng.png"),
    "ok": pg.image.load("assets/images/ok.png"),
    "good": pg.image.load("assets/images/good.png"),
    "great": pg.image.load("assets/images/great.png"),
}
images = {key: pg.transform.scale(image, (720, 720)) for key, image in images.items()}


async def websocket_session(queue: asyncio.Queue[ServerResponse], uri: str):
    async with websockets.connect(uri) as websocket:
        cap = cv2.VideoCapture(0)
        while True:

            ret, frame = cap.read()
            if not ret:
                print("Failed to capture image")
                break

            # 画像をBase64エンコードして送信
            _, buffer = cv2.imencode(".jpg", frame)
            encoded_image = base64.b64encode(buffer).decode("utf-8")
            await websocket.send(encoded_image)

            response = ServerResponse.from_json(await websocket.recv())
            queue.put_nowait(response)
            if response.status == ServerStatus.END:
                break
            # 0.2秒待機
            await asyncio.sleep(1 / FPS)

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


def draw_image(
    surface: pg.Surface,
    image: pg.Surface,
    left: int = None,
    top: int = None,
    right: int = None,
    bottom: int = None,
):
    if top is not None and left is not None:
        surface.blit(image, (left, top))
    elif top is not None and right is not None:
        rect = image.get_rect(topright=(right, top))
        surface.blit(image, rect.topleft)
    elif bottom is not None and left is not None:
        rect = image.get_rect(bottomleft=(left, bottom))
        surface.blit(image, rect.topleft)
    elif bottom is not None and right is not None:
        rect = image.get_rect(bottomright=(right, bottom))
        surface.blit(image, rect.topleft)


def draw_progress(
    surface: pg.Surface,
    progress: float,
):
    pg.draw.rect(
        surface,
        (200, 230, 210),
        (0, 0, SCREEN_SIZE[0] * progress, 50),
    )


class GamePhase(Enum):
    WAITING = "waiting"
    RUNNING = "running"
    RESULT = "result"


async def main(args):
    phase = GamePhase.WAITING
    result_countdown = 0
    last_response = None
    queue = asyncio.Queue()
    websocket_task = None

    running = True
    while running:
        # イベント処理
        for event in pg.event.get():
            # 共通
            if event.type == pg.QUIT:
                running = False
                break
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    running = False
                    break

            # 状態毎の処理
            if phase == GamePhase.WAITING:
                if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                    phase = GamePhase.RUNNING
                    websocket_task = asyncio.create_task(
                        websocket_session(queue, args.uri)
                    )
                    print("ゲーム開始")
            elif phase == GamePhase.RUNNING:
                if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                    # ここでは何もしない、ゲーム中はEnterキーでの操作は無視
                    pass
            elif phase == GamePhase.RESULT:
                if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
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
                elif response.status == ServerStatus.RECOGNIZED:
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
            draw_image(screen, images["wait"], left=0, bottom=SCREEN_SIZE[1])

        elif phase == GamePhase.RUNNING:
            if last_response is None:
                draw_text(screen, "カメラを起動中...", (150, 150), fonts[100])
                draw_image(screen, images["setup"], left=0, bottom=SCREEN_SIZE[1])

            elif last_response.status == ServerStatus.START:
                draw_text(screen, "顔認証中...", (150, 150), fonts[100])
                draw_image(screen, images["setup"], left=0, bottom=SCREEN_SIZE[1])

            elif last_response.status == ServerStatus.RECOGNIZED:
                name = last_response.name
                draw_text(screen, f"{name}さん、こんにちは！", (150, 150), fonts[100])
                draw_text(screen, "バーを持ってね〜！", (150, 400), fonts[150])
                draw_image(
                    screen, images["guide"], right=SCREEN_SIZE[0], bottom=SCREEN_SIZE[1]
                )

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
                    draw_image(
                        screen,
                        images["ng"],
                        right=SCREEN_SIZE[0],
                        bottom=SCREEN_SIZE[1],
                    )
                elif count < 10:
                    draw_image(
                        screen,
                        images["ok"],
                        right=SCREEN_SIZE[0],
                        bottom=SCREEN_SIZE[1],
                    )
                elif count < 20:
                    draw_image(
                        screen,
                        images["good"],
                        right=SCREEN_SIZE[0],
                        bottom=SCREEN_SIZE[1],
                    )
                else:
                    draw_image(
                        screen,
                        images["great"],
                        right=SCREEN_SIZE[0],
                        bottom=SCREEN_SIZE[1],
                    )

        elif phase == GamePhase.RESULT:
            name = last_response.name
            count = last_response.count
            draw_text(screen, f"結果", (150, 150), fonts[100])
            draw_text(screen, f"{name}さん、{count}回！！", (150, 400), fonts[150])
            if count < 5:
                draw_image(
                    screen, images["ng"], right=SCREEN_SIZE[0], bottom=SCREEN_SIZE[1]
                )
            elif count < 10:
                draw_image(
                    screen, images["ok"], right=SCREEN_SIZE[0], bottom=SCREEN_SIZE[1]
                )
            elif count < 20:
                draw_image(
                    screen, images["good"], right=SCREEN_SIZE[0], bottom=SCREEN_SIZE[1]
                )
            else:
                draw_image(
                    screen, images["great"], right=SCREEN_SIZE[0], bottom=SCREEN_SIZE[1]
                )

            if result_countdown > 0:
                draw_progress(
                    screen,
                    result_countdown / RESULT_DURATION,
                )

            print(f"name: {last_response.name}, Count: {last_response.count}")

        # 内部状態の処理
        if phase == GamePhase.RUNNING:
            if last_response and last_response.status == ServerStatus.END:
                phase = GamePhase.RESULT
                result_countdown = RESULT_DURATION

        elif phase == GamePhase.RESULT:
            if result_countdown > 0:
                result_countdown -= 1000 / FPS
            else:
                phase = GamePhase.WAITING
                last_response = None
                print("ゲームをリセット")

        pg.display.flip()
        await asyncio.sleep(1 / FPS)

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
