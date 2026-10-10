"""Modelos canónicos (contratos JSON) compartidos por los servicios."""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

Canal = Literal["INTERNO", "DISTRIBUIDOR", "MODERNO"]


class LineaPedido(BaseModel):
    sku: str = Field(..., examples=["ALI-ACE-0001"])
    cantidad: int = Field(..., gt=0, examples=[20])


class PedidoIn(BaseModel):
    clienteId: str = Field(..., examples=["CLI-0001"])
    canal: Canal = Field(..., examples=["INTERNO"])
    origen: Literal["CON01", "CON02"] = Field(..., examples=["CON01"])
    lineas: List[LineaPedido] = Field(..., min_length=1)
    fechaRequerida: Optional[str] = Field(None, examples=["2026-10-16"])
    direccionEntrega: Optional[str] = None
    observacion: Optional[str] = None
    usuario: Optional[str] = Field(None, examples=["vendedor.piura01"])


class EstadoPedidoIn(BaseModel):
    estado: Literal["CONFIRMADO", "ANULADO", "EN_DESPACHO", "ENTREGADO"]
    motivo: Optional[str] = None


class ClienteIn(BaseModel):
    clienteId: str
    razonSocial: str
    ruc: str = Field(..., pattern=r"^\d{11}$")
    tipo: Literal["DISTRIBUIDOR", "CANAL_MODERNO", "MAYORISTA"]
    canal: Canal
    ciudad: Optional[str] = None
    direccion: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    lineaCredito: float = 0


class ReservaIn(BaseModel):
    pedidoRef: str = Field(..., examples=["PRE-20261010-0001"])
    almacen: str = Field("CD-PIURA", examples=["CD-PIURA"])
    lineas: List[LineaPedido]


class CotizacionIn(BaseModel):
    canal: Canal
    lineas: List[LineaPedido]


class DespachoIn(BaseModel):
    pedidoId: str = Field(..., examples=["PED-000001"])
    fechaProgramada: str = Field(..., examples=["2026-10-15"])
    transportista: str = Field("Transportes Ruta Norte (ficticio)")
    placa: Optional[str] = Field(None, examples=["P1A-123"])
    almacenOrigen: str = "CD-PIURA"
    direccion: Optional[str] = None


class EstadoDespachoIn(BaseModel):
    estado: Literal["PROGRAMADO", "EN_RUTA", "ENTREGADO", "INCIDENCIA"]


class NotificacionIn(BaseModel):
    pedidoId: Optional[str] = None
    destinatario: str = Field(..., examples=["pedidos@dnortepiura.test"])
    medio: Literal["EMAIL", "WHATSAPP"] = "EMAIL"
    evento: str = Field(..., examples=["PEDIDO_REGISTRADO"])
    mensaje: str
