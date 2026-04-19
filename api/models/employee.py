from db import get_db


def find_all():
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT e.employee_id, e.full_name, e.document_id,
                   e.is_active, e.created_at, e.updated_at,
                   u.full_name AS registered_by
            FROM employees e
            LEFT JOIN usuarios u ON e.registered_by = u.usuario_id
            ORDER BY e.created_at DESC
        """)
        rows = cursor.fetchall()
        for r in rows:
            for f in ("created_at", "updated_at"):
                if r.get(f):
                    r[f] = r[f].isoformat()
        return rows
    finally:
        cursor.close()
        conn.close()


def find_by_id(employee_id: int):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT e.employee_id, e.full_name, e.document_id,
                   e.is_active, e.created_at, e.updated_at,
                   u.full_name AS registered_by
            FROM employees e
            LEFT JOIN usuarios u ON e.registered_by = u.usuario_id
            WHERE e.employee_id = %s
        """, (employee_id,))
        row = cursor.fetchone()
        if row:
            for f in ("created_at", "updated_at"):
                if row.get(f):
                    row[f] = row[f].isoformat()
        return row
    finally:
        cursor.close()
        conn.close()


def create(full_name: str, document_id: str, embedding: bytes, usuario_id):
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO employees (full_name, document_id, embedding, registered_by) "
            "VALUES (%s, %s, %s, %s)",
            (full_name, document_id, embedding, usuario_id),
        )
        new_id = cursor.lastrowid
        conn.commit()
        return new_id
    finally:
        cursor.close()
        conn.close()


def delete(employee_id: int):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT full_name FROM employees WHERE employee_id = %s", (employee_id,))
        row = cursor.fetchone()
        if not row:
            return None
        cursor.execute("DELETE FROM employees WHERE employee_id = %s", (employee_id,))
        conn.commit()
        return row["full_name"]
    finally:
        cursor.close()
        conn.close()


def find_active_with_embeddings():
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT employee_id AS user_id, full_name, embedding "
            "FROM employees WHERE embedding IS NOT NULL AND is_active = 1"
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
