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
        return "guest"
