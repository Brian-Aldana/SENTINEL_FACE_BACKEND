import cv2
import numpy as np
import insightface
import mysql.connector
import os
from dotenv import load_dotenv
from insightface.app import FaceAnalysis
from liveness import LivenessDetector

load_dotenv()

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '127.0.0.1'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'sentinel_db'),
    'use_pure': True
}

LIVENESS_MODEL_PATH = "models/2.7_80x80_MiniFASNetV2.onnx"
SIMILARITY_THRESHOLD = 0.50 

class FaceRecognitionSystem:
    def __init__(self):
        print("[INIT] Cargando InsightFace (Buffalo_L)...")
        self.app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        
        print("[INIT] Cargando Detector de Vida...")
        self.liveness = LivenessDetector(LIVENESS_MODEL_PATH)

    def _get_db_connection(self):
        return mysql.connector.connect(**DB_CONFIG)

    def _decode_image(self, image_bytes):
        nparr = np.frombuffer(image_bytes, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    def register_face(self, image_bytes, user_name):
        img = self._decode_image(image_bytes)
        if img is None: return False, "Imagen corrupta."

        faces = self.app.get(img)

        if len(faces) == 0: return False, "No se detectó ningún rostro."
        if len(faces) > 1: return False, "Asegúrese de que solo haya una persona."

        is_real, score, msg = self.liveness.check_liveness(img, faces[0].bbox)
        if not is_real:
            return False, f"No se puede registrar: Parece una foto falsa ({score:.2f})"

        embedding = faces[0].normed_embedding.tobytes()

        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            sql = "INSERT INTO users (full_name, embedding, role) VALUES (%s, %s, 'employee')"
            cursor.execute(sql, (user_name, embedding))
            conn.commit()
            cursor.close()
            conn.close()
            return True, f"Usuario {user_name} registrado exitosamente."
        except mysql.connector.Error as err:
            return False, f"Error base de datos: {err}"

    def recognize_face(self, image_bytes):
        img = self._decode_image(image_bytes)
        if img is None: return {"status": "error", "message": "Imagen inválida"}

        faces = self.app.get(img)

        if len(faces) == 0:
            return {"status": "error", "message": "No se detectó rostro"}

        face = faces[0]
        is_real, live_score, live_msg = self.liveness.check_liveness(img, face.bbox)

        if not is_real:
            self._log_access(user_id=None, status='DENIED', confidence=0.0, snapshot=image_bytes)
            return {
                "status": "success",
                "person": "POSIBLE ATAQUE",
                "confidence": float(live_score),
                "access": "DENIED",
                "message": f"Liveness Fallido ({live_score:.2f})"
            }

        target_embedding = face.normed_embedding
        best_match_name = "Desconocido"
        best_match_id = None
        highest_score = 0.0

        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, full_name, embedding FROM users WHERE is_active = 1")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            for uid, name, db_blob in rows:
                saved_embedding = np.frombuffer(db_blob, dtype=np.float32)
                score = np.dot(target_embedding, saved_embedding)
                
                if score > highest_score:
                    highest_score = score
                    best_match_name = name
                    best_match_id = uid

        except mysql.connector.Error as err:
            return {"status": "error", "message": f"Error DB: {err}"}

        access_status = 'GRANTED' if highest_score >= SIMILARITY_THRESHOLD else 'DENIED'
        
        if access_status == 'DENIED':
            best_match_name = "Desconocido"
            best_match_id = None

        self._log_access(user_id=best_match_id, status=access_status, confidence=float(highest_score), snapshot=image_bytes)

        return {
            "status": "success",
            "person": best_match_name,
            "confidence": float(highest_score),
            "access": access_status,
            "liveness": "REAL"
        }

    def _log_access(self, user_id, status, confidence, snapshot):
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            sql = """
                INSERT INTO access_logs (user_id, access_status, confidence_score, snapshot_img) 
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (user_id, status, confidence, snapshot))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"[ERROR LOG] No se pudo guardar historial: {e}")

    def get_all_logs(self):
        logs = []
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            sql = """
                SELECT l.log_id, l.access_status, l.confidence_score, l.event_time, u.full_name 
                FROM access_logs l
                LEFT JOIN users u ON l.user_id = u.user_id
                ORDER BY l.event_time DESC
                LIMIT 50
            """
            cursor.execute(sql)
            for row in cursor.fetchall():
                logs.append({
                    "id": row[0],
                    "status": row[1],
                    "score": round(row[2] * 100, 1),
                    "time": row[3].strftime("%Y-%m-%d %H:%M:%S"),
                    "name": row[4] if row[4] else "Desconocido"
                })
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching logs: {e}")
        return logs

    def get_log_image(self, log_id):
        img_data = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT snapshot_img FROM access_logs WHERE log_id = %s", (log_id,))
            row = cursor.fetchone()
            if row:
                img_data = row[0]
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching image: {e}")
        return img_data

    def get_all_users_for_api(self):
        users = []
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, full_name, role, is_active FROM users")
            for row in cursor.fetchall():
                users.append({
                    "user_id": row[0],
                    "full_name": row[1],
                    "role": row[2],
                    "is_active": bool(row[3])
                })
            cursor.close()
            conn.close()
            return {"status": "success", "data": users}
        except Exception as e:
            return {"status": "error", "message": f"Error DB: {e}"}