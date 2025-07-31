"""
体の位置情報の中から必要な情報を抽出

抽出する情報：
- 鼻
- 左手首
- 右手首
"""

import logging
import time
from dataclasses import dataclass

import cv2
from mediapipe.python.solutions import pose as mp_pose

logger = logging.getLogger(__name__)


@dataclass
class PoseDetectionResult:
    nose: tuple[float, float] | None
    left_hand: tuple[float, float] | None
    right_hand: tuple[float, float] | None


pose = None


def init(model_complexity: int = 0) -> None:
    global pose
    pose = mp_pose.Pose(static_image_mode=True, model_complexity=model_complexity)


def detect_pose(frame: cv2.Mat) -> PoseDetectionResult:
    results = pose.process(frame)
    if results.pose_landmarks:
        nose = results.pose_landmarks.landmark[mp_pose.PoseLandmark.NOSE]
        left_hand = results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST]
        right_hand = results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST]
        return PoseDetectionResult(
            nose=(nose.x, nose.y) if nose else None,
            left_hand=(left_hand.x, left_hand.y) if left_hand else None,
            right_hand=(right_hand.x, right_hand.y) if right_hand else None,
        )
    else:
        return PoseDetectionResult(nose=None, left_hand=None, right_hand=None)


if __name__ == "__main__":
    """動作テスト"""
    import sys
    import time

    import cv2

    logging.basicConfig(level=logging.INFO)

    cap = cv2.VideoCapture(sys.argv[1] if len(sys.argv) > 1 else 0)
    if not cap.isOpened():
        logger.error("Could not open video capture")
        exit(1)

    init()

    while True:
        start_time = time.time()

        ret, frame = cap.read()
        if not ret:
            logger.error("Failed to read frame from camera")
            break
        frame = cv2.resize(frame, (0, 0), fx=0.3, fy=0.3)

        result = detect_pose(frame)
        logging.info(f"Detection result: {result}")

        elapsed_time = time.time() - start_time
        logger.info(f"Frame processed in {elapsed_time:.2f} seconds")

        cv2.imshow("Position Detection", frame)

        time.sleep(0.1)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    pose.close()
    cv2.destroyAllWindows()
