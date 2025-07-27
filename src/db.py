import os

import psycopg
from dotenv import load_dotenv

# .envファイルをロード
load_dotenv()
HOST = os.getenv("POSTGRES_HOST")
USER = os.getenv("POSTGRES_USER")
PASSWORD = os.getenv("POSTGRES_PASSWORD")
DBNAME = os.getenv("POSTGRES_DATABASE")
PORT = os.getenv("POSTGRES_PORT")

# データベースとのコネクションを確立
connection = psycopg.connect(
    f"host={HOST} user={USER} password={PASSWORD} dbname={DBNAME} port={PORT}"
)


def register_record(name, count, wide):
    cursor = connection.cursor()
    # student_idsを利用してidをmembersテーブルから取得
    cursor.execute(
        """
        SELECT id FROM members WHERE face_name = %s
    """,
        (name,),
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
        SELECT nickname FROM members WHERE face_name = %s
    """,
        (name,),
    )
    result = cursor.fetchone()
    cursor.close()
    return result[0] if result else name
