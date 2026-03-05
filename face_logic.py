import cv2
import numpy as np
from insightface.app import FaceAnalysis
from liveness import LivenessDetector

LIVENESS_MODEL_PATH  = "models/2.7_80x80_MiniFASNetV2.onnx"
SIMILARITY_THRESHOLD = 0.50
MAX_FACE_RATIO       = 0.62   # Solución 1: bbox > 62% del ancho → foto acercada
MULTIFRAME_REQUIRED  = 2      # Solución 3: mínimo de frames que deben pasar liveness

print("[face_logic] Cargando InsightFace (buffalo_l)...")
_face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
_face_app.prepare(ctx_id=0, det_size=(640, 640))

print("[face_logic] Cargando LivenessDetector (ensemble)...")
_liveness = LivenessDetector()

print("[face_logic] Modelos listos.")


def _decode_image(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("No se pudo decodificar la imagen.")
    return img


def _check_face_ratio(img: np.ndarray, bbox) -> None:
    """
    Solución 1: rechaza si el rostro ocupa más del MAX_FACE_RATIO del frame.
    Una foto de celular acercada siempre supera este umbral.
    """
    face_width  = bbox[2] - bbox[0]
    frame_width = img.shape[1]
    ratio = face_width / frame_width
    if ratio > MAX_FACE_RATIO:
        raise ValueError(
            f"Rostro demasiado cercano o imagen plana (ratio={ratio:.2f}). "
            "Mantenga distancia normal de la cámara."
        )


def process_registration(image_bytes: bytes) -> np.ndarray:
    img   = _decode_image(image_bytes)
    faces = _face_app.get(img)

    if len(faces) == 0:
        raise ValueError("No se detectó ningún rostro en la imagen.")
    if len(faces) > 1:
        raise ValueError("Se detectaron varios rostros. Solo debe haber una persona.")

    face = faces[0]

    _check_face_ratio(img, face.bbox)

    is_real, score, _ = _liveness.check_liveness(img, face.bbox)
    if not is_real:
        raise ValueError(
            f"Anti-spoofing: imagen detectada como falsa (score={score:.2f}). "
            "Use una cámara en vivo."
        )

    return face.normed_embedding


def process_recognition(image_bytes: bytes, users_db: list, extra_frames: list = None) -> dict:
    """
    Solución 3: extra_frames es una lista opcional de bytes adicionales.
    Se requiere que al menos MULTIFRAME_REQUIRED frames pasen liveness.
    """
    primary_img   = _decode_image(image_bytes)
    primary_faces = _face_app.get(primary_img)

    if len(primary_faces) == 0:
        return {
            "status":     "error",
            "access":     "DENIED",
            "person":     "Desconocido",
            "user_id":    None,
            "confidence": 0.0,
            "liveness":   "UNKNOWN",
            "message":    "No se detectó ningún rostro.",
        }

    face = primary_faces[0]

    # ── Solución 1: ratio check ───────────────────────────────────────────────
    face_width  = face.bbox[2] - face.bbox[0]
    frame_width = primary_img.shape[1]
    if (face_width / frame_width) > MAX_FACE_RATIO:
        return {
            "status":     "success",
            "access":     "DENIED",
            "person":     "POSIBLE ATAQUE",
            "user_id":    None,
            "confidence": 0.0,
            "liveness":   "SPOOFING",
            "message":    "Rostro demasiado cercano o imagen plana detectada.",
        }

    # ── Solución 2 (ensemble) + Solución 3 (multi-frame) ─────────────────────
    all_frames = [primary_img]
    if extra_frames:
        for fb in extra_frames:
            try:
                all_frames.append(_decode_image(fb))
            except Exception:
                pass

    frames_passed = 0
    last_score    = 0.0

    for frame_img in all_frames:
        frame_faces = _face_app.get(frame_img)
        if len(frame_faces) == 0:
            continue
        is_real, score, _ = _liveness.check_liveness(frame_img, frame_faces[0].bbox)
        last_score = score
        if is_real:
            frames_passed += 1

    frames_evaluated = len(all_frames)
    required         = min(MULTIFRAME_REQUIRED, frames_evaluated)

    if frames_passed < required:
        return {
            "status":     "success",
            "access":     "DENIED",
            "person":     "POSIBLE ATAQUE",
            "user_id":    None,
            "confidence": float(last_score),
            "liveness":   "SPOOFING",
            "message":    (
                f"Liveness fallido: {frames_passed}/{frames_evaluated} frames pasaron "
                f"(requeridos {required}). Posible foto o pantalla."
            ),
        }

    # ── Comparar embedding ────────────────────────────────────────────────────
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