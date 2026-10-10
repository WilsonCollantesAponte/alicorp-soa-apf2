"""SRV01 – Pedidos. Servicio de negocio y controlador de composición del proceso
"registrar pedido": compone SRV03 → SRV06 → SRV02 → (persistencia) → SRV05."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from shared.persistence.db import tx, rows
from shared.domain.modelos import PedidoIn, EstadoPedidoIn
from shared.domain import reglas
from shared.security.seguridad import origen_confiable
from shared.audit.auditoria import registrar
from shared.cliente_servicios import invocar

router = APIRouter(prefix="/pedidos", tags=["SRV01 Pedidos"], dependencies=[Depends(origen_confiable)])


def _siguiente_id(con):
    n = con.execute("SELECT COUNT(*) FROM ped_pedidos").fetchone()[0] + 1
    return f"PED-{n:06d}"


def _leer(pedido_id: str):
    with tx() as con:
        p = con.execute("""SELECT p.*, c.razon_social FROM ped_pedidos p JOIN cli_clientes c ON c.cliente_id=p.cliente_id
                           WHERE p.pedido_id=?""", (pedido_id,)).fetchone()
        if not p: raise HTTPException(404, f"Pedido {pedido_id} no existe")
        lineas = rows(con.execute("SELECT item,sku,descripcion,cantidad,precio_unitario AS precioUnitario,importe FROM ped_lineas WHERE pedido_id=? ORDER BY item", (pedido_id,)))
    return {"pedidoId": p["pedido_id"], "clienteId": p["cliente_id"], "razonSocial": p["razon_social"], "canal": p["canal"],
            "origen": p["origen"], "estado": p["estado"], "subtotal": p["subtotal"], "igv": p["igv"], "total": p["total"],
            "moneda": "PEN", "reservaId": p["reserva_id"], "fechaRequerida": p["fecha_requerida"],
            "direccionEntrega": p["direccion_entrega"], "observacion": p["observacion"], "creadoPor": p["creado_por"],
            "creadoEn": p["creado_en"], "actualizadoEn": p["actualizado_en"], "lineas": lineas}


def _notificar(request, pedido_id, destinatario, evento, mensaje, medio="EMAIL"):
    invocar("SRV01", "POST", "/notificaciones", request, json={"pedidoId": pedido_id, "destinatario": destinatario or "sin-correo",
            "medio": medio, "evento": evento, "mensaje": mensaje})


@router.post("", status_code=201, summary="Registrar pedido (orquesta SRV03, SRV06, SRV02 y SRV05)")
def registrar_pedido(body: PedidoIn, request: Request):
    ahora = datetime.now().isoformat(timespec="seconds")
    # 1) SRV03: ¿el cliente está habilitado?
    v = invocar("SRV01", "GET", f"/clientes/{body.clienteId}/validacion", request)
    if v.status_code == 404: raise HTTPException(404, f"Cliente {body.clienteId} no existe")
    val = v.json()
    if not val["habilitado"]:
        registrar(request, "SRV01", "registrarPedido", body.clienteId, "RECHAZADO_CLIENTE")
        raise HTTPException(422, {"mensaje": "Cliente no habilitado para pedidos", "motivos": val["motivos"]})
    # 2) SRV06: valorizar con el precio vigente del canal
    c = invocar("SRV01", "POST", "/catalogo/cotizaciones", request, json={"canal": body.canal, "lineas": [l.model_dump() for l in body.lineas]})
    if c.status_code != 200: raise HTTPException(c.status_code, c.json().get("detail"))
    cot = c.json()
    subtotal, igv, total = reglas.calcular_totales(cot["subtotal"])
    with tx() as con:
        pedido_id = _siguiente_id(con)
        con.execute("INSERT INTO ped_pedidos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (pedido_id, body.clienteId, body.canal, body.origen, "REGISTRANDO", subtotal, igv, total, None,
                     body.fechaRequerida, body.direccionEntrega or val.get("direccion"), body.observacion, body.usuario or body.origen, ahora, ahora))
        for i, l in enumerate(cot["lineas"], 1):
            con.execute("INSERT INTO ped_lineas VALUES (?,?,?,?,?,?,?)", (pedido_id, i, l["sku"], l["descripcion"], l["cantidad"], l["precioUnitario"], l["importe"]))
    # 3) SRV02: reservar stock (todo o nada)
    almacen = "CD-PIURA"
    r = invocar("SRV01", "POST", "/inventario/reservas", request, json={"pedidoRef": pedido_id, "almacen": almacen, "lineas": [l.model_dump() for l in body.lineas]})
    if r.status_code == 409:
        with tx() as con:
            con.execute("UPDATE ped_pedidos SET estado='OBSERVADO_SIN_STOCK', actualizado_en=? WHERE pedido_id=?", (ahora, pedido_id))
        _notificar(request, pedido_id, val.get("email"), "PEDIDO_OBSERVADO", f"Pedido {pedido_id} observado por falta de stock en {almacen}.")
        registrar(request, "SRV01", "registrarPedido", pedido_id, "OBSERVADO_SIN_STOCK")
        return JSONResponse(status_code=409, content={"pedidoId": pedido_id, "estado": "OBSERVADO_SIN_STOCK", "detalle": r.json()["detail"]})
    reserva_id = r.json()["reservaId"]
    # 4) Regla comercial de crédito → estado inicial
    linea = invocar("SRV01", "GET", f"/clientes/{body.clienteId}", request).json()["lineaCredito"]
    estado = reglas.estado_inicial(total, linea)
    with tx() as con:
        con.execute("UPDATE ped_pedidos SET estado=?, reserva_id=?, actualizado_en=? WHERE pedido_id=?", (estado, reserva_id, ahora, pedido_id))
    # 5) SRV05: avisar al canal
    _notificar(request, pedido_id, val.get("email"), "PEDIDO_" + estado,
               f"Pedido {pedido_id} {estado.replace('_', ' ').lower()} por S/ {total:,.2f}. Reserva {reserva_id}.",
               "WHATSAPP" if body.origen == "CON02" else "EMAIL")
    registrar(request, "SRV01", "registrarPedido", pedido_id, estado)
    return _leer(pedido_id)


@router.get("", summary="Listar pedidos (filtros por cliente, estado y origen)")
def listar(clienteId: Optional[str] = None, estado: Optional[str] = None, origen: Optional[str] = None):
    sql = """SELECT p.pedido_id AS pedidoId, p.cliente_id AS clienteId, c.razon_social AS razonSocial, p.canal, p.origen,
             p.estado, p.total, p.creado_en AS creadoEn FROM ped_pedidos p JOIN cli_clientes c ON c.cliente_id=p.cliente_id WHERE 1=1"""
    prm = []
    if clienteId: sql += " AND p.cliente_id=?"; prm.append(clienteId)
    if estado: sql += " AND p.estado=?"; prm.append(estado)
    if origen: sql += " AND p.origen=?"; prm.append(origen)
    with tx() as con:
        return rows(con.execute(sql + " ORDER BY p.pedido_id DESC", prm))


@router.get("/{pedidoId}", summary="Consultar pedido con sus líneas")
def obtener(pedidoId: str):
    return _leer(pedidoId)


@router.patch("/{pedidoId}/estado", summary="Cambiar estado (aprobar, anular, despachar, entregar)")
def cambiar_estado(pedidoId: str, body: EstadoPedidoIn, request: Request):
    p = _leer(pedidoId)
    if not reglas.transicion_valida(p["estado"], body.estado):
        raise HTTPException(409, f"Transición no permitida: {p['estado']} → {body.estado}")
    if body.estado == "ANULADO" and p["reservaId"]:
        invocar("SRV01", "DELETE", f"/inventario/reservas/{p['reservaId']}", request)  # compensación
    with tx() as con:
        con.execute("UPDATE ped_pedidos SET estado=?, actualizado_en=? WHERE pedido_id=?", (body.estado, datetime.now().isoformat(timespec="seconds"), pedidoId))
    registrar(request, "SRV01", "cambiarEstado", pedidoId, body.estado)
    return _leer(pedidoId)
