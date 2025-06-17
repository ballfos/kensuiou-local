import psycopg2

# nameと紐付けられたmember_idのリスト
student_ids = {
    "inoue": "25622038",
    "takahashi": "25622041",
    "kawano": "25622021",
    "suzuki": "25622015",
}


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

