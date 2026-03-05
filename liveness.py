import cv2
import numpy as np
import onnxruntime
import os

MODEL_CONFIGS = [
    {
        "path":       "models/2.7_80x80_MiniFASNetV2.onnx",
        "scale":      4.0,
        "input_size": 128,
        "threshold":  0.60,
    },
    {
        "path":       "models/4_0_80x80_MiniFASNetV1SE.onnx",
        "scale":      4.0,
        "input_size": 80,
        "threshold":  0.60,
    },
]


class _SingleModel:
    def __init__(self, config: dict):
        self.scale      = config["scale"]
        self.input_size = config["input_size"]
        self.threshold  = config["threshold"]
        self.loaded     = False

        path = config["path"]
        if not os.path.exists(path):
            print(f"[LIVENESS] Modelo no encontrado (omitido): {path}")
            return
        try:
            self.session = onnxruntime.InferenceSession(
                path, providers=["CPUExecutionProvider"]
            )
            self.loaded = True
            print(f"[LIVENESS] Cargado: {path}")
        except Exception as e:
            print(f"[LIVENESS ERROR] {path}: {e}")

    def predict(self, image: np.ndarray, face_bbox):
        if not self.loaded:
            return None, None
        try:
            x1, y1, x2, y2 = map(int, face_bbox)
            h, w = image.shape[:2]
            wc = x2 - x1
            hc = y2 - y1
            nw = int(wc * self.scale)
            nh = int(hc * self.scale)
            nx1 = max(0, x1 - (nw - wc) // 2)
            ny1 = max(0, y1 - (nh - hc) // 2)
            nx2 = min(w, nx1 + nw)
            ny2 = min(h, ny1 + nh)
            crop = image[ny1:ny2, nx1:nx2]
            if crop.size == 0 or crop.shape[0] < 10 or crop.shape[1] < 10:
                return False, 0.0
            crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            crop = cv2.resize(crop, (self.input_size, self.input_size))
            inp  = crop.astype(np.float32) / 255.0
            inp  = (inp - 0.5) / 0.5
            inp  = np.transpose(inp, (2, 0, 1))[np.newaxis]
            name = self.session.get_inputs()[0].name
            raw  = self.session.run(None, {name: inp})[0][0]
            shift = raw - np.max(raw)
            probs = np.exp(shift) / np.sum(np.exp(shift))
            score = float(probs[1])
            return score >= self.threshold, score
        except Exception as e:
            print(f"[LIVENESS EXCEPTION] {e}")
            return False, 0.0


class LivenessDetector:
    """
    Ensemble de modelos MiniFASNet.
    Veredicto REAL solo si la mayoría de los modelos activos lo confirman.
    Si ningún modelo carga, falla abierto con advertencia en consola.
    """

    def __init__(self):
        self._models = [_SingleModel(cfg) for cfg in MODEL_CONFIGS]
        self._active = [m for m in self._models if m.loaded]
        n = len(self._active)
        if n == 0:
            print("[LIVENESS WARNING] Ningún modelo cargado — anti-spoofing desactivado.")
        else:
            print(f"[LIVENESS] Ensemble listo con {n} modelo(s).")

    def check_liveness(self, image: np.ndarray, face_bbox) -> tuple:
        if not self._active:
            return True, 1.0, "Módulo OFF"

        votes_real = 0
        scores     = []

        for model in self._active:
            is_real, score = model.predict(image, face_bbox)
            if is_real is None:
                continue
            scores.append(score)
            if is_real:
                votes_real += 1

        if not scores:
            return False, 0.0, "Error"

        avg_score = float(np.mean(scores))
        is_real   = votes_real > len(scores) / 2
        label     = f"Real ({votes_real}/{len(scores)})" if is_real else f"Fake ({votes_real}/{len(scores)})"
        return is_real, avg_score, label