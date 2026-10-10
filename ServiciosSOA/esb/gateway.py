"""ESB ligero del Proyecto 3: enrutamiento, transformación, seguridad básica,
correlación y registro de mediaciones. Puerto 8080.
Ejecutar:  uvicorn esb.gateway:app --port 8080   → http://127.0.0.1:8080/docs
En Vercel corre dentro de la app unificada (app_unificada.py) y llega a los
servicios en modo "inproc" (misma interfaz REST, sin salir a la red)."""
import json, os, time, uuid
from datetime import datetime
from pathlib import Path
import httpx, yaml
from fastapi import FastAPI, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ESB_CONFIG, BASE_DIR, API_VERSION, ESB_DESTINO, ESB_LOG_PATH, SERVICES_TRANSPORT  # noqa: E402
from esb.transformaciones import REGISTRO  # noqa: E402

CFG = yaml.safe_load(Path(ESB_CONFIG).read_text(encoding="utf-8"))
INPROC = SERVICES_TRANSPORT == "inproc"
if INPROC:
    CFG["esb"]["destino_servicios"] = "http://servicios-soa.interno/api/v1"
elif ESB_DESTINO:
    CFG["esb"]["destino_servicios"] = ESB_DESTINO.rstrip("/")
# Las API keys de demo de routes.yaml se pueden reemplazar por variables de entorno
for _cid, _c in CFG["consumidores"].items():
    _c["api_key"] = os.getenv(f"ESB_API_KEY_{_cid}") or _c["api_key"]
RUTAS = {r["prefijo"]: r for r in CFG["rutas"]}
KEYS = {c["api_key"]: (cid, c) for cid, c in CFG["consumidores"].items()}
LOG = Path(ESB_LOG_PATH) if ESB_LOG_PATH else BASE_DIR / CFG["esb"]["log_mediaciones"]
try:
    LOG.parent.mkdir(parents=True, exist_ok=True)
except OSError:
    pass


def _cliente_http():
    """Cliente hacia los servicios: por red (local) o en el mismo proceso (Vercel)."""
    if INPROC:
        from main import app as servicios
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=servicios, raise_app_exceptions=False), timeout=CFG["esb"]["timeout_segundos"])
    return httpx.AsyncClient(timeout=CFG["esb"]["timeout_segundos"])

app = FastAPI(title="Alicorp SOA – ESB (Enterprise Service Bus ligero)", version=API_VERSION,
              description="Puerta única de CON01 y CON02 hacia SRV01–SRV06. Enruta, transforma, valida al consumidor, "
                          "agrega correlación y deja traza de cada mediación. Cabeceras: `X-Api-Key`, `X-Usuario`, `X-Cliente` (solo CON02).")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _sobre(ok, data, meta, status):
    return JSONResponse(status_code=status, content={"ok": ok, "data": data, "meta": meta})


@app.get("/health", tags=["ESB"])
def health():
    return {"estado": "UP", "componente": "ESB", "destino": CFG["esb"]["destino_servicios"],
            "transporte": "inproc" if INPROC else "http", "rutas": len(RUTAS)}


@app.get("/esb/v1/_registro", tags=["ESB"], summary="Registro de servicios y rutas publicadas (descubrimiento)")
def registro():
    return [{"id": r["id"], "rutaPublica": f"/esb/v1/{p}", "servicio": r["servicio"], "destino": r["destino"],
             "metodosPorConsumidor": r["metodos"], "transformaciones": r.get("transformaciones", {})} for p, r in RUTAS.items()]


@app.get("/esb/v1/_trazas", tags=["ESB"], summary="Últimas mediaciones registradas")
def trazas(n: int = 15):
    if not LOG.exists(): return []
    return [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines()[-n:]][::-1]


@app.api_route("/esb/v1/{prefijo}", methods=["GET", "POST", "PATCH", "DELETE"], tags=["ESB – mediación"])
@app.api_route("/esb/v1/{prefijo}/{resto:path}", methods=["GET", "POST", "PATCH", "DELETE"], tags=["ESB – mediación"])
async def mediar(prefijo: str, request: Request, resto: str = "",
                 x_api_key: str = Header(..., description="con01-demo-key | con02-demo-key"),
                 x_usuario: str = Header("anonimo"), x_cliente: str | None = Header(None)):
    t0 = time.perf_counter()
    corr = request.headers.get("x-correlation-id") or "COR-" + uuid.uuid4().hex[:10].upper()
    meta = {"correlationId": corr, "esb": "ESB-Alicorp", "ruta": f"/esb/v1/{prefijo}/{resto}".rstrip("/")}
    # 1) Seguridad: ¿consumidor registrado?
    if x_api_key not in KEYS:
        return _sobre(False, {"error": "Consumidor no registrado"}, meta, 401)
    cid, ccfg = KEYS[x_api_key]
    meta["consumidor"] = cid
    # 2) Enrutamiento
    ruta = RUTAS.get(prefijo)
    if not ruta:
        return _sobre(False, {"error": f"No existe ruta para '{prefijo}'"}, meta, 404)
    metodo = request.method
    if metodo not in ruta["metodos"].get(cid, []):
        return _sobre(False, {"error": f"{cid} no tiene permiso para {metodo} {prefijo}"}, meta, 403)
    meta["servicio"] = ruta["servicio"]
    # 3) Transformación de entrada
    body = None
    if metodo in ("POST", "PATCH"):
        raw = await request.body()
        body = json.loads(raw) if raw else {}
    params = dict(request.query_params)
    ctx = {"metodo": metodo, "prefijo": prefijo, "subruta": ("/" + resto) if resto else "", "consumidor": cid,
           "canal": ccfg["canal_por_defecto"], "usuario": x_usuario, "cliente": x_cliente, "transformado": []}
    for nombre in ruta.get("transformaciones", {}).get(cid, []):
        body, params = REGISTRO[nombre](ctx, body, params)
    meta["transformaciones"] = ctx["transformado"]
    # 4) Comunicación con el servicio destino (REST/JSON)
    url = CFG["esb"]["destino_servicios"] + ruta["destino"] + ctx["subruta"]
    headers = {"X-Origen": "ESB", "X-Correlation-Id": corr, "X-Usuario": x_usuario, "X-Canal": ctx["canal"]}
    try:
        async with _cliente_http() as cli:
            r = await cli.request(metodo, url, params=params, json=body, headers=headers)
        status = r.status_code
        data = r.json() if r.content else None
    except httpx.HTTPError as e:
        status, data = 503, {"error": f"Servicio {ruta['servicio']} no disponible", "detalle": str(e)}
    # 5) Transformación de salida: sobre estándar {ok, data, meta}
    if isinstance(data, dict) and "detail" in data and status >= 400:
        data = {"error": data["detail"]}
    meta["latenciaMs"] = round((time.perf_counter() - t0) * 1000, 1)
    meta["destino"] = url.replace(CFG["esb"]["destino_servicios"], "SRV:/api/v1")
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"fechaHora": datetime.now().isoformat(timespec="seconds"), "correlationId": corr, "consumidor": cid,
                                "usuario": x_usuario, "metodo": metodo, "servicio": ruta["servicio"], "destino": meta["destino"],
                                "status": status, "transformaciones": ctx["transformado"], "latenciaMs": meta["latenciaMs"]}, ensure_ascii=False) + "\n")
    except OSError:
        pass  # el registro de mediaciones nunca debe tumbar la petición
    return _sobre(status < 400, data, meta, status)
