"""Cliente HTTP para que un servicio invoque a otro SOLO por su interfaz REST
(nunca importando sus clases internas). Propaga la correlación de la petición.

Dos transportes, misma interfaz REST (mismas rutas, cabeceras y JSON):
  - "http"   (local, procesos separados): petición de red a SOA_BASE_URL.
  - "inproc" (Vercel / app unificada): la petición REST se entrega a la app de
    servicios dentro del mismo proceso, sin salir a la red. Evita que la función
    serverless se llame a sí misma por Internet (latencia, protección de despliegue)."""
from urllib.parse import urlsplit
import httpx
from fastapi import HTTPException, Request
import config

_cliente_inproc = None


def _inproc():
    global _cliente_inproc
    if _cliente_inproc is None:
        from starlette.testclient import TestClient
        from main import app  # import diferido: evita import circular
        _cliente_inproc = TestClient(app, base_url="http://servicios-soa.interno", raise_server_exceptions=False)
    return _cliente_inproc


def invocar(origen: str, metodo: str, ruta: str, request: Request | None = None, **kw):
    h = {"X-Origen": origen}
    if request is not None:
        for k in ("x-correlation-id", "x-usuario", "x-canal"):
            if k in request.headers:
                h[k] = request.headers[k]
    try:
        if config.SERVICES_TRANSPORT == "inproc":
            prefijo = urlsplit(config.SERVICES_BASE_URL).path or "/api/v1"
            return _inproc().request(metodo, f"{prefijo}{ruta}", headers=h, **kw)
        return httpx.request(metodo, f"{config.SERVICES_BASE_URL}{ruta}", headers=h, timeout=10, **kw)
    except httpx.HTTPError as e:
        raise HTTPException(503, f"Servicio no disponible ({ruta}): {e}")
