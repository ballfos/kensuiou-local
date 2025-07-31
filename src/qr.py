import logging

import cv2

logger = logging.getLogger(__name__)

qr_detector = None


def init():
    global qr_detector
    # QRコード検出器を初期化
    qr_detector = cv2.QRCodeDetector()


def detect_qr_code_center(frame: cv2.Mat) -> tuple[float, float] | None:
    """
    frameに含まれるQRCodeの中心座標を割合で返す
    """
    _, points = qr_detector.detect(frame)
    if points is None:
        logger.debug("failed to detect QR code")
        return None

    center = points.mean(axis=0)[0]
    height, width, _ = frame.shape
    return (center[0] / width, center[1] / height)


if __name__ == "__main__":
    """動作テスト"""
    import sys
    import time

    logging.basicConfig(level=logging.INFO)

    cap = cv2.VideoCapture(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
    if not cap.isOpened():
        logger.error("Could not open video capture")
        exit(1)

    init()

    ret, frame = cap.read()
    if not ret:
        logger.error("Failed to read frame from video capture")
        exit(1)
    frame = cv2.resize(frame, (640, 480))
    cv2.imwrite("test_frame.jpg", frame)
    start_time = time.time()
    center = detect_qr_code_center(frame)
    elapsed_time = time.time() - start_time
    logger.info(f"QR Code detection took {elapsed_time:.2f} seconds")

    if center:
        logger.info(f"QR Code center: {center}")
    else:
        logger.info("QR Code not detected")


# def detect_qr_code_coordinates(image_path):
#     # 画像読み込み
#     image = cv2.imread(image_path)
#     if image is None:
#         raise FileNotFoundError(f"画像が見つかりません: {image_path}")

#     # QRコード検出器を作成
#     qr_detector = cv2.QRCodeDetector()

#     # QRコードのデコードとバウンディングボックス取得
#     data, points, _ = qr_detector.detectAndDecode(image)

#     if points is not None:
#         # QRコードの四隅の座標を取得
#         points = points[0]  # shape: (4, 2)
#         coordinates = [(int(x), int(y)) for [x, y] in points]

#         # 中心X座標と、Yの最小値（上部）を計算
#         cx = int(sum(x for x, _ in coordinates) / 4)
#         top_y = min(y for _, y in coordinates)

#         return cx, top_y
#     else:
#         print("QRコードが検出されませんでした。")
#         return None, None#         return None, None#         return None, None
