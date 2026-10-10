"""Seguridad básica del prototipo: los servicios solo aceptan tráfico que viene
del ESB o de otro servicio (cabecera X-Origen). En APF3 se reemplaza por JWT."""
from fastapi import Header, HTTPException

ORIGENES_PERMITIDOS = {"ESB", "SRV01", "SRV02", "SRV03", "SRV04", "SRV05", "SRV06", "SWAGGER"}


def origen_confiable(x_origen: str = Header("SWAGGER", description="Quién invoca: ESB, SRVxx o SWAGGER (pruebas)")):
    if x_origen not in ORIGENES_PERMITIDOS:
        raise HTTPException(status_code=403, detail=f"Origen no autorizado: {x_origen}")
    return x_origen
