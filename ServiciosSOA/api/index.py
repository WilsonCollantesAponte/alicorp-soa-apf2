"""Punto de entrada de Vercel (runtime Python). Expone la app ASGI unificada.
vercel.json reescribe todas las rutas hacia esta función."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app_unificada import app  # noqa: E402,F401
