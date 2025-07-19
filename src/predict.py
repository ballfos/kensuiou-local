import json
import cv2
import mediapipe as mp
# import face_recognition
mp_pose = mp.solutions.pose

def detect_objects_and_get_centers(image_path):
    # 画像を読み込む
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image not found: {image_path}")

    # BGR → RGB に変換
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # 出力用辞書
    keypoints = {"face": None, "lefthand": None, "righthand": None}

    with mp_pose.Pose(static_image_mode=True, model_complexity=1) as pose:
        results = pose.process(rgb_image)

        if results.pose_landmarks:
            h, w, _ = image.shape
            landmarks = results.pose_landmarks.landmark

            # 各ランドマークを取得
            nose = landmarks[0]  # face
            left_wrist = landmarks[15]  # lefthand
            right_wrist = landmarks[16]  # righthand

            keypoints["face"] = (int(nose.x * w), int(nose.y * h))
            keypoints["lefthand"] = (int(left_wrist.x * w), int(left_wrist.y * h))
            keypoints["righthand"] = (int(right_wrist.x * w), int(right_wrist.y * h))
    print(keypoints)

    return keypoints


def identify_person(image_path, face_features_path, threshold=0.6):
    return "tester"
    # # 既存の顔データをロード
    # with open(face_features_path, "r") as f:
    #     known_faces = json.load(f)

    # known_encodings = [np.array(face["encoding"]) for face in known_faces]
    # known_names = [face["name"] for face in known_faces]

    # # 入力画像を読み込み、顔のエンコーディングを抽出
    # image = face_recognition.load_image_file(image_path)
    # face_encodings = face_recognition.face_encodings(image)

    # if len(face_encodings) == 0:
    #     return None

    # # 入力画像に含まれる最初の顔で判定
    # input_encoding = face_encodings[0]
    # distances = face_recognition.face_distance(known_encodings, input_encoding)

    # # 最も近い顔のインデックスを取得
    # best_match_index = np.argmin(distances)

    # # 閾値以下であれば名前を返し、超えていれば "guest" を返す
    # if distances[best_match_index] <= threshold:
    #     return known_names[best_match_index]
    # else:
    #     return None


