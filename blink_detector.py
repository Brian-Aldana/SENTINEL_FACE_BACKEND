import cv2
import numpy as np

EAR_THRESHOLD     = 0.22
EAR_CONSEC_FRAMES = 2

# Índices FaceMesh 478-landmark (refine_landmarks=True)
L_EYE = [33, 160, 158, 133, 153, 144]
R_EYE = [362, 385, 387, 263, 373, 380]


def _ear(landmarks, indices, w: int, h: int) -> float:
    pts = [(landmarks[i].x * w, landmarks[i].y * h) for i in indices]
    A = np.hypot(pts[1][0] - pts[5][0], pts[1][1] - pts[5][1])
    B = np.hypot(pts[2][0] - pts[4][0], pts[2][1] - pts[4][1])
    C = np.hypot(pts[0][0] - pts[3][0], pts[0][1] - pts[3][1])
    return (A + B) / (2.0 * C) if C > 0 else 1.0


def detect_blink_in_sequence(frames: list) -> bool:
    try:
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
        from mediapipe.tasks.python.vision import FaceLandmarkerOptions, RunningMode
        import mediapipe as mp
        import urllib.request
        import os

        model_path = "/root/face_landmarker.task"
        if not os.path.exists(model_path):
            url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
            urllib.request.urlretrieve(url, model_path)

        options = FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.6,
            min_face_presence_confidence=0.6,
            min_tracking_confidence=0.6,
        )

        count   = 0
        blinked = False

        with mp_vision.FaceLandmarker.create_from_options(options) as landmarker:
            for frame in frames:
                if frame is None:
                    continue
                h, w = frame.shape[:2]
                rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result   = landmarker.detect(mp_image)

                if not result.face_landmarks:
                    count = 0
                    continue

                lm  = result.face_landmarks[0]
                ear = (_ear(lm, L_EYE, w, h) + _ear(lm, R_EYE, w, h)) / 2

                if ear < EAR_THRESHOLD:
                    count += 1
                elif count >= EAR_CONSEC_FRAMES:
                    blinked = True
                    break
                else:
                    count = 0

        return blinked

    except Exception as e:
        print(f"[BLINK] Error: {e} — permitiendo sin detección de parpadeo")
        return True


def capture_and_detect(camera_index: int = 0, timeout_seconds: int = 10):
    """
    Modo cámara física: captura frames directamente desde OpenCV.
    Retorna (blinked: bool, best_frame: np.ndarray | None).
    """
    try:
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
        from mediapipe.tasks.python.vision import FaceLandmarkerOptions, RunningMode
        import mediapipe as mp
        import urllib.request
        import os

        model_path = "/root/face_landmarker.task"
        if not os.path.exists(model_path):
            url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
            urllib.request.urlretrieve(url, model_path)

        options = FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.6,
            min_face_presence_confidence=0.6,
            min_tracking_confidence=0.6,
        )

        cap        = cv2.VideoCapture(camera_index)
        count      = 0
        blinked    = False
        best_frame = None

        with mp_vision.FaceLandmarker.create_from_options(options) as landmarker:
            start = cv2.getTickCount()
            while True:
                elapsed = (cv2.getTickCount() - start) / cv2.getTickFrequency()
                if elapsed > timeout_seconds:
                    break

                ret, frame = cap.read()
                if not ret:
                    continue

                best_frame = frame.copy()
                h, w = frame.shape[:2]
                rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result   = landmarker.detect(mp_image)

                if not result.face_landmarks:
                    count = 0
                    continue

                lm  = result.face_landmarks[0]
                ear = (_ear(lm, L_EYE, w, h) + _ear(lm, R_EYE, w, h)) / 2

                if ear < EAR_THRESHOLD:
                    count += 1
                elif count >= EAR_CONSEC_FRAMES:
                    blinked = True
                    break
                else:
                    count = 0

        cap.release()
        return blinked, best_frame if blinked else None

    except Exception as e:
        print(f"[BLINK] Error: {e}")
        return False, None