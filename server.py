import os
import websockets
import asyncio
import base64
import numpy as np
import os
import torch
from extract import identify_person,detect_objects_and_get_centers
import psycopg2
import dotenv
import os
from write_sql import register_record
import json

dotenv.load_dotenv()
USERNAME = os.getenv("USERNAME")
DBNAME = os.getenv("DBNAME")
PASSWORD = os.getenv("PASSWORD")
URL= os.getenv("URL")

status = "start"
name ="none"
count = 0
hand_flg = 1

hand_coordinate = 550
# bar_y_coordinate = 470 #バーのy座標
bar_x_reft = 770 #バーのx座標左
bar_x_right = 370 #バーのx座標右

# データベースとのコネクションを確立
connection = psycopg2.connect("host=" + URL + " dbname=" + DBNAME + " user=" + USERNAME + " password=" + PASSWORD + " port=5432")


model_path = 'yolov5/runs/train/exp5/weights/best.pt'  # トレーニング時の保存先

# トレーニング済みモデルをロード
model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path)

# 画像保存ディレクトリ
save_path = "received_images"
os.makedirs(save_path, exist_ok=True)


async def receive_image(websocket):
    global status, name, count, hand_flg
    global model, connection, save_path

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
            name = identify_person(file_path)
            if name != "none":
                status = "Authenticated"
                print(f"Identified: {name}")

        elif status == "Authenticated":
            centers = detect_objects_and_get_centers(model,file_path)
            if len(centers["hand"]) == 2 and all(y <= hand_coordinate for _, y in centers["hand"]):
               status = "Counting"
               if centers["hand"][0][0] <= bar_x_reft and centers["hand"][1][0] >= bar_x_right:
                    wide = False
               else:
                    wide = True
                    

        elif status == "Counting":
            centers = detect_objects_and_get_centers(model,file_path)    
            if len(centers["hand"]) == 2:
               bar_y_coordinate = centers["hand"][0][1]  #手のy座標をバーのy座標とする


            #手が二つ検出されない、またはバーより下にある時、カウントの終了
            if len(centers["hand"]) != 2 or all(y > hand_coordinate for _, y in centers["hand"]):
                status ="end"

            #頭がバーより上に来た時、回数追加、フラグのリセット
            elif hand_flg == 1 and centers["face"][0][1] <= bar_y_coordinate :
                hand_flg =0
                count = count+1
                print(f"count={count}")
            
            #頭を一定値下げるとフラグを1にする
            elif hand_flg == 0 and centers["face"][0][1] > bar_y_coordinate + 100:
                hand_flg = 1
        if status == "end":
            response = {
            "status": status,
            "name": name,
            "count": count
        }
            await websocket.send(json.dumps(response))
            # データベースに記録
            register_record(connection, name, count, wide)
            print(f"player: {name}")
            print("count=", count)
            print("wide=", wide)
            # 状態をリセット
            status = "start"
            name = "none"
            count = 0
            hand_flg = 1
            



        response = {
            "status": status,
            "name": name,
            "count": count
        }
        await websocket.send(json.dumps(response))




async def main():
    async with websockets.serve(receive_image, "localhost", 8765):
        print("Server started at ws://localhost:8765")
        await asyncio.Future()  # サーバーを永続実行

if __name__ == "__main__":
    asyncio.run(main())