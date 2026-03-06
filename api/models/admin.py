from db import get_db
from werkzeug.security import generate_password_hash, check_password_hash


def find_all():
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT admin_id, full_name, email, is_active, created_at, last_login "
            "FROM admins ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()
        for r in rows:
            for f in ("created_at", "last_login"):
                if r.get(f):
                    r[f] = r[f].isoformat()
        return rows
    finally:
        cursor.close()
        conn.close()


def find_by_id(admin_id: int):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT admin_id, full_name, email, is_active, created_at, last_login "
            "FROM admins WHERE admin_id = %s",
            (admin_id,),
        )
        row = cursor.fetchone()
        if row:
            for f in ("created_at", "last_login"):
                if row.get(f):
                    row[f] = row[f].isoformat()
        return row
    finally:
        cursor.close()
        conn.close()


def find_by_email(email: str):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM admins WHERE email = %s AND is_active = 1", (email,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()


def create(full_name: str, email: str, password: str):
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO admins (full_name, email, password_hash) VALUES (%s, %s, %s)",
            (full_name, email, generate_password_hash(password)),
        )
        new_id = cursor.lastrowid
        conn.commit()
        return new_id
    finally:
        cursor.close()
        conn.close()


def delete(admin_id: int):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT full_name FROM admins WHERE admin_id = %s", (admin_id,))
        row = cursor.fetchone()
        if not row:
            return None
        cursor.execute("DELETE FROM admins WHERE admin_id = %s", (admin_id,))
        conn.commit()
        return row["full_name"]
    finally:
        cursor.close()
        conn.close()


def update_last_login(admin_id: int):
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE admins SET last_login = NOW() WHERE admin_id = %s", (admin_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def ensure_default_admin():
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT admin_id FROM admins WHERE email = %s", ("admin@admin.com",))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO admins (full_name, email, password_hash) VALUES (%s, %s, %s)",
                ("Administrador", "admin@admin.com", generate_password_hash("admin123")),
            )
            conn.commit()
    finally:
        cursor.close()
        conn.close()