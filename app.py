import os
import base64
from flask import Flask, request, jsonify
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

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM users WHERE email = 'admin@admin.com'")
    admin = cursor.fetchone()
    if not admin:
        hashed_pw = generate_password_hash('admin123')
        cursor.execute(
            "INSERT INTO users (full_name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            ('Administrador', 'admin@admin.com', hashed_pw, 'admin')
        )
        conn.commit()

    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        return jsonify({
            "success": True,
            "user": {
                "user_id": user['user_id'],
                "full_name": user['full_name'],
                "role": user['role'],
                "email": user['email']
            }
        })
    return jsonify({"success": False, "message": "Credenciales inválidas"}), 401

@app.route('/api/register', methods=['POST'])
def register():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role', 'employee')
    image_file = request.files.get('image')

    if not all([name, email, password, image_file]):
        return jsonify({"success": False, "message": "Faltan datos requeridos"}), 400

    image_bytes = image_file.read()
    
    try:
        embedding = process_registration(image_bytes)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

    hashed_pw = generate_password_hash(password)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO users (full_name, email, password_hash, embedding, role) VALUES (%s, %s, %s, %s, %s)",
            (name, email, hashed_pw, embedding.tobytes(), role)
        )
        conn.commit()
        return jsonify({"success": True, "message": "Usuario registrado exitosamente"})
    except mysql.connector.IntegrityError:
        return jsonify({"success": False, "message": "El correo ya está registrado"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": "Error en base de datos"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/recognize', methods=['POST'])
def recognize():
    image_file = request.files.get('image')
    if not image_file:
        return jsonify({"status": "error", "message": "No se proporcionó imagen"}), 400

    image_bytes = image_file.read()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, full_name, embedding FROM users WHERE embedding IS NOT NULL")
    users_db = cursor.fetchall()

    try:
        result = process_recognition(image_bytes, users_db)
        
        user_id = result.get('user_id') 
        access_status = result.get('access')
        confidence = result.get('confidence', 0.0)
        
        cursor.execute(
            "INSERT INTO access_logs (user_id, access_status, confidence_score, snapshot_img) VALUES (%s, %s, %s, %s)",
            (user_id, access_status, confidence, image_bytes)
        )
        conn.commit()
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/users', methods=['GET'])
def get_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, full_name, email, role, created_at FROM users WHERE role != 'admin'")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(users)

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True, "message": "Usuario eliminado y registros en cascada actualizados"})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT l.log_id, l.access_status, l.confidence_score, l.event_time, 
               l.snapshot_img, u.full_name 
        FROM access_logs l 
        LEFT JOIN users u ON l.user_id = u.user_id 
        ORDER BY l.event_time DESC LIMIT 50
    """
    cursor.execute(query)
    logs = cursor.fetchall()
    
    for log in logs:
        if log['snapshot_img']:
            log['snapshot_img'] = f"data:image/jpeg;base64,{base64.b64encode(log['snapshot_img']).decode('utf-8')}"
            
    cursor.close()
    conn.close()
    return jsonify(logs)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)