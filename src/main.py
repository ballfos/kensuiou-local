import argparse
import logging
import os
from enum import Enum

import cv2
import dotenv
import numpy as np
import pygame as pg

import capture
import face
import pose

# ログの設定
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

os.environ["GLOG_minloglevel"] = "2"
# 環境変数の読み込み
dotenv.load_dotenv()
Y_RATIO = float(os.getenv("Y_RATIO", 0.5))
X_RIGHT_RATIO = float(os.getenv("X_RIGHT_RATIO", 0.6))
X_REFT_RATIO = float(os.getenv("X_REFT_RATIO", 0.4))

# 画像保存ディレクトリ (一時的な画像保存用)
SAVE_PATH = "temp_images"
os.makedirs(SAVE_PATH, exist_ok=True)

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
    50: pg.font.Font(font_path, 50),
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
    IDLE = "idle"
    RECOGNIZING = "recognizing"
    WAITING_HANDS = "waiting_hands"
    COUNTING = "counting"
    RESULT = "result"


def main(args):
    state = GamePhase.IDLE
    count = 0
    name = None
    result_countdown = 0
    recognizing_countdown = 0
    counting_countdown = 0
    chinuped = False
    clock = pg.time.Clock()

    bar_y_coordinate = 0.3

    face.init(args.face_feature)
    pose.init(args.pose_model_complexity)
    capture.init(args.capture_width, args.capture_height)

    running = True
    while running:
        clock.tick(FPS)

        # =========================
        # イベント処理
        # =========================
        for event in pg.event.get():
            if event.type == pg.QUIT or (
                event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE
            ):
                running = False
                break

            if state == GamePhase.IDLE:
                if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                    state = GamePhase.RECOGNIZING
                    recognizing_countdown = 3000
                    capture.open()
                    logger.info("Game started. -> Recognizing phase")
                    sounds["entry"].play()

            elif state == GamePhase.RESULT:
                if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                    state = GamePhase.IDLE
                    logger.info("Game ended. -> Idle phase")

        # =========================
        # ロジック処理
        # =========================
        if state == GamePhase.RECOGNIZING:
            frame = capture.read_rgb()
            names = face.recognize_face_names(frame)
            if len(names) == 1:
                name = names[0]
                count = 0
                state = GamePhase.WAITING_HANDS
                logger.info(f"Recognized: {name}")
                sounds["entry"].play()
            elif len(names) > 1:
                logger.warning(f"Multiple faces recognized: {names}")
            else:
                recognizing_countdown -= 1000 / FPS
                if recognizing_countdown <= 0:
                    state = GamePhase.IDLE
                    logger.info("Recognition failed, returning to idle state.")

        elif state == GamePhase.WAITING_HANDS:
            frame = capture.read_rgb()
            pose_result = pose.detect_pose(frame)
            # 両手のy座標がバーのy座標以下ならカウント開始
            if pose_result.left_hand and pose_result.right_hand:
                if (
                    pose_result.left_hand[1] <= bar_y_coordinate
                    and pose_result.right_hand[1] <= bar_y_coordinate
                ):
                    state = GamePhase.COUNTING
                    counting_countdown = 1000
                    sounds["entry"].play()
                    logger.info("Hands detected, starting count.")

        elif state == GamePhase.COUNTING:
            frame = capture.read_rgb()
            pose_result = pose.detect_pose(frame)
            if pose_result.nose and pose_result.left_hand and pose_result.right_hand:
                # 顔のy座標がバーのy座標以下ならカウント
                if pose_result.nose[1] <= bar_y_coordinate and not chinuped:
                    chinuped = True
                    count += 1
                    sounds["count"].play()
                    logger.info(f"Count incremented: {count}")

                # 一定時間顔がバーより下にある場合、カウント可能状態に戻す
                if pose_result.nose[1] > bar_y_coordinate + 0.2:
                    chinuped = False
                    logger.info("Face below bar, ready for next count.")

            if (
                pose_result.nose is None
                or pose_result.left_hand is None
                or pose_result.right_hand is None
                or pose_result.left_hand[1] > bar_y_coordinate
                or pose_result.right_hand[1] > bar_y_coordinate
            ):
                counting_countdown -= 1000 / FPS
                if counting_countdown <= 0:
                    state = GamePhase.RESULT
                    result_countdown = RESULT_DURATION
                    capture.release()
            else:
                counting_countdown = 1000

        elif state == GamePhase.RESULT:
            result_countdown -= 1000 / FPS
            if result_countdown <= 0:
                state = GamePhase.IDLE
                logger.info("Result phase ended, returning to idle state.")
                name = None
                count = 0

        # =========================
        # 描画処理
        # =========================
        screen.fill(BACKGROUND_COLOR)

        # FPS表示
        draw_text(
            screen,
            f"FPS: {int(clock.get_fps())}",
            (10, 10),
            fonts[100],
            color=(255, 255, 0),
        )

        if state == GamePhase.IDLE:
            draw_text(screen, "待機中...", (150, 150), fonts[100])
            draw_text(screen, "Enterでスタート！！", (150, 400), fonts[100])
            draw_image(screen, images["wait"], left=0, bottom=SCREEN_SIZE[1])

        elif state == GamePhase.RECOGNIZING:
            draw_text(screen, "顔認証中...", (150, 150), fonts[100])
            draw_image(screen, images["setup"], left=0, bottom=SCREEN_SIZE[1])

            if recognizing_countdown > 0:
                draw_progress(screen, recognizing_countdown / 3000)

        elif state == GamePhase.WAITING_HANDS:
            draw_text(screen, "バーを持ってね〜！", (150, 150), fonts[100])
            draw_image(
                screen, images["guide"], right=SCREEN_SIZE[0], bottom=SCREEN_SIZE[1]
            )

            # frameの表示
            frame = capture.read_rgb()
            pose_result = pose.detect_pose(frame)
            frame = cv2.circle(
                frame,
                (
                    int(pose_result.nose[0] * frame.shape[1]),
                    int(pose_result.nose[1] * frame.shape[0]),
                ),
                10,
                (0, 255, 0),
                -1,
            )
            frame = cv2.circle(
                frame,
                (
                    int(pose_result.left_hand[0] * frame.shape[1]),
                    int(pose_result.left_hand[1] * frame.shape[0]),
                ),
                10,
                (255, 0, 0),
                -1,
            )
            frame = cv2.circle(
                frame,
                (
                    int(pose_result.right_hand[0] * frame.shape[1]),
                    int(pose_result.right_hand[1] * frame.shape[0]),
                ),
                10,
                (0, 0, 255),
                -1,
            )
            frame = np.rot90(frame)
            surface = pg.surfarray.make_surface(frame)
            screen.blit(surface, (0, 0))

        elif state == GamePhase.COUNTING:
            draw_text(screen, "カウント中...", (150, 150), fonts[100])
            draw_text(screen, f"{name}さん、{count}回！！", (150, 400), fonts[150])

            img_key = (
                "great"
                if count >= 20
                else "good"
                if count >= 10
                else "ok"
                if count >= 5
                else "ng"
            )
            draw_image(
                screen, images[img_key], right=SCREEN_SIZE[0], bottom=SCREEN_SIZE[1]
            )

            # frameの表示
            frame = capture.read_rgb()
            pose_result = pose.detect_pose(frame)
            frame = cv2.circle(
                frame,
                (
                    int(pose_result.nose[0] * frame.shape[1]),
                    int(pose_result.nose[1] * frame.shape[0]),
                ),
                10,
                (0, 255, 0),
                -1,
            )
            frame = cv2.circle(
                frame,
                (
                    int(pose_result.left_hand[0] * frame.shape[1]),
                    int(pose_result.left_hand[1] * frame.shape[0]),
                ),
                10,
                (255, 0, 0),
                -1,
            )
            frame = cv2.circle(
                frame,
                (
                    int(pose_result.right_hand[0] * frame.shape[1]),
                    int(pose_result.right_hand[1] * frame.shape[0]),
                ),
                10,
                (0, 0, 255),
                -1,
            )
            frame = np.rot90(frame)
            surface = pg.surfarray.make_surface(frame)
            screen.blit(surface, (0, 0))

        elif state == GamePhase.RESULT:
            draw_text(screen, "結果", (150, 150), fonts[100])
            draw_text(screen, f"{name}さん、{count}回！！", (150, 400), fonts[150])

            img_key = (
                "great"
                if count >= 20
                else "good"
                if count >= 10
                else "ok"
                if count >= 5
                else "ng"
            )
            draw_image(
                screen, images[img_key], right=SCREEN_SIZE[0], bottom=SCREEN_SIZE[1]
            )

            if result_countdown > 0:
                draw_progress(screen, result_countdown / RESULT_DURATION)

        pg.display.flip()

    logger.info("Exiting game loop, releasing resources.")
    capture.release()
    pg.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local Kensuiou Application")
    parser.add_argument(
        "--face-feature",
        type=str,
        default="assets/models/face_features.json",
        help="Path to face features file",
    )
    parser.add_argument(
        "--pose-model-complexity",
        choices=[0, 1, 2],
        type=int,
        default=0,
        help="Model complexity for pose detection (0: Lite, 1: Full, 2: Heavy)",
    )
    parser.add_argument(
        "--capture-width",
        type=int,
        default=640,
        help="Width of the video capture",
    )
    parser.add_argument(
        "--capture-height",
        type=int,
        default=480,
        help="Height of the video capture",
    )

    args = parser.parse_args()

    main(args)
