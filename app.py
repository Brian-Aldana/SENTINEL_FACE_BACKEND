import os
import re
import json
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from face_logic import process_registration, process_recognition

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024


# ── DB ────────────────────────────────────────────────────────────────────────

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "db"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "sentinel_db"),
        port=int(os.getenv("DB_PORT", 3306)),
    )


def sanitize(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9\sáéíóúÁÉÍÓÚñÑ\-\.]", "", text).strip()


# ── HELPERS ───────────────────────────────────────────────────────────────────

def audit(cursor, admin_id, action, table=None, target_id=None, detail=None):
    cursor.execute(
        "INSERT INTO audit_log (admin_id, action, target_table, target_id, detail, ip_address) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (admin_id, action, table, target_id,
         json.dumps(detail) if detail else None, request.remote_addr),
    )


def create_alert(cursor, alert_type, log_id=None, severity="MEDIUM", description=None):
    cursor.execute(
        "INSERT INTO security_alerts (log_id, alert_type, severity, description) "
        "VALUES (%s, %s, %s, %s)",
        (log_id, alert_type, severity, description),
    )


def ensure_admin_exists(cursor, conn):
    cursor.execute("SELECT admin_id FROM admins WHERE email = %s", ("admin@admin.com",))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO admins (full_name, email, password_hash) VALUES (%s, %s, %s)",
            ("Administrador", "admin@admin.com", generate_password_hash("admin123")),
        )
        conn.commit()


# ── AUTH ──────────────────────────────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def login():
    data     = request.get_json(silent=True) or {}
    email    = data.get("email", "").strip()
    password = data.get("password", "")
    if not email or not password:
        return jsonify({"success": False, "message": "Email y contraseña requeridos"}), 400

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        ensure_admin_exists(cursor, conn)
        cursor.execute("SELECT * FROM admins WHERE email = %s AND is_active = 1", (email,))
        admin = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if admin and check_password_hash(admin["password_hash"], password):
        conn2   = get_db()
        cursor2 = conn2.cursor()
        try:
            cursor2.execute("UPDATE admins SET last_login = NOW() WHERE admin_id = %s",
                            (admin["admin_id"],))
            conn2.commit()
        finally:
            cursor2.close()
            conn2.close()
        return jsonify({
            "success":  True,
            "role":     "admin",
            "admin_id": admin["admin_id"],
            "name":     admin["full_name"],
            "email":    admin["email"],
        })

    return jsonify({"success": False, "message": "Credenciales inválidas"}), 401


# ── EMPLOYEES ─────────────────────────────────────────────────────────────────

