"""PROYECTO 3 – Servicios SOA (Alicorp S.A.A.). Expone SRV01..SRV06 como REST/JSON.
Ejecutar:  uvicorn main:app --port 8000   → Swagger en http://127.0.0.1:8000/docs
La BD (Postgres/Neon o SQLite) se crea y se siembra sola en la primera petición."""
import threading
from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from config import API_VERSION
from shared.persistence.seed import seed
from shared.persistence.db import motor
from services.pedidos.router import router as srv01
from services.inventario.router import router as srv02
from services.clientes_distribuidores.router import router as srv03
from services.despacho.router import router as srv04
from services.notificaciones.router import router as srv05
from services.catalogo_precios.router import router as srv06

app = FastAPI(
    title="Alicorp SOA – Proyecto 3: Servicios SOA",
    version=API_VERSION,
    description=("Servicios de negocio de la solución SOA de **gestión de pedidos y distribución** (prototipo académico APF2). "
                 "Los portales CON01 y CON02 no llaman aquí directamente: entran por el ESB (puerto 8080). "
                 "Datos de prueba ficticios."),
)
for r in (srv01, srv02, srv03, srv04, srv05, srv06):
    app.include_router(r, prefix="/api/v1")


_bd_lista = False
_bd_lock = threading.Lock()


def asegurar_bd():
    """Crea el esquema y carga la semilla una sola vez por proceso (idempotente).
    Se hace en la primera petición porque en Vercel una app montada no recibe
    el evento de arranque."""
    global _bd_lista
    if _bd_lista:
        return
    with _bd_lock:
        if not _bd_lista:
            seed()
            _bd_lista = True


@app.middleware("http")
async def _bd_middleware(request: Request, call_next):
    if not _bd_lista:
        await run_in_threadpool(asegurar_bd)
    return await call_next(request)


@app.get("/health", tags=["Salud"])
def health():
    return {"estado": "UP", "proyecto": "ServiciosSOA", "servicios": ["SRV01", "SRV02", "SRV03", "SRV04", "SRV05", "SRV06"], "version": API_VERSION, "bd": motor()}
