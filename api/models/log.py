from db import get_db


def find_all(result_filter=None, limit=20, page=1):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        limit  = min(int(limit), 100)
        page   = max(int(page), 1)
        offset = (page - 1) * limit

        where  = "WHERE l.access_result = %s" if result_filter else ""
        params = [result_filter] if result_filter else []

        # Total de registros para saber si hay más páginas
        cursor.execute(f"""
            SELECT COUNT(*) AS total
            FROM access_logs l
            {where}
        """, params)
        total = cursor.fetchone()["total"]

        cursor.execute(f"""
            SELECT l.log_id, l.access_result, l.confidence,
                   l.liveness, l.event_time,
                   e.full_name AS full_name
            FROM access_logs l
            LEFT JOIN employees e ON l.employee_id = e.employee_id
            {where}
            ORDER BY l.event_time DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])
        rows = cursor.fetchall()
        for r in rows:
            if r.get("event_time"):
                r["event_time"] = r["event_time"].isoformat()
        return {
            "items": rows,
            "total": total,
            "page": page,
            "limit": limit,
            "has_more": (offset + len(rows)) < total,
        }
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
                   e.full_name AS full_name
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