import logging

import cv2

logger = logging.getLogger(__name__)

PATTERN_SIZE = (3, 3)


def detect_chessboard_center(frame: cv2.Mat) -> tuple[float, float] | None:
    """
    frameに含まれるチェスボードの中心座標を割合で返す
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    ret, corners = cv2.findChessboardCorners(gray, PATTERN_SIZE, None)

    if not ret:
        logger.debug("failed to detect chessboard corners")
        return None

    # チェスボードの中心を計算
    center = corners.mean(axis=0)[0]
    height, width, _ = frame.shape
    return (center[0] / width, center[1] / height)


if __name__ == "__main__":
    """動作テスト"""
    import sys
    import time

    logging.basicConfig(level=logging.DEBUG)

    cap = cv2.VideoCapture(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
    if not cap.isOpened():
        logger.error("Could not open video capture")
        exit(1)
    while True:
        ret, frame = cap.read()
        if not ret:
            logger.error("Failed to read frame from video capture")
            exit(1)
        frame = cv2.resize(frame, (640, 480))
        cv2.imwrite("test_frame.jpg", frame)
        start_time = time.time()
        center = detect_chessboard_center(frame)
        elapsed_time = time.time() - start_time
        logger.info(f"Chessboard detection took {elapsed_time:.2f} seconds")

        if center:
            logger.info(f"Chessboard center: {center}")
        else:
            logger.info("Chessboard not detected")
        cv2.imshow("Chessboard Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
