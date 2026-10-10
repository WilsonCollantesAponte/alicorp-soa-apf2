"""SRV06 – Catálogo/Precios. Servicio de entidad/negocio."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from shared.persistence.db import tx, rows
from shared.domain.modelos import CotizacionIn
from shared.security.seguridad import origen_confiable

router = APIRouter(prefix="/catalogo", tags=["SRV06 Catálogo/Precios"], dependencies=[Depends(origen_confiable)])

@router.get("/productos", summary="Listar productos con precio vigente por canal")
def productos(canal: str = Query("INTERNO", examples=["DISTRIBUIDOR"]), categoria: Optional[str] = None, q: Optional[str] = None):
    sql = """SELECT p.sku,p.nombre,p.marca,p.categoria,p.presentacion,p.unidad,pr.precio,pr.moneda
             FROM cat_productos p JOIN cat_precios pr ON pr.sku=p.sku AND pr.canal=? WHERE p.activo=1"""
    prm = [canal]
    if categoria: sql += " AND p.categoria=?"; prm.append(categoria)
    if q: sql += " AND (p.nombre LIKE ? OR p.marca LIKE ?)"; prm += [f"%{q}%", f"%{q}%"]
    with tx() as con:
        return [{**r, "canal": canal} for r in rows(con.execute(sql + " ORDER BY p.sku", prm))]

@router.get("/productos/{sku}", summary="Obtener producto y precios de todos los canales")
def producto(sku: str):
    with tx() as con:
        p = con.execute("SELECT * FROM cat_productos WHERE sku=?", (sku,)).fetchone()
        if not p: raise HTTPException(404, f"SKU {sku} no existe")
        precios = rows(con.execute("SELECT canal,precio,moneda,vigente_desde AS vigenteDesde FROM cat_precios WHERE sku=?", (sku,)))
    return {**dict(p), "precios": precios}

@router.post("/cotizaciones", summary="Valorizar líneas de pedido según el canal")
def cotizar(body: CotizacionIn):
    lineas, subtotal = [], 0.0
    with tx() as con:
        for l in body.lineas:
            r = con.execute("""SELECT p.nombre,pr.precio FROM cat_productos p JOIN cat_precios pr
                               ON pr.sku=p.sku AND pr.canal=? WHERE p.sku=? AND p.activo=1""", (body.canal, l.sku)).fetchone()
            if not r: raise HTTPException(422, f"SKU {l.sku} no disponible para canal {body.canal}")
            imp = round(r["precio"] * l.cantidad, 2); subtotal += imp
            lineas.append({"sku": l.sku, "descripcion": r["nombre"], "cantidad": l.cantidad, "precioUnitario": r["precio"], "importe": imp})
    return {"canal": body.canal, "moneda": "PEN", "lineas": lineas, "subtotal": round(subtotal, 2)}
