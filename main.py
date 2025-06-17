import cv2
import numpy as np
import os
import torch
from face_identify import identify_person
import psycopg2
import dotenv
import os
from write_sql import register_record

dotenv.load_dotenv()
USERNAME = os.getenv("USERNAME")
DBNAME = os.getenv("DBNAME")
PASSWORD = os.getenv("PASSWORD")
URL= os.getenv("URL")
# データベースとのコネクションを確立
connection = psycopg2.connect("host=" + URL + " dbname=" + DBNAME + " user=" + USERNAME + " password=" + PASSWORD + " port=5432")


model_path = 'yolov5/runs/train/exp5/weights/best.pt'  # トレーニング時の保存先

# トレーニング済みモデルをロード
model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path)

cap = cv2.VideoCapture(0)

image_counter = 0  # 呼び出し回数をカウントする変数
hand_coordinate = 500
# bar_y_coordinate = 470 #バーのy座標
bar_x_reft = 770 #バーのx座標左
bar_x_right = 370 #バーのx座標右

def receive_image():
    global image_counter
    save_path="captured_images"
    
    if not cap.isOpened():
        raise Exception("カメラに接続できませんでした。")

    # フレームをキャプチャ
    ret, frame = cap.read()
    if not ret:
        cap.release()
        raise Exception("画像をキャプチャできませんでした。")

    # 保存ディレクトリを作成（存在しない場合）
    os.makedirs(save_path, exist_ok=True)

    # ファイル名を生成
    file_name = f"image_{image_counter:04d}.jpg"
    file_path = os.path.join(save_path, file_name)

    # 画像を保存
    cv2.imwrite(file_path, frame)

    return file_path

def detect_objects_and_get_centers(image_path):
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


def main():
    count = 0
    hand_flg = 1 # フラグが1の時のみ回数が加算される

    while True: #顔認識が成功するまで待機
        image_path = receive_image()
        name = identify_person(image_path)

        if name == "none"  or name == "guest":
            continue
        else:
            print(f"Identified: {name}")
            break


    while True: #バーを持つまで待機
        image_path = receive_image()
        centers = detect_objects_and_get_centers(image_path)

        if len(centers["hand"]) == 2 and all(y <= hand_coordinate for _, y in centers["hand"]):
            print("start")

            if centers["hand"][0][0] <= bar_x_reft and centers["hand"][1][0] >= bar_x_right:
                wide = False
            else:
                wide = True
            break


    while True:        
        # 画像の受信
        image_path = receive_image()
        
        # 画像の処理
        centers = detect_objects_and_get_centers(image_path)    
        bar_y_coordinate = centers["hand"][0][1]  #手のy座標をバーのy座標とする

        #手が二つ検出されない、またはバーより下にある時、カウントの終了
        if len(centers["hand"]) != 2 or all(y > hand_coordinate for _, y in centers["hand"]):
            break

        #頭がバーより上に来た時、回数追加、フラグのリセット
        if hand_flg == 1 and centers["face"][0][1] <= bar_y_coordinate :
            hand_flg =0
            count = count+1
            print(f"count={count}")
        
        #頭を一定値下げるとフラグを1にする
        if hand_flg == 0 and centers["face"][0][1] > bar_y_coordinate +30:
            hand_flg = 1

        # print("Face Centers:", centers["face"])
        # print("Hand Centers:", centers["hand"])

    print(f"player: {name}")
    print("count=",count)
    print("wide=",wide)
    register_record(connection, name, count, wide)
    # データベースとのコネクションを閉じる
    connection.close()

        # カメラリソースを解放
    cap.release()


if __name__ == "__main__":
    main()
