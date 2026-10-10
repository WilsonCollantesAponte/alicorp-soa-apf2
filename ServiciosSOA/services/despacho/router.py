"""SRV04 – Despacho/Logística. Programa la salida de mercadería de un pedido confirmado."""
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from shared.persistence.db import tx, rows
from shared.domain.modelos import DespachoIn, EstadoDespachoIn
from shared.security.seguridad import origen_confiable
from shared.audit.auditoria import registrar
from shared.cliente_servicios import invocar

router = APIRouter(prefix="/despachos", tags=["SRV04 Despacho/Logística"], dependencies=[Depends(origen_confiable)])
COLS = """despacho_id AS despachoId, pedido_id AS pedidoId, almacen_origen AS almacenOrigen, transportista, placa,
          fecha_programada AS fechaProgramada, direccion, estado, guia_remision AS guiaRemision, creado_en AS creadoEn, actualizado_en AS actualizadoEn"""


@router.post("", status_code=201, summary="Programar despacho de un pedido CONFIRMADO")
def programar(body: DespachoIn, request: Request):
    pr = invocar("SRV04", "GET", f"/pedidos/{body.pedidoId}", request)
    if pr.status_code == 404: raise HTTPException(404, "Pedido no existe")
    ped = pr.json()
    if ped["estado"] != "CONFIRMADO":
        raise HTTPException(409, f"Solo se despachan pedidos CONFIRMADOS (estado actual: {ped['estado']})")
    did = "DES-" + uuid.uuid4().hex[:6].upper()
    guia = "T001-" + uuid.uuid4().hex[:6].upper()  # referencia simulada de guía de remisión
    ahora = datetime.now().isoformat(timespec="seconds")
    with tx() as con:
        con.execute("INSERT INTO des_despachos VALUES (?,?,?,?,?,?,?,?,?,?,?)", (did, body.pedidoId, body.almacenOrigen, body.transportista,
                    body.placa, body.fechaProgramada, body.direccion or ped["direccionEntrega"], "PROGRAMADO", guia, ahora, ahora))
    invocar("SRV04", "PATCH", f"/pedidos/{body.pedidoId}/estado", request, json={"estado": "EN_DESPACHO"})
    cli = invocar("SRV04", "GET", f"/clientes/{ped['clienteId']}", request).json()
    invocar("SRV04", "POST", "/notificaciones", request, json={"pedidoId": body.pedidoId, "destinatario": cli.get("email") or "sin-correo",
            "medio": "EMAIL", "evento": "DESPACHO_PROGRAMADO", "mensaje": f"Despacho {did} programado para {body.fechaProgramada} con {body.transportista}."})
    registrar(request, "SRV04", "programarDespacho", did, "OK")
    return obtener(did)


@router.get("", summary="Listar despachos (por pedido o estado)")
def listar(pedidoId: Optional[str] = None, estado: Optional[str] = None):
    sql, p = f"SELECT {COLS} FROM des_despachos WHERE 1=1", []
    if pedidoId: sql += " AND pedido_id=?"; p.append(pedidoId)
    if estado: sql += " AND estado=?"; p.append(estado)
    with tx() as con:
        return rows(con.execute(sql + " ORDER BY creado_en DESC", p))


@router.get("/{despachoId}", summary="Consultar despacho (tracking)")
def obtener(despachoId: str):
    with tx() as con:
        r = con.execute(f"SELECT {COLS} FROM des_despachos WHERE despacho_id=?", (despachoId,)).fetchone()
    if not r: raise HTTPException(404, "Despacho no existe")
    return dict(r)


@router.patch("/{despachoId}/estado", summary="Actualizar estado del despacho (EN_RUTA, ENTREGADO, INCIDENCIA)")
def actualizar(despachoId: str, body: EstadoDespachoIn, request: Request):
    d = obtener(despachoId)
    with tx() as con:
        con.execute("UPDATE des_despachos SET estado=?, actualizado_en=? WHERE despacho_id=?", (body.estado, datetime.now().isoformat(timespec="seconds"), despachoId))
    if body.estado == "ENTREGADO":
        invocar("SRV04", "PATCH", f"/pedidos/{d['pedidoId']}/estado", request, json={"estado": "ENTREGADO"})
    registrar(request, "SRV04", "actualizarDespacho", despachoId, body.estado)
    return obtener(despachoId)
