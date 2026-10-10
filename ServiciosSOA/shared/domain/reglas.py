"""Reglas de negocio encapsuladas (no expuestas a los consumidores)."""
IGV = 0.18
# Máquina de estados del pedido (TO-BE)
TRANSICIONES = {
    "POR_APROBAR": {"CONFIRMADO", "ANULADO"},
    "CONFIRMADO": {"EN_DESPACHO", "ANULADO"},
    "EN_DESPACHO": {"ENTREGADO"},
    "OBSERVADO_SIN_STOCK": {"ANULADO"},
    "ENTREGADO": set(),
    "ANULADO": set(),
}


def calcular_totales(subtotal: float):
    igv = round(subtotal * IGV, 2)
    return round(subtotal, 2), igv, round(subtotal + igv, 2)


def estado_inicial(total: float, linea_credito: float) -> str:
    """Regla comercial: si el total supera la línea de crédito, el analista de CON01 debe aprobarlo."""
    return "CONFIRMADO" if total <= linea_credito else "POR_APROBAR"


def transicion_valida(actual: str, nuevo: str) -> bool:
    return nuevo in TRANSICIONES.get(actual, set())
