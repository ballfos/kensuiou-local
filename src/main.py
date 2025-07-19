import argparse
import asyncio
import base64
import json
import os

from dataclasses import dataclass
from enum import Enum

import cv2
import dotenv
import pygame as pg
import torch
# from db import get_nickname, register_record
from predict import detect_objects_and_get_centers,identify_person
from qr import detect_qr_code_coordinates
os.environ['GLOG_minloglevel'] = '2'
# 環境変数の読み込み
dotenv.load_dotenv()
Y_RATIO = float(os.getenv("Y_RATIO", 0.5))
X_RIGHT_RATIO = float(os.getenv("X_RIGHT_RATIO", 0.6))
X_REFT_RATIO = float(os.getenv("X_REFT_RATIO", 0.4))

# 画像保存ディレクトリ (一時的な画像保存用)
SAVE_PATH = "temp_images"
os.makedirs(SAVE_PATH, exist_ok=True)


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


TEXT_COLOR = (255, 255, 255)
BACKGROUND_COLOR = (0, 0, 0)
SCREEN_SIZE = (1920, 1080)
RESULT_DURATION = 7000
FPS = 5

pg.init()
pg.mixer.init()
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


async def local_game_logic(queue: asyncio.Queue,face_features_path):
    """
    カメラから映像を取得し、顔認証、物体検出、カウント処理をローカルで行う。
    サーバーの`handler`関数のロジックを移植。
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("エラー: カメラを開けませんでした。")
        return

    # 状態変数の初期化
    status = "start"
    name = None
    nickname = None
    count = 0
    hand_flg = 1
    get_size_flg = True
    bar_x_reft = 0
    bar_y_coordinate = 0
    wide = False

    while True:
        ret, frame = cap.read()
        if not ret:
            print("エラー: フレームをキャプチャできませんでした。")
            break

      
        file_path = os.path.join(SAVE_PATH, "current_frame.jpg")
        cv2.imwrite(file_path, frame)

        # 初回フレームで座標の閾値を計算
        if get_size_flg:
            bar_y_coordinate, bar_x_reft = detect_qr_code_coordinates(file_path)
            if bar_y_coordinate is None or bar_x_reft is None:
                bar_y_coordinate = frame.shape[0] * Y_RATIO
                bar_x_reft = frame.shape[1] * X_REFT_RATIO
  
            get_size_flg = False

        # --- 状態ごとの処理 ---
        if status == "start":
            name = identify_person(file_path, face_features_path)
            if name is not None:
                status = "Authenticated"
                nickname ="test man"    #get_nickname(name)
                print(f"認証成功: {nickname}")

        elif status == "Authenticated":
            centers = detect_objects_and_get_centers(file_path)

            # 両手が検出され、かつ初期位置より上にあるか
            if centers["lefthand"] and centers["lefthand"]:
                left_y = centers["lefthand"][1]
                right_y = centers["righthand"][1]

                if left_y <= bar_y_coordinate and right_y <= bar_y_coordinate:
                    status = "Counting"

                    # 手のx座標がバーの範囲外なら wide = True
                    left_x = centers["lefthand"][0]
                    right_x = centers["righthand"][0]

                    if left_x <= bar_x_reft :
                        wide = False
                    else:
                        wide = True

                    print("カウント開始")

        elif status == "Counting":
            centers = detect_objects_and_get_centers(file_path)
            
            # 手が2つ検出されない、またはバーより下に手を下ろした場合、カウント終了
            if (not centers["lefthand"] and not centers["lefthand"]) or (centers["lefthand"][1] > bar_y_coordinate and centers["righthand"][1] > bar_y_coordinate):
                status = "end"
                print("カウント終了条件")
            
            # 顔が検出された場合のみカウント処理
            elif "face" in centers and len(centers["face"]) > 0:
                if hand_flg == 1:                   
                    # 頭がバーより上にきたらカウント
                    if centers["face"][1] <= bar_y_coordinate:
                        hand_flg = 0
                        count += 1
                        print(f"カウント: {count}")
                
                elif hand_flg == 0:
                    # 一定以上頭を下げたら、次のカウントができるようにフラグを戻す
                    if centers["face"][1] > bar_y_coordinate + 100:
                        print("手を下げたのでカウント可能")
                        hand_flg = 1

        # レスポンスを生成してUIスレッドに送信
        current_status = ServerStatus(status)
        response = ServerResponse(status=current_status, name=nickname, count=count)
        await queue.put(response)

        # 終了状態ならループを抜ける
        if status == "end":
            print(f"最終結果 - Player: {nickname}, Count: {count}, Wide: {wide}")
            break

        await asyncio.sleep(1 / FPS)

    cap.release()
    print("カメラを解放しました。")


def draw_text(surface, text, pos, font, color=TEXT_COLOR, background=None):
    text_surface = font.render(text, True, color, background)
    surface.blit(text_surface, pos)

def draw_image(surface, image, left=None, top=None, right=None, bottom=None):
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

def draw_progress(surface, progress):
    pg.draw.rect(surface, (200, 230, 210), (0, 0, SCREEN_SIZE[0] * progress, 50))

class GamePhase(Enum):
    WAITING = "waiting"
    RUNNING = "running"
    RESULT = "result"


async def main(args):
    # モデルの読み込み

    phase = GamePhase.WAITING
    result_countdown = 0
    last_response = None
    queue = asyncio.Queue()
    processing_task = None

    running = True
    while running:
        # イベント処理
        for event in pg.event.get():
            if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                running = False
                break
            
            if phase == GamePhase.WAITING:
                if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                    phase = GamePhase.RUNNING
                    processing_task = asyncio.create_task(
                        local_game_logic(queue,  args.face_feature)
                    )
                    print("ゲーム開始")
            elif phase == GamePhase.RESULT:
                if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                    phase = GamePhase.WAITING
                    last_response = None
                    print("待機画面に戻ります。")

        # キューからのメッセージ処理
        try:
            response = queue.get_nowait()
            if response and (last_response is None or response != last_response):
                if response.status != last_response.status if last_response else True:
                     if response.status == ServerStatus.RECOGNIZED: sounds["entry"].play()
                if response.status == ServerStatus.COUNTING and (response.count != last_response.count if last_response else False):
                    sounds["count"].play()

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
                draw_image(screen, images["guide"], right=SCREEN_SIZE[0], bottom=SCREEN_SIZE[1])
            elif last_response.status == ServerStatus.COUNTING:
                name = last_response.name
                count = last_response.count
                if count == 0:
                    draw_text(screen, f"{name}さん、スタート！！！", (150, 150), fonts[100])
                else:
                    draw_text(screen, f"{name}さん、{count}回！！", (150, 150), fonts[100])
                
                # 回数に応じた画像の表示
                img_key = "great" if count >= 20 else "good" if count >= 10 else "ok" if count >= 5 else "ng"
                draw_image(screen, images[img_key], right=SCREEN_SIZE[0], bottom=SCREEN_SIZE[1])


        elif phase == GamePhase.RESULT:
            name = last_response.name
            count = last_response.count
            draw_text(screen, f"結果", (150, 150), fonts[100])
            draw_text(screen, f"{name}さん、{count}回！！", (150, 400), fonts[150])

            img_key = "great" if count >= 20 else "good" if count >= 10 else "ok" if count >= 5 else "ng"
            draw_image(screen, images[img_key], right=SCREEN_SIZE[0], bottom=SCREEN_SIZE[1])

            if result_countdown > 0:
                draw_progress(screen, result_countdown / RESULT_DURATION)

        # 状態遷移
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
                print("待機画面に戻ります。")

        pg.display.flip()
        await asyncio.sleep(1 / FPS)

    print("終了します")
    if processing_task:
        processing_task.cancel()
    pg.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local Kensuiou Application")
    parser.add_argument("--face-feature", type=str, default="models/face_features.json", help="Path to face features file")
    args = parser.parse_args()
    
    asyncio.run(main(args))