@app.route("/api/employees", methods=["POST"])
def register_employee():
    name        = request.form.get("name", "").strip()
    document_id = request.form.get("document_id", "").strip() or None
    admin_id    = request.form.get("admin_id") or None
    image_file  = request.files.get("image")

    if not name or not image_file:
        return jsonify({"success": False, "message": "Nombre e imagen son requeridos"}), 400

    clean_name = sanitize(name)
    if not clean_name:
        return jsonify({"success": False, "message": "Nombre con caracteres inválidos"}), 400

    try:
        embedding = process_registration(image_file.read())
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO employees (full_name, document_id, embedding, registered_by) "
            "VALUES (%s, %s, %s, %s)",
            (clean_name, document_id, embedding.tobytes(), admin_id),
        )
        new_id = cursor.lastrowid
        audit(cursor, admin_id, "CREATE_EMPLOYEE", "employees", new_id,
              {"full_name": clean_name, "document_id": document_id})
        conn.commit()
        return jsonify({"success": True, "employee_id": new_id,
                        "message": "Empleado registrado exitosamente"})
    except mysql.connector.IntegrityError:
        return jsonify({"success": False, "message": "El documento ya está registrado"}), 409
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route("/api/employees", methods=["GET"])
def get_employees():
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT e.employee_id, e.full_name, e.document_id, e.is_active,
                   e.created_at, a.full_name AS registered_by
            FROM employees e
            LEFT JOIN admins a ON e.registered_by = a.admin_id
            ORDER BY e.created_at DESC
        """)
        rows = cursor.fetchall()
        for r in rows:
            if r.get("created_at"):
                r["created_at"] = r["created_at"].isoformat()
        return jsonify({"employees": rows})
    finally:
        cursor.close()
        conn.close()


@app.route("/api/employees/<int:emp_id>", methods=["DELETE"])
def delete_employee(emp_id):
    admin_id = request.args.get("admin_id")
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT full_name FROM employees WHERE employee_id = %s", (emp_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"success": False, "message": "Empleado no encontrado"}), 404
        cursor.execute("DELETE FROM employees WHERE employee_id = %s", (emp_id,))
        audit(cursor, admin_id, "DELETE_EMPLOYEE", "employees", emp_id,
              {"full_name": row["full_name"]})
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# ── RECOGNIZE ─────────────────────────────────────────────────────────────────

@app.route("/api/recognize", methods=["POST"])
def recognize():
    image_file = request.files.get("image")
    if not image_file:
        return jsonify({"status": "error", "message": "No se proporcionó imagen"}), 400

    image_bytes  = image_file.read()
    extra_frames = [f.read() for k in ("image_1", "image_2")
                    if (f := request.files.get(k))]

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT employee_id, full_name, embedding FROM employees "
            "WHERE embedding IS NOT NULL AND is_active = 1"
        )
        employees = cursor.fetchall()
        result    = process_recognition(image_bytes, employees, extra_frames or None)

        emp_id     = result.get("user_id")
        access     = result.get("access")
        confidence = result.get("confidence", 0.0)
        liveness   = result.get("liveness", "UNKNOWN")

        cursor.execute(
            "INSERT INTO access_logs (employee_id, access_result, confidence, liveness, snapshot_img) "
            "VALUES (%s, %s, %s, %s, %s)",
            (emp_id, access, confidence, liveness, image_bytes),
        )
        log_id = cursor.lastrowid

        if liveness == "SPOOFING":
            create_alert(cursor, "SPOOFING_ATTEMPT", log_id=log_id,
                         severity="HIGH", description=result.get("message"))
        elif access == "DENIED" and liveness == "REAL":
            create_alert(cursor, "UNKNOWN_FACE", log_id=log_id, severity="LOW")

        conn.commit()
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# ── LOGS ──────────────────────────────────────────────────────────────────────

@app.route("/api/logs", methods=["GET"])
def get_logs():
    result = request.args.get("result")
    limit  = min(int(request.args.get("limit", 50)), 200)
    filters, params = [], []
    if result:
        filters.append("l.access_result = %s")
        params.append(result)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(f"""
            SELECT l.log_id, l.access_result, l.confidence, l.liveness, l.event_time,
                   e.full_name AS person_name
            FROM access_logs l
            LEFT JOIN employees e ON l.employee_id = e.employee_id
            {where}
            ORDER BY l.event_time DESC LIMIT %s
        """, params + [limit])
        logs = cursor.fetchall()
        for log in logs:
            if log.get("event_time"):
                log["event_time"] = log["event_time"].isoformat()
        return jsonify({"logs": logs})
    finally:
        cursor.close()
        conn.close()


@app.route("/api/logs/<int:log_id>/image", methods=["GET"])
def get_log_image(log_id):
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT snapshot_img FROM access_logs WHERE log_id = %s", (log_id,))
        row = cursor.fetchone()
        if row and row[0]:
            return Response(row[0], mimetype="image/jpeg")
        return jsonify({"status": "error", "message": "Imagen no encontrada"}), 404
    finally:
        cursor.close()
        conn.close()


# ── ALERTS ────────────────────────────────────────────────────────────────────

@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    resolved = request.args.get("resolved", "0")
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT sa.alert_id, sa.alert_type, sa.severity,
                   sa.description, sa.resolved, sa.created_at,
                   al.event_time
            FROM security_alerts sa
            LEFT JOIN access_logs al ON sa.log_id = al.log_id
            WHERE sa.resolved = %s
            ORDER BY sa.created_at DESC LIMIT 100
        """, (resolved,))
        alerts = cursor.fetchall()
        for a in alerts:
            for f in ("created_at", "event_time"):
                if a.get(f):
                    a[f] = a[f].isoformat()
        return jsonify({"alerts": alerts})
    finally:
        cursor.close()
        conn.close()


@app.route("/api/alerts/<int:alert_id>/resolve", methods=["PATCH"])
def resolve_alert(alert_id):
    data     = request.get_json(silent=True) or {}
    admin_id = data.get("admin_id")
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE security_alerts SET resolved=1, resolved_by=%s, resolved_at=NOW() "
            "WHERE alert_id=%s", (admin_id, alert_id),
        )
        audit(cursor, admin_id, "RESOLVE_ALERT", "security_alerts", alert_id)
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# ── AUDIT LOG ─────────────────────────────────────────────────────────────────

@app.route("/api/audit", methods=["GET"])
def get_audit():
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT al.audit_id, al.action, al.target_table, al.target_id,
                   al.detail, al.ip_address, al.created_at,
                   a.full_name AS admin_name
            FROM audit_log al
            LEFT JOIN admins a ON al.admin_id = a.admin_id
            ORDER BY al.created_at DESC LIMIT 100
        """)
        rows = cursor.fetchall()
        for r in rows:
            if r.get("created_at"):
                r["created_at"] = r["created_at"].isoformat()
        return jsonify({"audit": rows})
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, host="0.0.0.0", port=5000)