from db import get_db


def find_all(result_filter=None, limit=50):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        where  = "WHERE l.access_result = %s" if result_filter else ""
        params = [result_filter] if result_filter else []
        cursor.execute(f"""
            SELECT l.log_id, l.access_result, l.confidence,
                   l.liveness, l.event_time,
                   e.full_name AS person_name
            FROM access_logs l
            LEFT JOIN employees e ON l.employee_id = e.employee_id
            {where}
            ORDER BY l.event_time DESC LIMIT %s
        """, params + [min(int(limit), 200)])
        rows = cursor.fetchall()
        for r in rows:
            if r.get("event_time"):
                r["event_time"] = r["event_time"].isoformat()
        return rows
    finally:
        cursor.close()
        conn.close()


def find_by_id(log_id: int):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT l.log_id, l.access_result, l.confidence,
                   l.liveness, l.event_time,
                   e.full_name AS person_name
            FROM access_logs l
            LEFT JOIN employees e ON l.employee_id = e.employee_id
            WHERE l.log_id = %s
        """, (log_id,))
        row = cursor.fetchone()
        if row and row.get("event_time"):
            row["event_time"] = row["event_time"].isoformat()
        return row
    finally:
        cursor.close()
        conn.close()


def create(employee_id, access_result: str, confidence: float,
           liveness: str, snapshot_img: bytes):
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO access_logs "
            "(employee_id, access_result, confidence, liveness, snapshot_img) "
            "VALUES (%s, %s, %s, %s, %s)",
            (employee_id, access_result, confidence, liveness, snapshot_img),
        )
        log_id = cursor.lastrowid
        conn.commit()
        return log_id
    finally:
        cursor.close()
        conn.close()


def delete(log_id: int):
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT log_id FROM access_logs WHERE log_id = %s", (log_id,))
        if not cursor.fetchone():
            return False
        cursor.execute("DELETE FROM access_logs WHERE log_id = %s", (log_id,))
        conn.commit()
        return True
    finally:
        cursor.close()
        conn.close()


def get_image(log_id: int):
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT snapshot_img FROM access_logs WHERE log_id = %s", (log_id,))
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        cursor.close()
        conn.close()