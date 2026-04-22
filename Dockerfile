FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project

RUN mkdir -p /root/.insightface/models && \
    .venv/bin/python -c "\
from insightface.app import FaceAnalysis; \
app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider']); \
app.prepare(ctx_id=0, det_size=(640,640)); \
print('buffalo_l descargado OK')"

RUN .venv/bin/python -c "\
import urllib.request; \
urllib.request.urlretrieve(\
'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task',\
'/root/face_landmarker.task'\
); \
print('face_landmarker.task descargado OK')"

COPY . .

EXPOSE 5000

CMD ["uv", "run", "gunicorn", "--config", "gunicorn.conf.py", "app:app"]