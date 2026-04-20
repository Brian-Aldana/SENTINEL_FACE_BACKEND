from db import get_db
from werkzeug.security import generate_password_hash, check_password_hash


def find_all(include_inactive: bool = False):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        where = "" if include_inactive else "WHERE u.is_active = 1"
        cursor.execute(f"""
            SELECT u.usuario_id, u.full_name, u.email,
                   u.is_active, u.created_at, u.last_login,
                   GROUP_CONCAT(r.name ORDER BY r.name SEPARATOR ',') AS roles
            FROM usuarios u
            LEFT JOIN usuarios_roles ur ON u.usuario_id = ur.usuario_id
            LEFT JOIN roles r ON ur.role_id = r.role_id
            {where}
            GROUP BY u.usuario_id
            ORDER BY u.created_at DESC
        """)
        rows = cursor.fetchall()
        for r in rows:
            for f in ("created_at", "last_login"):
                if r.get(f):
                    r[f] = r[f].isoformat()
            r["roles"] = r["roles"].split(",") if r.get("roles") else []
        return rows
    finally:
        cursor.close()
        conn.close()


def find_by_id(usuario_id: int):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT u.usuario_id, u.full_name, u.email,
                   u.is_active, u.created_at, u.last_login,
                   GROUP_CONCAT(r.name ORDER BY r.name SEPARATOR ',') AS roles
            FROM usuarios u
            LEFT JOIN usuarios_roles ur ON u.usuario_id = ur.usuario_id
            LEFT JOIN roles r ON ur.role_id = r.role_id
            WHERE u.usuario_id = %s
            GROUP BY u.usuario_id
        """, (usuario_id,))
        row = cursor.fetchone()
        if row:
            for f in ("created_at", "last_login"):
                if row.get(f):
                    row[f] = row[f].isoformat()
            row["roles"] = row["roles"].split(",") if row.get("roles") else []
        return row
    finally:
        cursor.close()
        conn.close()


def find_by_email(email: str):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT u.*,
                   GROUP_CONCAT(r.name ORDER BY r.name SEPARATOR ',') AS roles
            FROM usuarios u
            LEFT JOIN usuarios_roles ur ON u.usuario_id = ur.usuario_id
            LEFT JOIN roles r ON ur.role_id = r.role_id
            WHERE u.email = %s AND u.is_active = 1
            GROUP BY u.usuario_id
        """, (email,))
        row = cursor.fetchone()
        if row:
            row["roles"] = row["roles"].split(",") if row.get("roles") else []
        return row
    finally:
        cursor.close()
        conn.close()


def create(full_name: str, email: str, password: str, role_names: list = None):
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO usuarios (full_name, email, password_hash) VALUES (%s, %s, %s)",
            (full_name, email, generate_password_hash(password)),
        )
        new_id = cursor.lastrowid
        if role_names:
            for role_name in role_names:
                cursor.execute(
                    "SELECT role_id FROM roles WHERE name = %s AND is_active = 1",
                    (role_name,)
                )
                role = cursor.fetchone()
                if role:
                    cursor.execute(
                        "INSERT IGNORE INTO usuarios_roles (usuario_id, role_id) VALUES (%s, %s)",
                        (new_id, role[0]),
                    )
        conn.commit()
        return new_id
    finally:
        cursor.close()
        conn.close()


def deactivate(usuario_id: int):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT full_name, is_active FROM usuarios WHERE usuario_id = %s",
            (usuario_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None, "Usuario no encontrado"
        if not row["is_active"]:
            return None, "El usuario ya está inactivo"
        cursor.execute(
            "UPDATE usuarios SET is_active = 0 WHERE usuario_id = %s", (usuario_id,)
        )
        conn.commit()
        return row["full_name"], None
    finally:
        cursor.close()
        conn.close()


def activate(usuario_id: int):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT full_name, is_active FROM usuarios WHERE usuario_id = %s",
            (usuario_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None, "Usuario no encontrado"
        if row["is_active"]:
            return None, "El usuario ya está activo"
        cursor.execute(
            "UPDATE usuarios SET is_active = 1 WHERE usuario_id = %s", (usuario_id,)
        )
        conn.commit()
        return row["full_name"], None
    finally:
        cursor.close()
        conn.close()


def update_last_login(usuario_id: int):
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE usuarios SET last_login = NOW() WHERE usuario_id = %s", (usuario_id,)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def assign_role(usuario_id: int, role_id: int, asignado_por: int = None):
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT IGNORE INTO usuarios_roles (usuario_id, role_id, asignado_por) "
            "VALUES (%s, %s, %s)",
            (usuario_id, role_id, asignado_por),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        conn.close()


def remove_role(usuario_id: int, role_id: int):
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM usuarios_roles WHERE usuario_id = %s AND role_id = %s",
            (usuario_id, role_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        conn.close()


def ensure_default_usuario():
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT usuario_id FROM usuarios WHERE email = %s", ("admin@admin.com",)
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO usuarios (full_name, email, password_hash) VALUES (%s, %s, %s)",
                ("Administrador", "admin@admin.com", generate_password_hash("admin123")),
            )
            new_id = cursor.lastrowid
            cursor.execute(
                "SELECT role_id FROM roles WHERE name = 'admin' AND is_active = 1"
            )
            role = cursor.fetchone()
            if not role:
                cursor.execute(
                    "INSERT INTO roles (name, description) "
                    "VALUES ('admin', 'Administrador con acceso completo')"
                )
                role_id = cursor.lastrowid
            else:
                role_id = role[0]
            cursor.execute(
                "INSERT IGNORE INTO usuarios_roles (usuario_id, role_id) VALUES (%s, %s)",
                (new_id, role_id),
            )
            conn.commit()
    finally:
        cursor.close()
        conn.close()
