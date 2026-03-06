import cv2
import numpy as np
import onnxruntime
import os

LIVENESS_THRESHOLD = 0.60


class LivenessDetector:
    def __init__(self, model_path: str):
        self.loaded = False
        if not os.path.exists(model_path):
            print(f"[LIVENESS] Modelo no encontrado: {model_path}")
            return
        try:
            self.session = onnxruntime.InferenceSession(
                model_path, providers=["CPUExecutionProvider"]
            )
            self.loaded = True
            print(f"[LIVENESS] Modelo cargado: {model_path}")
        except Exception as e:
            print(f"[LIVENESS ERROR] {e}")

    def check_liveness(self, image: np.ndarray, face_bbox) -> tuple:
        if not self.loaded:
            return True, 1.0, "Módulo OFF"
        try:
            x1, y1, x2, y2 = map(int, face_bbox)
            h, w = image.shape[:2]

            scale = 4.0
            wc = x2 - x1
            hc = y2 - y1
            nw = int(wc * scale)
            nh = int(hc * scale)
            nx1 = max(0, x1 - (nw - wc) // 2)
            ny1 = max(0, y1 - (nh - hc) // 2)
            nx2 = min(w, nx1 + nw)
            ny2 = min(h, ny1 + nh)

            crop = image[ny1:ny2, nx1:nx2]
            if crop.size == 0 or crop.shape[0] < 10 or crop.shape[1] < 10:
                return False, 0.0, "Error Crop"

            crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)

            lab = cv2.cvtColor(crop, cv2.COLOR_RGB2LAB)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
            lab[:, :, 0] = clahe.apply(lab[:, :, 0])
            crop = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

            crop = cv2.resize(crop, (128, 128))
            inp  = crop.astype(np.float32) / 255.0
            inp  = (inp - 0.5) / 0.5
            inp  = np.transpose(inp, (2, 0, 1))[np.newaxis]

            name  = self.session.get_inputs()[0].name
            raw   = self.session.run(None, {name: inp})[0][0]
            shift = raw - np.max(raw)
            probs = np.exp(shift) / np.sum(np.exp(shift))
            score = float(probs[1])

            is_real = score >= LIVENESS_THRESHOLD
            return is_real, score, "Real" if is_real else "Fake"

        except Exception as e:
            print(f"[LIVENESS EXCEPTION] {e}")
            return False, 0.0, "Error"