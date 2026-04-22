# Gunicorn configuration for SENTINEL_FACE_BACKEND
#
# Memory rationale: each worker loads the full InsightFace buffalo_l model
# (~300-500 MB) plus the ONNX liveness model into its own private heap.
# Running more than one worker on a memory-constrained host causes SIGKILL.
# A single worker with a generous timeout is the safest default; raise
# `workers` only if the host has enough RAM to sustain N × model footprint.

# ── Worker count ──────────────────────────────────────────────────────────────
# Hard-cap at 1 to prevent OOM kills.  Override via the GUNICORN_WORKERS
# environment variable if the deployment host has sufficient memory.
workers = int(__import__("os").environ.get("GUNICORN_WORKERS", "1"))

# ── Worker class & timeouts ───────────────────────────────────────────────────
# sync workers are the most memory-efficient (no event-loop overhead).
worker_class = "sync"

# ML inference can take several seconds; give each request up to 120 s before
# Gunicorn kills and restarts the worker.
timeout = 120

# Keep the worker alive between requests so the loaded models are reused.
keepalive = 5

# ── Binding ───────────────────────────────────────────────────────────────────
bind = "0.0.0.0:5000"

# ── Logging ───────────────────────────────────────────────────────────────────
accesslog = "-"
errorlog  = "-"
loglevel  = "info"

# ── Memory guard ─────────────────────────────────────────────────────────────
# Restart a worker after it has served this many requests to reclaim any
# memory that Python's allocator has not yet returned to the OS.
max_requests = 200
max_requests_jitter = 20
