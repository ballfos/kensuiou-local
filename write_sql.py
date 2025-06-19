import psycopg2
import os
import json
from dotenv import load_dotenv

# .envファイルをロード
load_dotenv()

# 環境変数からJSON文字列を取得
student_ids_json = os.getenv("STUDENT_IDS")

# JSON文字列を辞書型に変換
student_ids = json.loads(student_ids_json)

def register_record(connection, name, count, wide):
    cursor = connection.cursor()
    #student_idsを利用してidをmembersテーブルから取得
    cursor.execute("""
        SELECT id FROM members WHERE student_id = %s
    """, (student_ids.get(name),))
    result = cursor.fetchone()
    id = result[0] if result else None
    # SQL文を実行してlogsテーブルにmember_id, counts, wideを挿入
    cursor.execute("""
        INSERT INTO logs (member_id, counts, wide)
        VALUES (%s, %s, %s)
    """, (id, count, wide))
    connection.commit()
    cursor.close()

def get_nickname(connection, name):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT nickname FROM members WHERE student_id = %s
    """, (student_ids.get(name),))
    result = cursor.fetchone()
    cursor.close()
    return result[0] if result else name
