import argparse
import logging
import os
from enum import Enum, auto
from typing import Dict, Optional

import cv2
import dotenv
import numpy as np
import pygame as pg

import capture
import face
import pose

# ロガー設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 環境変数設定
dotenv.load_dotenv()
os.environ["GLOG_minloglevel"] = "2"


class Config:
    """設定値を管理するクラス"""

    SCREEN_SIZE = (1920, 1080)
    FPS = 5
    RESULT_DURATION_MS = 10000
    RECOGNIZING_TIMEOUT_MS = 10000
    COUNTING_TIMEOUT_MS = 2000

    # Colors
    TEXT_COLOR = (255, 255, 255)
    BACKGROUND_COLOR = (0, 0, 0)
    PROGRESS_BAR_COLOR = (200, 230, 210)
    FPS_COUNTER_COLOR = (255, 255, 0)

    # Pose estimation thresholds
    BAR_Y_COORDINATE = 0.3
    CHINUP_RESET_THRESHOLD = 0.2


class Assets:
    """フォント、画像、サウンドなどのリソースを管理するクラス"""

    def __init__(self):
        pg.mixer.init()
        font_path = pg.font.match_font("Noto Sans CJK JP")
        self.fonts = {
            size: pg.font.Font(font_path, size)
            for size in [50, 100, 150, 200, 250, 300]
        }
        self.sounds = self._load_sounds()
        self.images = self._load_images()

    def _load_sounds(self) -> Dict[str, pg.mixer.Sound]:
        return {
            "entry": pg.mixer.Sound("assets/sounds/entry.wav"),
            "count": pg.mixer.Sound("assets/sounds/coin.mp3"),
        }

    def _load_images(self) -> Dict[str, pg.Surface]:
        image_files = {
            "wait": "assets/images/wait.png",
            "setup": "assets/images/setup.png",
            "guide": "assets/images/guide.png",
            "ng": "assets/images/ng.png",
            "ok": "assets/images/ok.png",
            "good": "assets/images/good.png",
            "great": "assets/images/great.png",
        }
        images = {key: pg.image.load(path) for key, path in image_files.items()}
        return {key: pg.transform.scale(img, (720, 720)) for key, img in images.items()}

    def get_rank_image(self, count: int) -> pg.Surface:
        if count >= 20:
            return self.images["great"]
        if count >= 10:
            return self.images["good"]
        if count >= 5:
            return self.images["ok"]
        return self.images["ng"]


