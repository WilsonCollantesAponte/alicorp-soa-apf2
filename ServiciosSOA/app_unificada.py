"""App unificada del Proyecto 3 (la que se despliega en Vercel como UNA función Python).

  /                     → índice con enlaces
  /esb/v1/...           → ESB (puerta única de CON01 y CON02)
  /docs, /openapi.json  → Swagger / contrato OpenAPI del ESB
  /health               → salud del ESB
  /srv/api/v1/...       → servicios SRV01–SRV06 (solo para pruebas desde Swagger)
  /srv/docs             → Swagger de los servicios
  /srv/health           → salud de los servicios y motor de BD

El ESB llega a los servicios por su interfaz REST en modo "inproc" (mismo proceso).
Local:  uvicorn app_unificada:app --port 8000"""
import os

os.environ.setdefault("SOA_TRANSPORTE", "inproc")  # debe ir antes de importar config

from esb.gateway import app  # noqa: E402  (la app raíz es el ESB)
from main import app as servicios  # noqa: E402
from config import API_VERSION, DB_MOTOR  # noqa: E402

app.mount("/srv", servicios)


@app.get("/", tags=["ESB"], summary="Índice del despliegue")
def indice():
    return {
        "proyecto": "Alicorp SOA – Proyecto 3: Servicios SOA + ESB (APF2)",
        "version": API_VERSION,
        "bd": DB_MOTOR,
        "esb": {"base": "/esb/v1", "registro": "/esb/v1/_registro", "trazas": "/esb/v1/_trazas", "swagger": "/docs", "salud": "/health"},
        "servicios": {"base": "/srv/api/v1", "swagger": "/srv/docs", "salud": "/srv/health"},
        "nota": "Los portales CON01 y CON02 consumen solo /esb/v1 con su cabecera X-Api-Key.",
    }
