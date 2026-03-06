import cv2
import numpy as np
from insightface.app import FaceAnalysis
from liveness import LivenessDetector
from blink_detector import detect_blink_in_sequence

LIVENESS_MODEL_PATH  = "models/2.7_80x80_MiniFASNetV2.onnx"
SIMILARITY_THRESHOLD = 0.50

print("[face_logic] Cargando InsightFace (buffalo_l)...")
_face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
_face_app.prepare(ctx_id=0, det_size=(640, 640))

print("[face_logic] Cargando LivenessDetector...")
_liveness = LivenessDetector(LIVENESS_MODEL_PATH)

print("[face_logic] Modelos listos.")


def _decode_image(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("No se pudo decodificar la imagen.")
    return img


def process_registration(image_bytes: bytes) -> np.ndarray:
    img   = _decode_image(image_bytes)
    faces = _face_app.get(img)

    if len(faces) == 0:
        raise ValueError("No se detectó ningún rostro en la imagen.")
    if len(faces) > 1:
        raise ValueError("Se detectaron varios rostros. Solo debe haber una persona.")

    face = faces[0]
    is_real, score, _ = _liveness.check_liveness(img, face.bbox)

    if not is_real:
        raise ValueError(
            f"Anti-spoofing: imagen detectada como falsa (score={score:.2f}). "
            "Use una cámara en vivo."
        )

    return face.normed_embedding


def process_recognition(frame_bytes_list: list, users_db: list) -> dict:
    """
    Recibe una lista de bytes (frames en orden cronológico).
    1. Decodifica todos los frames
    2. Detecta parpadeo con MediaPipe en la secuencia completa
    3. Corre liveness model en el frame central
    4. Compara embedding contra la DB
    """
    if not frame_bytes_list:
        return {
            "status":     "error",
            "access":     "DENIED",
            "person":     "Desconocido",
            "user_id":    None,
            "confidence": 0.0,
            "liveness":   "UNKNOWN",
            "message":    "No se recibieron frames.",
        }

    frames = []
    for fb in frame_bytes_list:
        try:
            frames.append(_decode_image(fb))
        except Exception:
            pass

    if not frames:
        return {
            "status":     "error",
            "access":     "DENIED",
            "person":     "Desconocido",
            "user_id":    None,
            "confidence": 0.0,
            "liveness":   "UNKNOWN",
            "message":    "No se pudieron decodificar los frames.",
        }

    # ── 1. Detección de parpadeo ──────────────────────────────────────────────
    blinked = detect_blink_in_sequence(frames)
    if not blinked:
        return {
            "status":     "success",
            "access":     "DENIED",
            "person":     "POSIBLE ATAQUE",
            "user_id":    None,
            "confidence": 0.0,
            "liveness":   "SPOOFING",
            "message":    "No se detectó parpadeo. Posible foto o imagen estática.",
        }

    # ── 2. Usar el frame central para liveness + reconocimiento ──────────────
    best_frame = frames[len(frames) // 2]
    faces      = _face_app.get(best_frame)

    if len(faces) == 0:
        return {
            "status":     "error",
            "access":     "DENIED",
            "person":     "Desconocido",
            "user_id":    None,
            "confidence": 0.0,
            "liveness":   "UNKNOWN",
            "message":    "No se detectó ningún rostro.",
        }

    face = faces[0]

    # ── 3. Liveness model pasivo (segunda capa) ───────────────────────────────
    is_real, live_score, _ = _liveness.check_liveness(best_frame, face.bbox)
    if not is_real:
        return {
            "status":     "success",
            "access":     "DENIED",
            "person":     "POSIBLE ATAQUE",
            "user_id":    None,
            "confidence": float(live_score),
            "liveness":   "SPOOFING",
            "message":    f"Liveness fallido (score={live_score:.2f}). Posible video o deepfake.",
        }

    # ── 4. Comparar embedding ─────────────────────────────────────────────────
    target     = face.normed_embedding
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
            "status":     "success",
            "access":     "GRANTED",
            "person":     best_name,
            "user_id":    best_id,
            "confidence": best_score,
            "liveness":   "REAL",
            "message":    "",
        }

    return {
        "status":     "success",
        "access":     "DENIED",
        "person":     "Desconocido",
        "user_id":    None,
        "confidence": best_score,
        "liveness":   "REAL",
        "message":    "Rostro no reconocido.",
    }