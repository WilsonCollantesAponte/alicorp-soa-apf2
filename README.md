# Alicorp SOA – Producto APF2 (prototipo técnico)

Curso **Arquitectura Orientada al Servicio** – UTP Piura. Caso: **Alicorp S.A.A., gestión de pedidos y distribución**.
Prototipo académico con **datos ficticios**. Este repositorio reúne los **3 proyectos** del APF2:

| Proyecto | Carpeta | Rol | Tecnología |
|---|---|---|---|
| Proyecto 1 – **CON01 Portal Comercial Interno** | `PortalComercialInterno/` | Web consumidora 1 (analista / vendedor interno) | HTML + JS (Express solo en local) |
| Proyecto 2 – **CON02 Portal Distribuidores / Canal moderno** | `PortalDistribuidores/` | Web consumidora 2 (distribuidor) | HTML + JS (Express solo en local) |
| Proyecto 3 – **Servicios SOA + ESB** | `ServiciosSOA/` | Servicios SRV01–SRV06, ESB ligero y BD compartida | Python 3.12 + FastAPI |

## Arquitectura

```
 CON01 Portal Comercial ─┐                     ┌─ SRV01 Pedidos (orquesta SRV03 → SRV06 → SRV02 → SRV05)
                         │  REST/JSON          ├─ SRV02 Inventario
                         ├──► ESB /esb/v1 ────►├─ SRV03 Clientes / Distribuidores ──► BD compartida
 CON02 Portal Distrib. ──┘  X-Api-Key          ├─ SRV04 Despacho / Logística          (Postgres en Neon
                            enruta, transforma,├─ SRV05 Notificaciones                 o SQLite local)
                            valida, traza      └─ SRV06 Catálogo / Precios
```

- Los portales **solo hablan con el ESB** (`/esb/v1/...`). No tienen conexión ni credenciales de la BD.
- El ESB (`ServiciosSOA/esb/`, rutas en `esb-config/routes.yaml`) valida al consumidor por `X-Api-Key`, revisa los métodos permitidos, transforma mensajes (p. ej., pedido del distribuidor → modelo canónico), agrega `X-Correlation-Id`, registra trazas y devuelve el sobre `{ok, data, meta}`.
- Los servicios se invocan entre sí **solo por su interfaz REST** (`shared/cliente_servicios.py`) y son los únicos que tocan la BD (`shared/persistence/`).
- Contratos OpenAPI exportados en `ServiciosSOA/api/openapi/` (`openapi-servicios.json`, `openapi-esb.json`).

## Ejecutar en local

Requisitos: Python 3.11+ y Node.js 18+.

```bash
# 1) Dependencias
cd ServiciosSOA && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && cd ..
(cd PortalComercialInterno && npm install) && (cd PortalDistribuidores && npm install)

# 2) Todo junto (servicios :8000, ESB :8080, CON01 :3001, CON02 :3002)
PYTHON=ServiciosSOA/.venv/bin/python ./iniciar_todo.sh

# 3) Prueba de humo (en otra terminal)
PYTHON=ServiciosSOA/.venv/bin/python ServiciosSOA/scripts/prueba_humo.sh
```

- Sin `DATABASE_URL` se usa **SQLite** (`ServiciosSOA/data/alicorp_soa.db`, se crea sola).
- Con `DATABASE_URL=postgresql://...` se usa **Postgres** (Neon u otro). El esquema y los datos de prueba se crean solos en la primera petición.
- Modo igual a Vercel (ESB y servicios en un solo proceso): `cd ServiciosSOA && uvicorn app_unificada:app --port 8000`, y la prueba con `python scripts/prueba_humo.py --unificada http://127.0.0.1:8000 --sin-portales`.
- Swagger: servicios `http://127.0.0.1:8000/docs` · ESB `http://127.0.0.1:8080/docs`.

## Variables de entorno

Ver `ServiciosSOA/.env.example` y `Portal*/.env.example` (solo nombres). Los archivos `.env` **no se versionan**.

| Proyecto | Variable | Uso |
|---|---|---|
| ServiciosSOA | `DATABASE_URL` | Cadena de Postgres (Neon). Si falta, SQLite. **Secreto: solo en Vercel o en `.env`.** |
| ServiciosSOA | `ESB_API_KEY_CON01`, `ESB_API_KEY_CON02` | Opcionales: reemplazan las keys de demo de `routes.yaml` |
| ServiciosSOA | `SOA_TRANSPORTE`, `SOA_BASE_URL`, `ESB_DESTINO`, `SOA_DB_PATH`, `ESB_LOG_PATH` | Opcionales (modo local) |
| Portales | `ESB_URL` | URL del ESB (base o terminada en `/esb/v1`) |
| Portales | `API_KEY` | Key del consumidor en el ESB (por defecto `con01-demo-key` / `con02-demo-key`) |
| Portales | `USUARIO`, `CONSUMIDOR`, `PORT` | Opcionales |

> La `API_KEY` de un portal viaja al navegador: identifica al consumidor ante el ESB, no es un secreto. En APF3 se reemplaza por JWT.

## Endpoints

### ESB (lo que consumen los portales) – cabeceras `X-Api-Key`, `X-Usuario`, `X-Cliente` (solo CON02)

