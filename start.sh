#!/bin/sh
set -e
if [ -d "backend/app" ]; then
  uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port "${PORT:-8000}"
else
  uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
fi
