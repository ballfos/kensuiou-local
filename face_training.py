import face_recognition
import os
import json

# 顔画像が格納されているルートディレクトリ
input_dir = "face_images/"
output_json = "face_features.json"  # 保存先のJSONファイル

# 保存するデータを格納するリスト
known_faces = []

# サブディレクトリを含めて処理
for person_name in os.listdir(input_dir):
    person_dir = os.path.join(input_dir, person_name)

    # サブディレクトリでなければスキップ
    if not os.path.isdir(person_dir):
        print(f"スキップ: {person_dir}（ディレクトリではありません）")
        continue

    # サブディレクトリ内の画像ファイルを処理
    for filename in os.listdir(person_dir):
        file_path = os.path.join(person_dir, filename)

        # 画像ファイルかどうかを確認
        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            print(f"スキップ: {filename}（画像ファイルではありません）")
            continue

        # 画像を読み込む
        print(f"処理中: {file_path}")
        image = face_recognition.load_image_file(file_path)

        # 顔特徴量を抽出
        face_encodings = face_recognition.face_encodings(image)
        if len(face_encodings) == 0:
            print(f"警告: {file_path} から顔が検出されませんでした")
            continue

        # データに追加
        known_faces.append({
            "name": person_name,  # サブディレクトリ名を名前として使用
            "encoding": face_encodings[0].tolist()  # numpy配列をリストに変換
        })

# 結果をJSONに保存
with open(output_json, "w") as f:
    json.dump(known_faces, f)

print(f"顔データを {output_json} に保存しました。")