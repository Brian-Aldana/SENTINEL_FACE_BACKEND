from db import get_db


def find_all():
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT r.role_id, r.name, r.description, r.created_at,
                   COUNT(ur.usuario_id) AS total_usuarios
            FROM roles r
            LEFT JOIN usuarios_roles ur ON r.role_id = ur.role_id
            GROUP BY r.role_id
            ORDER BY r.created_at ASC
        """)
        rows = cursor.fetchall()
        for r in rows:
            if r.get("created_at"):
                r["created_at"] = r["created_at"].isoformat()
        return rows
    finally:
        cursor.close()
        conn.close()


def find_by_id(role_id: int):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT r.role_id, r.name, r.description, r.created_at,
                   COUNT(ur.usuario_id) AS total_usuarios
            FROM roles r
            LEFT JOIN usuarios_roles ur ON r.role_id = ur.role_id
            WHERE r.role_id = %s
            GROUP BY r.role_id
        """, (role_id,))
        row = cursor.fetchone()
        if row and row.get("created_at"):
            row["created_at"] = row["created_at"].isoformat()
        return row
    finally:
        cursor.close()
        conn.close()


def create(name: str, description: str = None):
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO roles (name, description) VALUES (%s, %s)",
            (name, description),
        )
        new_id = cursor.lastrowid
        conn.commit()
        return new_id
    finally:
        cursor.close()
        conn.close()


def delete(role_id: int):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT name FROM roles WHERE role_id = %s", (role_id,))
        row = cursor.fetchone()
        if not row:
            return None
        cursor.execute("DELETE FROM roles WHERE role_id = %s", (role_id,))
        conn.commit()
        return row["name"]
    finally:
        cursor.close()
        conn.close()
