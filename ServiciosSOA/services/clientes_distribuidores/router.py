"""SRV03 – Clientes/Distribuidores. Servicio de entidad (datos maestros)."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from shared.persistence.db import tx, rows
from shared.domain.modelos import ClienteIn
from shared.security.seguridad import origen_confiable
from shared.audit.auditoria import registrar

router = APIRouter(prefix="/clientes", tags=["SRV03 Clientes/Distribuidores"], dependencies=[Depends(origen_confiable)])

def _map(r):
    return {"clienteId": r["cliente_id"], "razonSocial": r["razon_social"], "ruc": r["ruc"], "tipo": r["tipo"],
            "canal": r["canal"], "ciudad": r["ciudad"], "direccion": r["direccion"], "email": r["email"],
            "telefono": r["telefono"], "lineaCredito": r["linea_credito"], "estado": r["estado"]}

@router.get("", summary="Listar clientes/distribuidores")
def listar(tipo: Optional[str] = Query(None, examples=["DISTRIBUIDOR"]), ciudad: Optional[str] = None, q: Optional[str] = None):
    sql, p = "SELECT * FROM cli_clientes WHERE 1=1", []
    if tipo: sql += " AND tipo=?"; p.append(tipo)
    if ciudad: sql += " AND ciudad=?"; p.append(ciudad)
    if q: sql += " AND (razon_social LIKE ? OR ruc LIKE ?)"; p += [f"%{q}%", f"%{q}%"]
    with tx() as con:
        return [_map(r) for r in rows(con.execute(sql + " ORDER BY cliente_id", p))]

@router.get("/{clienteId}", summary="Obtener cliente por código")
def obtener(clienteId: str):
    with tx() as con:
        r = con.execute("SELECT * FROM cli_clientes WHERE cliente_id=?", (clienteId,)).fetchone()
    if not r:
        raise HTTPException(404, f"Cliente {clienteId} no existe")
    return _map(r)

@router.get("/{clienteId}/validacion", summary="Validar si el cliente puede generar pedidos")
def validar(clienteId: str):
    c = obtener(clienteId)
    motivos = []
    if c["estado"] != "ACTIVO": motivos.append(f"Cliente {c['estado'].lower()}")
    if c["lineaCredito"] <= 0: motivos.append("Sin línea de crédito disponible")
    return {"clienteId": clienteId, "habilitado": not motivos, "canal": c["canal"], "motivos": motivos,
            "email": c["email"], "direccion": c["direccion"]}

@router.post("", status_code=201, summary="Registrar cliente/distribuidor")
def crear(body: ClienteIn, request: Request):
    with tx() as con:
        if con.execute("SELECT 1 FROM cli_clientes WHERE cliente_id=?", (body.clienteId,)).fetchone():
            raise HTTPException(409, "El cliente ya existe")
        con.execute("INSERT INTO cli_clientes (cliente_id,razon_social,ruc,tipo,canal,ciudad,direccion,email,telefono,linea_credito) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (body.clienteId, body.razonSocial, body.ruc, body.tipo, body.canal, body.ciudad, body.direccion, body.email, body.telefono, body.lineaCredito))
    registrar(request, "SRV03", "crearCliente", body.clienteId, "OK")
    return obtener(body.clienteId)
