import cv2
import numpy as np
from insightface.app import FaceAnalysis
from liveness import LivenessDetector

LIVENESS_MODEL_PATH = "models/2.7_80x80_MiniFASNetV2.onnx"
SIMILARITY_THRESHOLD = 0.50

print("[face_logic] Cargando InsightFace (buffalo_l)...")
_face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
_face_app.prepare(ctx_id=0, det_size=(640, 640))

print("[face_logic] Cargando LivenessDetector...")
_liveness = LivenessDetector(LIVENESS_MODEL_PATH)

print("[face_logic] Modelos listos.")

def _decode_image(image_bytes: bytes) -> np.ndarray:
    """Decodifica bytes a imagen BGR de OpenCV."""
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("No se pudo decodificar la imagen. Formato no soportado o archivo corrupto.")
    return img

def process_registration(image_bytes: bytes) -> np.ndarray:

    img = _decode_image(image_bytes)

    faces = _face_app.get(img)

    if len(faces) == 0:
        raise ValueError("No se detectó ningún rostro en la imagen.")
    if len(faces) > 1:
        raise ValueError("Se detectaron varios rostros. Asegúrese de que solo haya una persona.")

    face = faces[0]
    is_real, score, _ = _liveness.check_liveness(img, face.bbox)

    if not is_real:
        raise ValueError(
            f"Anti-spoofing: la imagen parece falsa (score liveness: {score:.2f}). "
            "Use una cámara en vivo."
        )

    return face.normed_embedding  # np.ndarray float32 [512]


def process_recognition(image_bytes: bytes, users_db: list) -> dict:

    img = _decode_image(image_bytes)

    faces = _face_app.get(img)

    if len(faces) == 0:
        return {
            "status": "error",
            "access": "DENIED",
            "person": "Desconocido",
            "user_id": None,
            "confidence": 0.0,
            "liveness": "UNKNOWN",
            "message": "No se detectó ningún rostro.",
        }

    face = faces[0]
    is_real, live_score, _ = _liveness.check_liveness(img, face.bbox)

    if not is_real:
        return {
            "status": "success",
            "access": "DENIED",
            "person": "POSIBLE ATAQUE",
            "user_id": None,
            "confidence": float(live_score),
            "liveness": "SPOOFING",
            "message": f"Liveness fallido (score: {live_score:.2f}). Posible foto o pantalla.",
        }

    # ── Comparar embedding con cada usuario en la DB ──
    target = face.normed_embedding
    best_id    = None
    best_name  = "Desconocido"
    best_score = 0.0

    for user in users_db:
        raw = user.get("embedding")
        if raw is None:
            continue
        saved = np.frombuffer(raw, dtype=np.float32)

        if saved.shape != target.shape:
            continue

        score = float(np.dot(target, saved))
        if score > best_score:
            best_score = score
            best_name  = user["full_name"]
            best_id    = user["user_id"]

    if best_score >= SIMILARITY_THRESHOLD:
        return {
            "status": "success",
            "access": "GRANTED",
            "person": best_name,
            "user_id": best_id,
            "confidence": best_score,
            "liveness": "REAL",
            "message": "",
        }
    else:
        return {
            "status": "success",
            "access": "DENIED",
            "person": "Desconocido",
            "user_id": None,
            "confidence": best_score,
            "liveness": "REAL",
            "message": "Rostro no reconocido.",
        }