import cv2

import cv2

def detect_qr_code_coordinates(image_path):
    # 画像読み込み
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"画像が見つかりません: {image_path}")

    # QRコード検出器を作成
    qr_detector = cv2.QRCodeDetector()

    # QRコードのデコードとバウンディングボックス取得
    data, points, _ = qr_detector.detectAndDecode(image)

    if points is not None:
        # QRコードの四隅の座標を取得
        points = points[0]  # shape: (4, 2)
        coordinates = [(int(x), int(y)) for [x, y] in points]

        # 中心X座標と、Yの最小値（上部）を計算
        cx = int(sum(x for x, _ in coordinates) / 4)
        top_y = min(y for _, y in coordinates)

        print(f"QRコード内容: {data}")
        print(f"四隅の座標: {coordinates}")
        print(f"中心X, 上部Y: ({cx}, {top_y})")
        return cx, top_y
    else:
        print("QRコードが検出されませんでした。")
        return None, None