from db import get_db


def find_all(resolved=0):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT sa.alert_id, sa.alert_type, sa.severity,
                   sa.description, sa.resolved, sa.created_at,
                   sa.resolved_at, al.event_time
            FROM security_alerts sa
            LEFT JOIN access_logs al ON sa.log_id = al.log_id
            WHERE sa.resolved = %s
            ORDER BY sa.created_at DESC LIMIT 100
        """, (resolved,))
        rows = cursor.fetchall()
        for r in rows:
            for f in ("created_at", "event_time", "resolved_at"):
                if r.get(f):
                    r[f] = r[f].isoformat()
        return rows
    finally:
        cursor.close()
        conn.close()


def find_by_id(alert_id: int):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT sa.alert_id, sa.alert_type, sa.severity,
                   sa.description, sa.resolved, sa.created_at,
                   sa.resolved_at, sa.log_id,
                   al.event_time,
                   u.full_name AS resolved_by_name
            FROM security_alerts sa
            LEFT JOIN access_logs al ON sa.log_id = al.log_id
            LEFT JOIN usuarios u ON sa.resolved_by = u.usuario_id
            WHERE sa.alert_id = %s
        """, (alert_id,))
        row = cursor.fetchone()
        if row:
            for f in ("created_at", "event_time", "resolved_at"):
                if row.get(f):
                    row[f] = row[f].isoformat()
        return row
    finally:
        cursor.close()
        conn.close()


def create(log_id, alert_type: str, severity: str, description: str = None):
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO security_alerts (log_id, alert_type, severity, description) "
            "VALUES (%s, %s, %s, %s)",
            (log_id, alert_type, severity, description),
        )
        alert_id = cursor.lastrowid
        conn.commit()
        return alert_id
    finally:
        cursor.close()
        conn.close()


def resolve(alert_id: int, usuario_id):
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE security_alerts SET resolved=1, resolved_by=%s, resolved_at=NOW() "
            "WHERE alert_id=%s",
            (usuario_id, alert_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        conn.close()


def delete(alert_id: int):
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT alert_id FROM security_alerts WHERE alert_id = %s", (alert_id,))
        if not cursor.fetchone():
            return False
        cursor.execute("DELETE FROM security_alerts WHERE alert_id = %s", (alert_id,))
        conn.commit()
        return True
    finally:
        cursor.close()
        conn.close()
