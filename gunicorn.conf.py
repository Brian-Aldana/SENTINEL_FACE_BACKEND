import os

workers      = int(os.environ.get("GUNICORN_WORKERS", "1"))
worker_class = "sync"
timeout      = 120
keepalive    = 5
bind         = "0.0.0.0:5000"
accesslog    = "-"
errorlog     = "-"
loglevel     = "info"
max_requests        = 200
max_requests_jitter = 20
