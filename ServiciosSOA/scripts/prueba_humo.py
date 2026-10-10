"""Prueba de humo del prototipo (local o desplegado en Vercel).

Uso:
  python scripts/prueba_humo.py                       # local: servicios :8000, ESB :8080, portales :3001/:3002
  python scripts/prueba_humo.py --unificada http://127.0.0.1:8000     # app unificada (igual que Vercel)
  python scripts/prueba_humo.py --unificada https://<servicios>.vercel.app --con01 https://<con01>.vercel.app --con02 https://<con02>.vercel.app
Variables opcionales: API_KEY_CON01, API_KEY_CON02 (si se cambiaron en el ESB)."""
import argparse, json, os, sys
from datetime import date, timedelta
import httpx

ap = argparse.ArgumentParser()
ap.add_argument("--esb", default="http://127.0.0.1:8080")
ap.add_argument("--srv", default="http://127.0.0.1:8000")
ap.add_argument("--unificada", help="URL base de la app unificada (ESB en /, servicios en /srv)")
ap.add_argument("--con01", default="http://127.0.0.1:3001")
ap.add_argument("--con02", default="http://127.0.0.1:3002")
ap.add_argument("--sin-portales", action="store_true")
a = ap.parse_args()
if a.unificada:
    a.esb, a.srv = a.unificada.rstrip("/"), a.unificada.rstrip("/") + "/srv"
K1 = {"X-Api-Key": os.getenv("API_KEY_CON01", "con01-demo-key"), "X-Usuario": "vendedor.piura01"}
K2 = {"X-Api-Key": os.getenv("API_KEY_CON02", "con02-demo-key"), "X-Usuario": "usuario.distribuidor", "X-Cliente": "CLI-0001"}
ESB = a.esb + "/esb/v1"
cli = httpx.Client(timeout=30, follow_redirects=True)
fallos = 0


def ok(nombre, cond, muestra=None):
    global fallos
    fallos += 0 if cond else 1
    print(("PASS " if cond else "FAIL ") + nombre)
    if muestra is not None:
        print("     " + json.dumps(muestra, ensure_ascii=False)[:300])


r = cli.get(a.srv + "/health").json(); ok("Servicios /health", r.get("estado") == "UP", r)
r = cli.get(a.esb + "/health").json(); ok("ESB /health", r.get("estado") == "UP", r)
r = cli.get(ESB + "/_registro").json(); ok("ESB registro de rutas (6)", len(r) == 6, [x["rutaPublica"] + "→" + x["servicio"] for x in r])

d = cli.get(ESB + "/catalogo/productos", params={"q": "primor"}, headers=K1).json()
ok("SRV06 catálogo vía ESB [CON01] (búsqueda sin distinguir mayúsculas)", d["ok"] and d["data"] and d["data"][0]["canal"] == "INTERNO",
   {"data": d["data"], "meta": {k: d["meta"].get(k) for k in ("consumidor", "servicio", "transformaciones")}})
d2 = cli.get(ESB + "/catalogo/productos", params={"q": "Primor"}, headers=K2).json()
ok("SRV06 catálogo vía ESB [CON02] precio canal DISTRIBUIDOR", d2["ok"] and d2["data"][0]["canal"] == "DISTRIBUIDOR", d2["data"])
d = cli.get(ESB + "/inventario/stock", params={"sku": "ALI-SAL-0001", "almacen": "CD-PIURA"}, headers=K1).json()
ok("SRV02 inventario/stock vía ESB", d["ok"] and len(d["data"]) == 1, d["data"])
d = cli.get(ESB + "/clientes", headers=K1).json(); ok("SRV03 clientes (CON01 ve 5)", d["ok"] and len(d["data"]) >= 5, [c["clienteId"] for c in d["data"]])
d = cli.get(ESB + "/clientes", headers=K2).json(); ok("SRV03 clientes (CON02 solo ve su cuenta)", d["ok"] and d["data"]["clienteId"] == "CLI-0001", d["data"])

# Proceso crítico: registrar pedido (SRV01 orquesta SRV03 → SRV06 → SRV02 → SRV05)
manana = (date.today() + timedelta(days=3)).isoformat()
r = cli.post(ESB + "/pedidos", headers=K1, json={"clienteId": "CLI-0003", "canal": "MODERNO", "lineas": [{"sku": "ALI-ACE-0001", "cantidad": 5}, {"sku": "ALI-GAL-0001", "cantidad": 10}],
                                                 "fechaRequerida": manana, "direccionEntrega": "Av. Grau 1800, Piura"})
