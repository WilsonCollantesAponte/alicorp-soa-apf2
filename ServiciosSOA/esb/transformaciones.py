"""Transformaciones de mensajes del ESB (formato del consumidor ⇄ modelo canónico)."""


def pedido_distribuidor_a_canonico(ctx, body, params):
    """CON02 envía su pedido en el formato del distribuidor; el ESB lo convierte al
    modelo canónico que entiende SRV01."""
    if ctx["metodo"] == "POST" and isinstance(body, dict) and "items" in body:
        entrega = body.get("entrega") or {}
        body = {
            "clienteId": body.get("codigoDistribuidor") or ctx["cliente"],
            "canal": "DISTRIBUIDOR",
            "origen": "CON02",
            "lineas": [{"sku": i["codigo"], "cantidad": int(i["cant"])} for i in body["items"]],
            "fechaRequerida": entrega.get("fecha"),
            "direccionEntrega": entrega.get("direccion"),
            "observacion": body.get("comentario"),
            "usuario": ctx["usuario"],
        }
        ctx["transformado"].append("pedido_distribuidor_a_canonico")
    return body, params


def completar_origen_canal(ctx, body, params):
    if ctx["metodo"] == "POST" and isinstance(body, dict) and ctx["subruta"] == "":
        body.setdefault("origen", "CON01")
        body.setdefault("canal", ctx["canal"])
        body.setdefault("usuario", ctx["usuario"])
        ctx["transformado"].append("completar_origen_canal")
    return body, params


def filtrar_por_distribuidor(ctx, body, params):
    """Un distribuidor solo ve SUS pedidos y SUS datos (seguridad por contexto)."""
    if ctx["metodo"] == "GET" and ctx["cliente"]:
        if ctx["prefijo"] == "pedidos" and ctx["subruta"] == "":
            params["clienteId"] = ctx["cliente"]
        if ctx["prefijo"] == "clientes" and ctx["subruta"] == "":
            ctx["subruta"] = "/" + ctx["cliente"]
        ctx["transformado"].append("filtrar_por_distribuidor")
    return body, params


def forzar_canal_consumidor(ctx, body, params):
    """El precio depende del canal del consumidor: CON01 → INTERNO, CON02 → DISTRIBUIDOR."""
    if ctx["metodo"] == "GET" and ctx["subruta"].startswith("/productos") and ctx["consumidor"] == "CON02":
        params["canal"] = "DISTRIBUIDOR"
    elif ctx["metodo"] == "GET" and ctx["subruta"].startswith("/productos"):
        params.setdefault("canal", ctx["canal"])
    if ctx["metodo"] == "POST" and isinstance(body, dict) and ctx["consumidor"] == "CON02":
        body["canal"] = "DISTRIBUIDOR"
    ctx["transformado"].append("forzar_canal_consumidor")
    return body, params


REGISTRO = {f.__name__: f for f in (pedido_distribuidor_a_canonico, completar_origen_canal, filtrar_por_distribuidor, forzar_canal_consumidor)}
