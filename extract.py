import face_recognition
import numpy as np
import json

def identify_person(image_path,  threshold=0.6):

    face_features_json = "face_features.json"  # 既存の顔データが保存されているJSONファイル
    # 既存の顔データをロード
    with open(face_features_json, "r") as f:
        known_faces = json.load(f)

    known_encodings = [np.array(face["encoding"]) for face in known_faces]
    known_names = [face["name"] for face in known_faces]

    # 入力画像を読み込み、顔のエンコーディングを抽出
    image = face_recognition.load_image_file(image_path)
    face_encodings = face_recognition.face_encodings(image)

    if len(face_encodings) == 0:
        return "none"

    # 入力画像に含まれる最初の顔で判定
    input_encoding = face_encodings[0]
    distances = face_recognition.face_distance(known_encodings, input_encoding)
    
    # 最も近い顔のインデックスを取得
    best_match_index = np.argmin(distances)

    # 閾値以下であれば名前を返し、超えていれば "guest" を返す
    if distances[best_match_index] <= threshold:
        return known_names[best_match_index]
    else:
        return "none"

def detect_objects_and_get_centers(model,image_path):
    import cv2
    import numpy as np

    # 画像を読み込む
    frame = cv2.imread(image_path)
    if frame is None:
        raise FileNotFoundError(f"Image not found: {image_path}")

    # BGR画像をRGBに変換
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # 推論を実行
    results = model(rgb_frame)

    # 検出結果を取得
    detections = results.xyxy[0].cpu().numpy()
    
    # クラスIDに対応するラベルを定義
    class_labels = {0: "Face", 1: "Hand"}

    # 結果を格納する辞書
    centers = {"hand": [], "face": []}

    # 閾値を適用してフィルタリング
    conf_threshold = 0.1  # 信頼度の閾値
    for det in detections:
        x1, y1, x2, y2, conf, cls = det
        if conf >= conf_threshold:
            class_id = int(cls)
            label = class_labels.get(class_id)
            if label:
                # 中心座標を計算
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                centers[label.lower()].append((cx, cy))

    # x座標でhandのリストをソート（大きい順）
    centers["hand"].sort(key=lambda coord: coord[0], reverse=True)

    return centers