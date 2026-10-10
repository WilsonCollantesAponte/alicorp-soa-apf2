"""SRV05 – Notificaciones. Servicio de utilidad. En el prototipo el envío por
correo/WhatsApp se SIMULA (queda registrado como ENVIADO_SIMULADO)."""
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends
from shared.persistence.db import tx, rows
from shared.domain.modelos import NotificacionIn
from shared.security.seguridad import origen_confiable

router = APIRouter(prefix="/notificaciones", tags=["SRV05 Notificaciones"], dependencies=[Depends(origen_confiable)])

@router.post("", status_code=202, summary="Encolar/enviar una notificación de estado")
def enviar(body: NotificacionIn):
    nid = "NTF-" + uuid.uuid4().hex[:8].upper()
    with tx() as con:
        con.execute("INSERT INTO ntf_notificaciones VALUES (?,?,?,?,?,?,?,?)", (nid, body.pedidoId, body.destinatario, body.medio,
                    body.evento, body.mensaje, "ENVIADO_SIMULADO", datetime.now().isoformat(timespec="seconds")))
    return {"notificacionId": nid, "estado": "ENVIADO_SIMULADO", "medio": body.medio}

@router.get("", summary="Consultar notificaciones emitidas")
def listar(pedidoId: Optional[str] = None, destinatario: Optional[str] = None):
    sql, p = "SELECT notificacion_id AS notificacionId, pedido_id AS pedidoId, destinatario, medio, evento, mensaje, estado, creado_en AS creadoEn FROM ntf_notificaciones WHERE 1=1", []
    if pedidoId: sql += " AND pedido_id=?"; p.append(pedidoId)
    if destinatario: sql += " AND destinatario=?"; p.append(destinatario)
    with tx() as con:
        return rows(con.execute(sql + " ORDER BY creado_en DESC", p))
