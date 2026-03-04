import cv2
import numpy as np
import onnxruntime
import os

class LivenessDetector:
    def __init__(self, model_path):
        self.model_loaded = False
        if os.path.exists(model_path):
            try:
                self.session = onnxruntime.InferenceSession(model_path, providers=['CPUExecutionProvider'])
                self.model_loaded = True
                print(f"[LIVENESS] Modelo cargado: {model_path}")
            except Exception as e:
                print(f"[LIVENESS ERROR] {e}")
        else:
            print(f"[LIVENESS WARNING] NO ENCONTRADO: {model_path}")

    def check_liveness(self, image, face_bbox):
        if not self.model_loaded: 
            return True, 1.0, "Módulo OFF"

        try:
            x1, y1, x2, y2 = map(int, face_bbox)
            h, w, _ = image.shape
            
            # Ajuste para modelos de 128x128 (Scale 4.0 es el estándar para esta dimensión)
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
            
            # CORRECCIÓN: El modelo espera 128x128
            crop_resized = cv2.resize(crop, (128, 128))
            
            img_input = crop_resized.astype(np.float32) / 255.0
            
            mean = np.array([0.5, 0.5, 0.5], dtype=np.float32)
            std = np.array([0.5, 0.5, 0.5], dtype=np.float32)
            img_input = (img_input - mean) / std
            
            img_input = np.transpose(img_input, (2, 0, 1))
            img_input = np.expand_dims(img_input, 0)
            
            input_name = self.session.get_inputs()[0].name
            outputs = self.session.run(None, {input_name: img_input})
            raw_prediction = outputs[0][0]
            
            shift = raw_prediction - np.max(raw_prediction)
            probs = np.exp(shift) / np.sum(np.exp(shift))
            
            real_score = probs[1]
            
            is_real = real_score > 0.60
            
            return is_real, float(real_score), "Real" if is_real else "Fake"
            
        except Exception as e:
            print(f"[LIVENESS EXCEPTION] {e}")
            return False, 0.0, "Error"