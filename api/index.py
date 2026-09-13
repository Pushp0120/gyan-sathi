"""Vercel serverless entry point for the Gyan Sathi FastAPI backend.

Vercel mounts every /api/* request to this function. The frontend static build
is served separately; SPA rewrites live in vercel.json.
"""
import os
import sys

# Serverless: no persistent disk — put uploads in /tmp
os.environ.setdefault("UPLOAD_DIR", "/tmp/uploads")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: E402

# Vercel's Python runtime uses this ASGI app object directly
app = app
