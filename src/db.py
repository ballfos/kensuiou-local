import json
import os

import psycopg2
from dotenv import load_dotenv

# .envファイルをロード
load_dotenv()
HOST = os.getenv("POSTGRES_HOST")
USER = os.getenv("POSTGRES_USER")
PASSWORD = os.getenv("POSTGRES_PASSWORD")
DBNAME = os.getenv("POSTGRES_DATABASE")
PORT = os.getenv("POSTGRES_PORT")

# データベースとのコネクションを確立
connection = psycopg2.connect(
    f"host={HOST} user={USER} password={PASSWORD} dbname={DBNAME} port={PORT}"
)

# 環境変数からJSON文字列を取得
student_ids_json = os.getenv("STUDENT_IDS")

# JSON文字列を辞書型に変換
student_ids = json.loads(student_ids_json)


def register_record(name, count, wide):
    cursor = connection.cursor()
    # student_idsを利用してidをmembersテーブルから取得
    cursor.execute(
        """
        SELECT id FROM members WHERE student_id = %s
    """,
        (student_ids.get(name),),
    )
    result = cursor.fetchone()
    id = result[0] if result else None
    # SQL文を実行してlogsテーブルにmember_id, counts, wideを挿入
    cursor.execute(
        """
        INSERT INTO logs (member_id, counts, wide)
        VALUES (%s, %s, %s)
    """,
        (id, count, wide),
    )
    connection.commit()
    cursor.close()


def get_nickname(name):
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT nickname FROM members WHERE student_id = %s
    """,
        (student_ids.get(name),),
    )
    result = cursor.fetchone()
    cursor.close()
    return result[0] if result else name
