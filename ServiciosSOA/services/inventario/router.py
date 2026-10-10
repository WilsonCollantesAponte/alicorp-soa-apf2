"""SRV02 – Inventario. Disponibilidad, reserva y liberación de stock."""
import json, uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from shared.persistence.db import tx, rows
from shared.domain.modelos import ReservaIn
from shared.security.seguridad import origen_confiable
from shared.audit.auditoria import registrar

router = APIRouter(prefix="/inventario", tags=["SRV02 Inventario"], dependencies=[Depends(origen_confiable)])

@router.get("/stock", summary="Consultar stock disponible")
def stock(sku: Optional[str] = None, almacen: Optional[str] = None):
    sql, p = "SELECT s.sku,c.nombre,s.almacen,s.disponible,s.reservado FROM inv_stock s JOIN cat_productos c ON c.sku=s.sku WHERE 1=1", []
    if sku: sql += " AND s.sku=?"; p.append(sku)
    if almacen: sql += " AND s.almacen=?"; p.append(almacen)
    with tx() as con:
        return rows(con.execute(sql + " ORDER BY s.almacen,s.sku", p))

@router.post("/reservas", status_code=201, summary="Reservar stock para un pedido (todo o nada)")
def reservar(body: ReservaIn, request: Request):
    with tx() as con:
        faltantes = []
        for l in body.lineas:
            r = con.execute("SELECT disponible FROM inv_stock WHERE sku=? AND almacen=?", (l.sku, body.almacen)).fetchone()
            disp = r["disponible"] if r else 0
            if disp < l.cantidad:
                faltantes.append({"sku": l.sku, "solicitado": l.cantidad, "disponible": disp})
        if faltantes:
            registrar(request, "SRV02", "reservarStock", body.pedidoRef, "RECHAZADO_SIN_STOCK")
            raise HTTPException(409, {"mensaje": "Stock insuficiente", "faltantes": faltantes})
        for l in body.lineas:
            con.execute("UPDATE inv_stock SET disponible=disponible-?, reservado=reservado+? WHERE sku=? AND almacen=?",
                        (l.cantidad, l.cantidad, l.sku, body.almacen))
        rid = "RES-" + uuid.uuid4().hex[:8].upper()
        con.execute("INSERT INTO inv_reservas VALUES (?,?,?,?,?,?)", (rid, body.pedidoRef, body.almacen, "ACTIVA",
                    json.dumps([l.model_dump() for l in body.lineas]), datetime.now().isoformat(timespec="seconds")))
    registrar(request, "SRV02", "reservarStock", rid, "OK")
    return {"reservaId": rid, "pedidoRef": body.pedidoRef, "almacen": body.almacen, "estado": "ACTIVA"}

@router.delete("/reservas/{reservaId}", summary="Liberar una reserva (anulación o compensación)")
def liberar(reservaId: str, request: Request):
    with tx() as con:
        r = con.execute("SELECT * FROM inv_reservas WHERE reserva_id=?", (reservaId,)).fetchone()
        if not r: raise HTTPException(404, "Reserva no existe")
        if r["estado"] != "ACTIVA": raise HTTPException(409, "La reserva ya no está activa")
        for l in json.loads(r["lineas_json"]):
            con.execute("UPDATE inv_stock SET disponible=disponible+?, reservado=reservado-? WHERE sku=? AND almacen=?",
                        (l["cantidad"], l["cantidad"], l["sku"], r["almacen"]))
        con.execute("UPDATE inv_reservas SET estado='LIBERADA' WHERE reserva_id=?", (reservaId,))
    registrar(request, "SRV02", "liberarReserva", reservaId, "OK")
    return {"reservaId": reservaId, "estado": "LIBERADA"}