class State:
    """ゲームの状態を管理するデータクラス"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.count: int = 0
        self.name: Optional[str] = None
        self.chinuped: bool = False
        self.timers = {
            "recognizing": Config.RECOGNIZING_TIMEOUT_MS,
            "counting": Config.COUNTING_TIMEOUT_MS,
            "result": Config.RESULT_DURATION_MS,
        }

    def reset_timer(self, name: str):
        self.timers[name] = getattr(Config, f"{name.upper()}_TIMEOUT_MS", 0)


class GamePhase(Enum):
    IDLE = auto()
    RECOGNIZING = auto()
    WAITING_HANDS = auto()
    COUNTING = auto()
    RESULT = auto()


class Phase:
    """各ゲームフェーズの基底クラス"""

    def __init__(self, game: "Game"):
        self.game = game
        self.state = game.state
        self.assets = game.assets
        self.screen = game.screen
        self.debug = game.debug

    def handle_event(self, event: pg.event.Event) -> Optional["Phase"]:
        return None

    def update(self, dt: int) -> Optional["Phase"]:
        return self

    def draw(self):
        pass

    def _draw_text(self, text, pos, size, color=Config.TEXT_COLOR):
        font = self.assets.fonts.get(size)
        if font:
            text_surface = font.render(text, True, color)
            self.screen.blit(text_surface, pos)

    def _draw_image(self, image_key, **kwargs):
        image = self.assets.images[image_key]
        rect = image.get_rect(**kwargs)
        self.screen.blit(image, rect)

    def _draw_camera_with_landmarks(self):
        if not self.debug:
            return
        frame = capture.read_rgb()
        if frame is None:
            return

        pose_result = pose.detect_pose(frame)

        # ランドマークを描画
        if pose_result:
            points_to_draw = []
            if pose_result.nose:
                points_to_draw.append((pose_result.nose, (0, 255, 0)))
            if pose_result.left_hand:
                points_to_draw.append((pose_result.left_hand, (255, 0, 0)))
            if pose_result.right_hand:
                points_to_draw.append((pose_result.right_hand, (0, 0, 255)))

            for (x, y), color in points_to_draw:
                center = (int(x * frame.shape[1]), int(y * frame.shape[0]))
                cv2.circle(frame, center, 10, color, -1)

        # Pygame用に変換して描画
        frame = np.rot90(frame)
        surface = pg.surfarray.make_surface(frame)
        self.screen.blit(surface, (Config.SCREEN_SIZE[0] - surface.get_width(), 0))


class IdlePhase(Phase):
    def handle_event(self, event: pg.event.Event):
        if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
            capture.open()
            self.assets.sounds["entry"].play()
            logger.info("Game started. -> Recognizing phase")
            return RecognizingPhase(self.game)
        return None

    def draw(self):
        self._draw_text("待機中...", (150, 150), 100)
        self._draw_text("Enterでスタート！！", (150, 400), 100)
        self._draw_image("wait", bottomleft=(0, Config.SCREEN_SIZE[1]))


class RecognizingPhase(Phase):
    def update(self, dt: int):
        self.state.timers["recognizing"] -= dt
        if self.state.timers["recognizing"] <= 0:
            logger.info("Recognition failed, returning to idle.")
            return IdlePhase(self.game)

        frame = capture.read_rgb()
        if frame is None:
            return self

        names = face.recognize_face_names(frame)
        if len(names) == 1:
            self.state.name = names[0]
            logger.info(f"Recognized: {self.state.name}")
            self.assets.sounds["entry"].play()
            return WaitingHandsPhase(self.game)
        elif len(names) > 1:
            logger.warning(f"Multiple faces recognized: {names}")

        return self

    def draw(self):
        self._draw_text("顔認証中...", (150, 150), 100)
        self._draw_image("setup", bottomleft=(0, Config.SCREEN_SIZE[1]))
        progress = self.state.timers["recognizing"] / Config.RECOGNIZING_TIMEOUT_MS
        pg.draw.rect(
            self.screen,
            Config.PROGRESS_BAR_COLOR,
            (0, 0, Config.SCREEN_SIZE[0] * progress, 50),
        )


class WaitingHandsPhase(Phase):
    def update(self, dt: int):
        frame = capture.read_rgb()
        if frame is None:
            return self  # or IdlePhase

        pose_result = pose.detect_pose(frame)
        if pose_result and pose_result.left_hand and pose_result.right_hand:
            if (
                pose_result.left_hand[1] <= Config.BAR_Y_COORDINATE
                and pose_result.right_hand[1] <= Config.BAR_Y_COORDINATE
            ):
                logger.info("Hands detected, starting count.")
                self.assets.sounds["entry"].play()
                return CountingPhase(self.game)
        return self

    def draw(self):
        self._draw_text("バーを持ってね〜！", (150, 150), 100)
        self._draw_image("guide", bottomright=Config.SCREEN_SIZE)
        self._draw_camera_with_landmarks()


class CountingPhase(Phase):
    def update(self, dt: int):
        frame = capture.read_rgb()
        if frame is None:
            return ResultPhase(self.game)

        pose_result = pose.detect_pose(frame)

        if (
            not (
                pose_result
                and pose_result.nose
                and pose_result.left_hand
                and pose_result.right_hand
            )
            or pose_result.left_hand[1] > Config.BAR_Y_COORDINATE
            or pose_result.right_hand[1] > Config.BAR_Y_COORDINATE
        ):
            self.state.timers["counting"] -= dt
            if self.state.timers["counting"] <= 0:
                return ResultPhase(self.game)
        else:
            self.state.reset_timer("counting")
            # 顔がバーを越えたらカウント
            if (
                pose_result.nose[1] <= Config.BAR_Y_COORDINATE
                and not self.state.chinuped
            ):
                self.state.chinuped = True
                self.state.count += 1
                self.assets.sounds["count"].play()
                logger.info(f"Count incremented: {self.state.count}")
            # 顔が一定以上下がったらリセット
            if (
                pose_result.nose[1]
                > Config.BAR_Y_COORDINATE + Config.CHINUP_RESET_THRESHOLD
            ):
                self.state.chinuped = False
        return self

    def draw(self):
        self._draw_text("カウント中...", (150, 150), 100)
        self._draw_text(
            f"{self.state.name}さん、{self.state.count}回！！", (150, 400), 150
        )
        image = self.assets.get_rank_image(self.state.count)
        rect = image.get_rect(bottomright=Config.SCREEN_SIZE)
        self.screen.blit(image, rect)
        self._draw_camera_with_landmarks()


class ResultPhase(Phase):
    def __init__(self, game: "Game"):
        super().__init__(game)
        capture.release()

    def handle_event(self, event: pg.event.Event):
        if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
            logger.info("Game ended. -> Idle phase")
            return IdlePhase(self.game)
        return None

    def update(self, dt: int):
        self.state.timers["result"] -= dt
        if self.state.timers["result"] <= 0:
            logger.info("Result phase ended, returning to idle state.")
            return IdlePhase(self.game)
        return self

    def draw(self):
        self._draw_text("結果", (150, 150), 100)
        self._draw_text(
            f"{self.state.name}さん、{self.state.count}回！！", (150, 400), 150
        )
        image = self.assets.get_rank_image(self.state.count)
        rect = image.get_rect(bottomright=Config.SCREEN_SIZE)
        self.screen.blit(image, rect)
        progress = self.state.timers["result"] / Config.RESULT_DURATION_MS
        pg.draw.rect(
            self.screen,
            Config.PROGRESS_BAR_COLOR,
            (0, 0, Config.SCREEN_SIZE[0] * progress, 50),
        )


class Game:
    """ゲーム全体の管理とメインループを実行するクラス"""

    def __init__(self, args):
        pg.init()
        self.screen = pg.display.set_mode(
            Config.SCREEN_SIZE,
            pg.RESIZABLE if args.resizable else pg.FULLSCREEN,
        )
        pg.display.set_caption("kensuiou")
        self.clock = pg.time.Clock()
        self.assets = Assets()
        self.state = State()
        self.debug = args.debug
        self.current_phase: Phase = IdlePhase(self)

        # 外部モジュールの初期化
        face.init(args.face_feature)
        pose.init(args.pose_model_complexity)
        capture.init(args.capture_width, args.capture_height)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(Config.FPS)

            for event in pg.event.get():
                if event.type == pg.QUIT or (
                    event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE
                ):
                    running = False

                next_phase = self.current_phase.handle_event(event)
                if next_phase:
                    self.current_phase = next_phase
                    if isinstance(self.current_phase, IdlePhase):
                        self.state.reset()

            next_phase = self.current_phase.update(dt)
            if next_phase is not self.current_phase:
                self.current_phase = next_phase
                if isinstance(self.current_phase, IdlePhase):
                    self.state.reset()

            self.screen.fill(Config.BACKGROUND_COLOR)
            self.current_phase.draw()
            if self.debug:
                self._draw_fps()
            pg.display.flip()

        self._cleanup()

    def _draw_fps(self):
        font = self.assets.fonts[50]
        fps_text = f"FPS: {int(self.clock.get_fps())}"
        text_surface = font.render(fps_text, True, Config.FPS_COUNTER_COLOR)
        self.screen.blit(text_surface, (10, 10))

    def _cleanup(self):
        logger.info("Exiting game loop, releasing resources.")
        capture.release()
        pg.quit()


def main():
    parser = argparse.ArgumentParser(description="Local Kensuiou Application")
    parser.add_argument(
        "--face-feature", type=str, default="assets/models/face_features.json"
    )
    parser.add_argument(
        "--pose-model-complexity", choices=[0, 1, 2], type=int, default=0
    )
    parser.add_argument("--capture-width", type=int, default=640)
    parser.add_argument("--capture-height", type=int, default=480)
    parser.add_argument("--resizable", action="store_true")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    game = Game(args)
    game.run()


if __name__ == "__main__":
    main()
