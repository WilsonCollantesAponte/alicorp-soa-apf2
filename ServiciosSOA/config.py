"""Configuración inicial del Proyecto 3 – Servicios SOA (Alicorp, APF2).
Todos los valores se pueden sobreescribir con variables de entorno (ver .env.example).
Ningún secreto vive en el código: la cadena de conexión llega solo por DATABASE_URL."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
EN_VERCEL = bool(os.getenv("VERCEL"))
# El sistema de archivos de Vercel es de solo lectura salvo /tmp
_TMP = Path("/tmp")

# Persistencia: Postgres (Neon) si existe DATABASE_URL; si no, SQLite local.
DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
DB_MOTOR = "postgres" if DATABASE_URL.startswith(("postgres://", "postgresql://")) else "sqlite"
DB_PATH = Path(os.getenv("SOA_DB_PATH", (_TMP if EN_VERCEL else BASE_DIR / "data") / "alicorp_soa.db"))

SERVICES_HOST = os.getenv("SOA_HOST", "127.0.0.1")
SERVICES_PORT = int(os.getenv("SOA_PORT", "8000"))
# Cómo un servicio invoca a otro (siempre por su interfaz REST):
#   "http"   → por red, a SOA_BASE_URL (modo local con procesos separados)
#   "inproc" → misma interfaz REST pero dentro del mismo proceso (Vercel / app unificada)
SERVICES_TRANSPORT = os.getenv("SOA_TRANSPORTE", "http")
SERVICES_BASE_URL = os.getenv("SOA_BASE_URL", f"http://{SERVICES_HOST}:{SERVICES_PORT}/api/v1")
ESB_PORT = int(os.getenv("ESB_PORT", "8080"))
ESB_CONFIG = Path(os.getenv("ESB_CONFIG", BASE_DIR / "esb-config" / "routes.yaml"))
# Destino del ESB: si se define, reemplaza a destino_servicios de routes.yaml
ESB_DESTINO = os.getenv("ESB_DESTINO")
ESB_LOG_PATH = os.getenv("ESB_LOG_PATH") or (str(_TMP / "mediaciones.jsonl") if EN_VERCEL else None)
API_VERSION = "1.0.0-apf2"
