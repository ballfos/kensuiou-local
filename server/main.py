import argparse
import asyncio
import base64
import functools
import json
import os

import dotenv
import torch
import websockets
from db import get_nickname, register_record
from predict import detect_objects_and_get_centers, identify_person

dotenv.load_dotenv()


hand_coordinate = 550
# bar_y_coordinate = 470 #バーのy座標
bar_x_reft = 770  # バーのx座標左
bar_x_right = 370  # バーのx座標右

# 画像保存ディレクトリ
save_path = "received_images"
os.makedirs(save_path, exist_ok=True)




async def handler(websocket, model, face_features_path):
    status = "start"
    name = None
    nickname = None
    count = 0
    hand_flg = 1

    async for message in websocket:
        
        # Base64デコードしてバイナリデータを取得
        image_data = base64.b64decode(message)

        # ファイル名を生成
        file_name = f"image.jpg"
        file_path = os.path.join(save_path, file_name)

        # ファイルに保存
        with open(file_path, "wb") as f:
            f.write(image_data)

        if status == "start":
            name = identify_person(file_path, face_features_path)
            if name is not None:
                status = "Authenticated"
                nickname = get_nickname(name)
                print(f"Identified: {nickname}")

        elif status == "Authenticated":
            centers = detect_objects_and_get_centers(model, file_path)
            if len(centers["hand"]) == 2 and all(
                y <= hand_coordinate for _, y in centers["hand"]
            ):
                status = "Counting"
                if (
                    centers["hand"][0][0] <= bar_x_reft
                    and centers["hand"][1][0] >= bar_x_right
                ):
                    wide = False
                else:
                    wide = True

        elif status == "Counting":
            centers = detect_objects_and_get_centers(model, file_path)
            if len(centers["hand"]) == 2:
                bar_y_coordinate = centers["hand"][0][1]  # 手のy座標をバーのy座標とする

            # 手が二つ検出されない、またはバーより下にある時、カウントの終了
            if len(centers["hand"]) != 2 or all(
                y > hand_coordinate for _, y in centers["hand"]
            ):
                status = "end"

            # 頭がバーより上に来た時、回数追加、フラグのリセット
            elif hand_flg == 1 and centers["face"][0][1] <= bar_y_coordinate:
                hand_flg = 0
                count = count + 1
                print(f"count={count}")

            # 頭を一定値下げるとフラグを1にする
            elif hand_flg == 0 and centers["face"][0][1] > bar_y_coordinate + 100:
                hand_flg = 1
        if status == "end":
            response = {"status": status, "name": nickname, "count": count}
            await websocket.send(json.dumps(response))
            # データベースに記録
            register_record(name, count, wide)
            print(f"player: {nickname}")
            print("count=", count)
            print("wide=", wide)
            # 状態をリセット
            status = "start"
            name = None
            nickname = None
            count = 0
            hand_flg = 1

        response = {"status": status, "name": nickname, "count": count}
        await websocket.send(json.dumps(response))


async def main(args):
    # モデルのロード
    model = torch.hub.load("ultralytics/yolov5", "custom", path=args.model)
    handler_with_model = functools.partial(
        handler,
        model=model,
        face_features_path=args.face_feature,
    )

    async with websockets.serve(handler_with_model, args.host, args.port):
        await asyncio.Future()  # サーバーを永続実行


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebSocket Server for Kensuiou")
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--model", type=str, default="models/best.pt")
    parser.add_argument("--face-feature", type=str, default="models/face_features.json")
    args = parser.parse_args()
    print(f"Starting server on ws://{args.host}:{args.port}")

    asyncio.run(main(args))