d = r.json(); ped = d["data"] if d["ok"] else {}
ok(f"SRV01 POST pedido CON01 → HTTP {r.status_code}", r.status_code == 201, {k: ped.get(k) for k in ("pedidoId", "estado", "total", "reservaId")} if ped else d)
r = cli.post(ESB + "/pedidos", headers=K2, json={"codigoDistribuidor": "CLI-0001", "items": [{"codigo": "ALI-FID-0001", "cant": 8}],
                                                 "entrega": {"fecha": manana, "direccion": "Av. Sánchez Cerro 1250, Piura"}, "comentario": "prueba de humo"})
d = r.json(); ok(f"SRV01 POST pedido CON02 (formato distribuidor → canónico) → HTTP {r.status_code}",
                 r.status_code == 201 and "pedido_distribuidor_a_canonico" in d["meta"]["transformaciones"], {"pedidoId": d["data"].get("pedidoId"), "transformaciones": d["meta"]["transformaciones"]})
d = cli.get(ESB + "/pedidos", headers=K2).json(); ok("SRV01 CON02 solo ve sus pedidos", d["ok"] and all(p["clienteId"] == "CLI-0001" for p in d["data"]), len(d["data"]))
r = cli.post(ESB + "/pedidos", headers=K1, json={"clienteId": "CLI-0005", "canal": "DISTRIBUIDOR", "lineas": [{"sku": "ALI-ACE-0001", "cantidad": 1}]})
ok(f"SRV01 rechaza cliente SUSPENDIDO → HTTP {r.status_code}", r.status_code in (409, 422), r.json()["data"])

if ped.get("estado") == "CONFIRMADO":
    r = cli.post(ESB + "/despachos", headers=K1, json={"pedidoId": ped["pedidoId"], "fechaProgramada": manana, "placa": "P1A-123"})
    d = r.json(); ok(f"SRV04 programar despacho → HTTP {r.status_code}", r.status_code == 201, d["data"])
    if r.status_code == 201:
        did = d["data"]["despachoId"]
        r = cli.patch(ESB + f"/despachos/{did}/estado", headers=K1, json={"estado": "ENTREGADO"}); ok("SRV04 despacho ENTREGADO", r.status_code == 200, r.json()["data"])
        d = cli.get(ESB + f"/pedidos/{ped['pedidoId']}", headers=K1).json(); ok("SRV01 pedido quedó ENTREGADO", d["data"]["estado"] == "ENTREGADO", d["data"]["estado"])
else:
    ok("Pedido CON01 quedó CONFIRMADO (para probar despacho)", False, ped)
d = cli.get(ESB + "/notificaciones", headers=K1).json(); ok("SRV05 notificaciones emitidas", d["ok"] and len(d["data"]) >= 1, d["data"][:1])

r = cli.post(ESB + "/inventario/reservas", headers=K2, json={}); ok(f"ESB bloquea POST reservas a CON02 → HTTP {r.status_code}", r.status_code == 403)
r = cli.get(ESB + "/pedidos", headers={"X-Api-Key": "clave-falsa"}); ok(f"ESB rechaza API key inválida → HTTP {r.status_code}", r.status_code == 401)
r = cli.get(a.srv + "/api/v1/pedidos", headers={"X-Origen": "PORTAL"}); ok(f"Servicio rechaza origen no confiable → HTTP {r.status_code}", r.status_code == 403)
d = cli.get(ESB + "/_trazas", params={"n": 3}).json(); ok("ESB trazas de mediación", isinstance(d, list), d[:1])

if not a.sin_portales:
    for nom, url in (("CON01", a.con01), ("CON02", a.con02)):
        r = cli.get(url + "/"); ok(f"{nom} portal sirve index.html", r.status_code == 200 and "<html" in r.text.lower())
        r = cli.get(url + "/config.js"); ok(f"{nom} config.js apunta al ESB", r.status_code == 200 and "/esb/v1" in r.text, r.text.strip()[:200])

print(f"\n{'TODO OK' if not fallos else str(fallos) + ' FALLO(S)'}")
sys.exit(1 if fallos else 0)
