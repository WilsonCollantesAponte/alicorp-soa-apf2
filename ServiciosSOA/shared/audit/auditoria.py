"""Trazabilidad de operaciones (quién, cuándo, qué, resultado). RNF07."""
from datetime import datetime
from fastapi import Request
from shared.persistence.db import tx


def registrar(request: Request | None, servicio: str, operacion: str, recurso: str, resultado: str):
    h = request.headers if request else {}
    with tx() as con:
        con.execute(
            "INSERT INTO aud_operaciones (fecha_hora,usuario,canal,servicio,operacion,recurso,resultado,correlation_id) VALUES (?,?,?,?,?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), h.get("x-usuario", "sistema"), h.get("x-canal", "INTERNO"),
             servicio, operacion, recurso, resultado, h.get("x-correlation-id", "-")))
