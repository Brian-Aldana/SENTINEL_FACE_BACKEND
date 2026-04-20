from db import get_db


def find_all(include_inactive: bool = False):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        where = "" if include_inactive else "WHERE r.is_active = 1"
        cursor.execute(f"""
            SELECT r.role_id, r.name, r.description,
                   r.is_active, r.created_at,
                   COUNT(ur.usuario_id) AS total_usuarios
            FROM roles r
            LEFT JOIN usuarios_roles ur ON r.role_id = ur.role_id
            {where}
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
            SELECT r.role_id, r.name, r.description,
                   r.is_active, r.created_at,
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


def deactivate(role_id: int):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT name, is_active FROM roles WHERE role_id = %s", (role_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None, "Rol no encontrado"
        if not row["is_active"]:
            return None, "El rol ya está inactivo"
        cursor.execute(
            "UPDATE roles SET is_active = 0 WHERE role_id = %s", (role_id,)
        )
        conn.commit()
        return row["name"], None
    finally:
        cursor.close()
        conn.close()


def activate(role_id: int):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT name, is_active FROM roles WHERE role_id = %s", (role_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None, "Rol no encontrado"
        if row["is_active"]:
            return None, "El rol ya está activo"
        cursor.execute(
            "UPDATE roles SET is_active = 1 WHERE role_id = %s", (role_id,)
        )
        conn.commit()
        return row["name"], None
    finally:
        cursor.close()
        conn.close()
