"""
Gunicorn configuration — auto-loaded from the working directory by gunicorn
(so it applies no matter how the start command is written).

The critical bit is `bind`: PaaS platforms (Railway, Render, Heroku…) route
traffic to the port in $PORT and expect the app on 0.0.0.0. Gunicorn's default
127.0.0.1:8000 is unreachable from the platform proxy, which shows up as a
failing "service unavailable" healthcheck.
"""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", "3"))
timeout = int(os.environ.get("WEB_TIMEOUT", "60"))
# Recycle workers periodically to cap memory growth (jitter avoids a thundering herd).
max_requests = 1000
max_requests_jitter = 100
