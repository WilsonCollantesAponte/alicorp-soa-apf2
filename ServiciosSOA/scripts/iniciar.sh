#!/usr/bin/env bash
# Levanta el Proyecto 3: servicios (8000) y ESB (8080).
set -e
cd "$(dirname "$0")/.."
"${PYTHON:-python3}" -m shared.persistence.seed
"${PYTHON:-python3}" -m uvicorn main:app --host 127.0.0.1 --port 8000 &
sleep 2
"${PYTHON:-python3}" -m uvicorn esb.gateway:app --host 127.0.0.1 --port 8080 &
echo "Servicios: http://127.0.0.1:8000/docs | ESB: http://127.0.0.1:8080/docs"
wait