| Ruta pública | Servicio | CON01 | CON02 | Transformaciones |
|---|---|---|---|---|
| `/esb/v1/pedidos[/...]` | SRV01 | GET, POST, PATCH | GET, POST | CON01: `completar_origen_canal` · CON02: `pedido_distribuidor_a_canonico`, `filtrar_por_distribuidor` |
| `/esb/v1/inventario[/...]` | SRV02 | GET, POST, DELETE | GET | – |
| `/esb/v1/clientes[/...]` | SRV03 | GET, POST | GET | CON02: `filtrar_por_distribuidor` |
| `/esb/v1/despachos[/...]` | SRV04 | GET, POST, PATCH | GET | – |
| `/esb/v1/notificaciones[/...]` | SRV05 | GET, POST | GET | – |
| `/esb/v1/catalogo[/...]` | SRV06 | GET, POST | GET, POST | `forzar_canal_consumidor` |
| `/esb/v1/_registro` · `/esb/v1/_trazas` · `/health` | ESB | descubrimiento de rutas, últimas mediaciones, salud | | |

### Servicios (`/api/v1`, solo aceptan `X-Origen` = ESB, SRVxx o SWAGGER)

| Servicio | Endpoints |
|---|---|
| SRV01 Pedidos | `POST /pedidos` (orquesta SRV03, SRV06, SRV02, SRV05) · `GET /pedidos` · `GET /pedidos/{pedidoId}` · `PATCH /pedidos/{pedidoId}/estado` |
| SRV02 Inventario | `GET /inventario/stock` · `POST /inventario/reservas` · `DELETE /inventario/reservas/{reservaId}` |
| SRV03 Clientes / Distribuidores | `GET /clientes` · `POST /clientes` · `GET /clientes/{clienteId}` · `GET /clientes/{clienteId}/validacion` |
| SRV04 Despacho / Logística | `POST /despachos` · `GET /despachos` · `GET /despachos/{despachoId}` · `PATCH /despachos/{despachoId}/estado` |
| SRV05 Notificaciones | `POST /notificaciones` · `GET /notificaciones` |
| SRV06 Catálogo / Precios | `GET /catalogo/productos` · `GET /catalogo/productos/{sku}` · `POST /catalogo/cotizaciones` |
| Salud | `GET /health` |

## Despliegue en Vercel

Tres proyectos de Vercel importados desde **este mismo repositorio**, cada uno con su *Root Directory*:

| Proyecto Vercel | Root Directory | Framework | Build | Variables |
|---|---|---|---|---|
| Servicios SOA + ESB | `ServiciosSOA` | Other (Python) | ninguno (lo define `vercel.json`) | `DATABASE_URL` (cadena de Neon, *pooled*) · opcional `ESB_API_KEY_CON01/02` |
| CON01 Portal Comercial | `PortalComercialInterno` | Other | `npm run build` → `public/` (en `vercel.json`) | `ESB_URL=https://<servicios>.vercel.app` · opcional `API_KEY`, `USUARIO` |
| CON02 Portal Distribuidores | `PortalDistribuidores` | Other | `npm run build` → `public/` (en `vercel.json`) | `ESB_URL=https://<servicios>.vercel.app` · opcional `API_KEY`, `USUARIO` |

Orden: 1) desplegar **ServiciosSOA** y copiar su dominio; 2) poner ese dominio en `ESB_URL` de los dos portales y desplegarlos. Si se cambia `ESB_URL` hay que **volver a desplegar** el portal, porque `config.js` se genera en el build.

**ServiciosSOA en Vercel**
- `api/index.py` expone la app ASGI `app_unificada.py`; `vercel.json` reescribe todas las rutas hacia esa función.
- Rutas publicadas: `/` (índice) · `/esb/v1/...` (ESB) · `/docs` y `/openapi.json` (Swagger del ESB) · `/health` · `/srv/api/v1/...`, `/srv/docs`, `/srv/health` (servicios, para pruebas).
- El ESB llega a los servicios en modo `inproc`: misma interfaz REST, pero dentro de la función, sin salir a Internet.
- Python 3.12 (`.python-version`), dependencias en `requirements.txt` (incluye `psycopg[binary]`).
- La primera petición crea las tablas y carga los datos de prueba en Neon (idempotente, con *advisory lock*).
- Las trazas del ESB se guardan en `/tmp` (efímeras en serverless).

**Portales en Vercel**
- Son sitios estáticos. `npm run build` ejecuta `scripts/generar-config.js`, que escribe `public/config.js` con `ESB_URL`, `API_KEY` y `USUARIO`. El navegador llama directamente al ESB (CORS abierto en el ESB).
- `src/server.js` (Express) se usa solo en local.

## Estructura

```
alicorp-soa-apf2/
├── iniciar_todo.sh
├── PortalComercialInterno/   (CON01)  public/ · src/server.js · src/config.js · scripts/generar-config.js · vercel.json
├── PortalDistribuidores/     (CON02)  ídem
└── ServiciosSOA/             (Proyecto 3)
    ├── main.py               app de servicios SRV01–SRV06 (/api/v1)
    ├── app_unificada.py      ESB + servicios en una sola app (Vercel)
    ├── api/index.py          entrada de Vercel · api/openapi/ contratos
    ├── esb/                  gateway.py, transformaciones.py
    ├── esb-config/routes.yaml
    ├── services/             pedidos, inventario, clientes_distribuidores, despacho, notificaciones, catalogo_precios
    ├── shared/               domain, persistence (SQLite/Postgres), security, audit, cliente_servicios.py
    ├── scripts/              prueba_humo.py/.sh, iniciar.sh, exportar_openapi.py
    └── vercel.json · requirements.txt · .python-version · .env.example
```
