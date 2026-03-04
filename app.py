import os
import re
import base64
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from face_logic import process_registration, process_recognition

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "db"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "NuevaClaveSegura2026"),
        database=os.getenv("DB_NAME", "sentinel_db"),
        port=int(os.getenv("DB_PORT", 3306))
    )

def sanitize_string(text: str) -> str:
    """Permite letras, números, espacios y acentos."""
    return re.sub(r"[^a-zA-Z0-9\sáéíóúÁÉÍÓÚñÑ\-\.]", "", text).strip()

def ensure_admin_exists(cursor, conn):
    """Crea el usuario admin por defecto si no existe."""
    cursor.execute("SELECT user_id FROM users WHERE email = %s", ("admin@admin.com",))
    if not cursor.fetchone():
        hashed_pw = generate_password_hash("admin123")
        cursor.execute(
            "INSERT INTO users (full_name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            ("Administrador", "admin@admin.com", hashed_pw, "admin"),
        )
        conn.commit()

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "Cuerpo JSON requerido"}), 400

    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"success": False, "message": "Email y contraseña requeridos"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        ensure_admin_exists(cursor, conn)

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if user and check_password_hash(user["password_hash"], password):
        return jsonify({
            "success": True,
            "user": {
                "user_id": user["user_id"],
                "full_name": user["full_name"],
                "role": user["role"],       # "admin" | "employee"
                "email": user["email"],
            },
        })

    return jsonify({"success": False, "message": "Credenciales inválidas"}), 401

@app.route("/api/register", methods=["POST"])
def register():
    name     = request.form.get("name", "").strip()
    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    role     = request.form.get("role", "employee")
    image_file = request.files.get("image")

    if not all([name, email, password, image_file]):
        return jsonify({"success": False, "message": "Faltan datos requeridos"}), 400

    clean_name = sanitize_string(name)
    if not clean_name:
        return jsonify({"success": False, "message": "El nombre contiene caracteres inválidos"}), 400

    if role not in ("admin", "employee"):
        role = "employee"

    image_bytes = image_file.read()

    # Procesar embedding facial
    try:
        embedding = process_registration(image_bytes)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

    hashed_pw = generate_password_hash(password)
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (full_name, email, password_hash, embedding, role) "
            "VALUES (%s, %s, %s, %s, %s)",
            (clean_name, email, hashed_pw, embedding.tobytes(), role),
        )
        conn.commit()
        return jsonify({"success": True, "message": "Usuario registrado exitosamente"})
    except mysql.connector.IntegrityError:
        return jsonify({"success": False, "message": "El correo ya está registrado"}), 409
    except Exception as e:
        return jsonify({"success": False, "message": f"Error en base de datos: {e}"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/api/recognize", methods=["POST"])
def recognize():
    image_file = request.files.get("image")
    if not image_file:
        return jsonify({"status": "error", "message": "No se proporcionó imagen"}), 400

    image_bytes = image_file.read()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT user_id, full_name, embedding FROM users WHERE embedding IS NOT NULL"
        )
        users_db = cursor.fetchall()

        result = process_recognition(image_bytes, users_db)

        user_id       = result.get("user_id")
        access_status = result.get("access")
        confidence    = result.get("confidence", 0.0)

        cursor.execute(
            "INSERT INTO access_logs (user_id, access_status, confidence_score, snapshot_img) "
            "VALUES (%s, %s, %s, %s)",
            (user_id, access_status, confidence, image_bytes),
        )
        conn.commit()
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/api/users", methods=["GET"])
def get_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT user_id, full_name, email, role, created_at "
            "FROM users WHERE role != 'admin'"
        )
        users = cursor.fetchall()
        # Serializar fechas
        for u in users:
            if u.get("created_at"):
                u["created_at"] = u["created_at"].isoformat()
        return jsonify(users)
    finally:
        cursor.close()
        conn.close()


@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Evitar borrar al admin por accidente
        cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"success": False, "message": "Usuario no encontrado"}), 404
        if row["role"] == "admin":
            return jsonify({"success": False, "message": "No se puede eliminar al administrador"}), 403

        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
        return jsonify({"success": True, "message": "Usuario eliminado correctamente"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/api/logs", methods=["GET"])
def get_logs():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT l.log_id, l.access_status, l.confidence_score, l.event_time,
                   u.full_name
            FROM access_logs l
            LEFT JOIN users u ON l.user_id = u.user_id
            ORDER BY l.event_time DESC
            LIMIT 50
        """)
        logs = cursor.fetchall()
        for log in logs:
            if log.get("event_time"):
                log["event_time"] = log["event_time"].isoformat()
        return jsonify(logs)
    finally:
        cursor.close()
        conn.close()


@app.route("/api/logs/<int:log_id>/image", methods=["GET"])
def get_log_image(log_id):
    """Devuelve la imagen de un log como binario JPEG (evita base64 en el listado)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT snapshot_img FROM access_logs WHERE log_id = %s", (log_id,)
        )
        row = cursor.fetchone()
        if row and row[0]:
            return Response(row[0], mimetype="image/jpeg")
        return jsonify({"status": "error", "message": "Imagen no encontrada"}), 404
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, host="0.0.0.0", port=5000)