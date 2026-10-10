#!/usr/bin/env bash
# Arranca la solución completa en local (4 procesos). Ctrl+C detiene todo.
set -e
RAIZ="$(cd "$(dirname "$0")" && pwd)"
trap 'kill 0' EXIT
cd "$RAIZ/ServiciosSOA"
"${PYTHON:-python3}" -m shared.persistence.seed
"${PYTHON:-python3}" -m uvicorn main:app --host 127.0.0.1 --port 8000 &
sleep 2
"${PYTHON:-python3}" -m uvicorn esb.gateway:app --host 127.0.0.1 --port 8080 &
sleep 1
(cd "$RAIZ/PortalComercialInterno" && npm start --silent) &
(cd "$RAIZ/PortalDistribuidores" && npm start --silent) &
sleep 2
echo "Listo:  CON01 http://127.0.0.1:3001 | CON02 http://127.0.0.1:3002 | Swagger servicios http://127.0.0.1:8000/docs | Swagger ESB http://127.0.0.1:8080/docs"
wait
