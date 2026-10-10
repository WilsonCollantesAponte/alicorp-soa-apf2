#!/usr/bin/env bash
# Prueba de humo del prototipo. Ver opciones en scripts/prueba_humo.py
cd "$(dirname "$0")/.."
exec "${PYTHON:-python3}" scripts/prueba_humo.py "$@"
