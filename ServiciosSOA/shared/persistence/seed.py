"""Datos de prueba ACADÉMICOS (ficticios). No son datos internos de Alicorp.
Las marcas se usan solo como referencia del portafolio público de consumo masivo;
SKU, precios, stock y clientes son inventados para el prototipo."""
from datetime import date
from shared.persistence.db import tx, init_db, ES_POSTGRES

CLIENTES = [
    ("CLI-0001", "Distribuidora Norte Piura S.A.C. (ficticia)", "20600000011", "DISTRIBUIDOR", "DISTRIBUIDOR", "Piura", "Av. Sánchez Cerro 1250, Piura", "pedidos@dnortepiura.test", "073-000111", 85000),
    ("CLI-0002", "Comercial Sullana Express E.I.R.L. (ficticia)", "20600000022", "DISTRIBUIDOR", "DISTRIBUIDOR", "Sullana", "Calle San Martín 455, Sullana", "compras@sullanaexpress.test", "073-000222", 40000),
    ("CLI-0003", "Supermercados del Pacífico S.A. (ficticia)", "20600000033", "CANAL_MODERNO", "MODERNO", "Piura", "Av. Grau 1800, Piura", "abastecimiento@superpacifico.test", "073-000333", 150000),
    ("CLI-0004", "Mayorista Chiclayo Centro S.A.C. (ficticia)", "20600000044", "MAYORISTA", "INTERNO", "Chiclayo", "Av. Balta 990, Chiclayo", "ventas@maychiclayo.test", "074-000444", 60000),
    ("CLI-0005", "Distribuidora Tumbes Frontera S.R.L. (ficticia)", "20600000055", "DISTRIBUIDOR", "DISTRIBUIDOR", "Tumbes", "Av. Tumbes Norte 310, Tumbes", "logistica@tumbesfrontera.test", "072-000555", 0),
]
CLIENTES_ESTADO = {"CLI-0005": "SUSPENDIDO"}

PRODUCTOS = [  # sku, nombre, marca, categoría, presentación
    ("ALI-ACE-0001", "Aceite vegetal 900 ml x 12", "Primor", "Aceites", "Caja 12 und"),
    ("ALI-ACE-0002", "Aceite vegetal 1 L x 12", "Cocinero", "Aceites", "Caja 12 und"),
    ("ALI-FID-0001", "Fideo spaghetti 500 g x 20", "Don Vittorio", "Pastas", "Caja 20 und"),
    ("ALI-FID-0002", "Fideo tallarín 1 kg x 10", "Lavaggi", "Pastas", "Caja 10 und"),
    ("ALI-HAR-0001", "Harina preparada 1 kg x 10", "Blanca Flor", "Harinas", "Caja 10 und"),
    ("ALI-SAL-0001", "Mayonesa 475 g x 12", "Alacena", "Salsas", "Caja 12 und"),
    ("ALI-DET-0001", "Detergente 2.6 kg x 6", "Bolívar", "Cuidado del hogar", "Caja 6 und"),
    ("ALI-GAL-0001", "Galleta soda 6 pack x 12", "Casino", "Galletas", "Caja 12 pack"),
]
# Precio base de referencia (PEN, inventado) y factor por canal
BASE = {"ALI-ACE-0001": 98.40, "ALI-ACE-0002": 92.10, "ALI-FID-0001": 58.00, "ALI-FID-0002": 49.50,
        "ALI-HAR-0001": 61.20, "ALI-SAL-0001": 88.80, "ALI-DET-0001": 132.00, "ALI-GAL-0001": 54.60}
FACTOR = {"INTERNO": 1.00, "DISTRIBUIDOR": 0.94, "MODERNO": 0.97}
STOCK = {"ALI-ACE-0001": 1200, "ALI-ACE-0002": 800, "ALI-FID-0001": 2500, "ALI-FID-0002": 900,
         "ALI-HAR-0001": 650, "ALI-SAL-0001": 40, "ALI-DET-0001": 300, "ALI-GAL-0001": 1500}


def seed(reset: bool = False):
    """Crea el esquema (si no existe) y carga los datos de prueba (si la BD está vacía).
    Es idempotente: se puede llamar en cada arranque (local o función de Vercel)."""
    with tx() as con:
        if ES_POSTGRES:  # evita que dos instancias serverless creen/siembren a la vez
            con.execute("SELECT pg_advisory_xact_lock(20262002)")
        init_db(con)
        if reset:
            for t in ["aud_operaciones", "ntf_notificaciones", "des_despachos", "ped_lineas", "ped_pedidos",
                      "inv_reservas", "inv_stock", "cat_precios", "cat_productos", "cli_clientes"]:
                con.execute(f"DELETE FROM {t}")
        if con.execute("SELECT COUNT(*) FROM cli_clientes").fetchone()[0]:
            return False
        for c in CLIENTES:
            con.execute("INSERT INTO cli_clientes (cliente_id,razon_social,ruc,tipo,canal,ciudad,direccion,email,telefono,linea_credito,estado) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (*c, CLIENTES_ESTADO.get(c[0], "ACTIVO")))
        hoy = date.today().isoformat()
        for p in PRODUCTOS:
            con.execute("INSERT INTO cat_productos (sku,nombre,marca,categoria,presentacion) VALUES (?,?,?,?,?)", p)
            for canal, f in FACTOR.items():
                con.execute("INSERT INTO cat_precios VALUES (?,?,?,?,?)", (p[0], canal, round(BASE[p[0]] * f, 2), "PEN", hoy))
            con.execute("INSERT INTO inv_stock VALUES (?,?,?,0)", (p[0], "CD-PIURA", STOCK[p[0]]))
            con.execute("INSERT INTO inv_stock VALUES (?,?,?,0)", (p[0], "CD-CALLAO", STOCK[p[0]] * 4))
    return True


if __name__ == "__main__":
    import sys
    print("Semilla cargada" if seed(reset="--reset" in sys.argv) else "La BD ya tenía datos")
