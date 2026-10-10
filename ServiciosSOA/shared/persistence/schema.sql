-- BD empresarial compartida (estrategia definida en APF1, sección 3.8).
-- SQLite no maneja esquemas: cada dominio se separa con un prefijo de tabla.
-- Solo el Proyecto 3 (Servicios SOA) accede a esta base. Los portales nunca.

CREATE TABLE IF NOT EXISTS cli_clientes (
  cliente_id TEXT PRIMARY KEY, razon_social TEXT NOT NULL, ruc TEXT NOT NULL,
  tipo TEXT NOT NULL CHECK (tipo IN ('DISTRIBUIDOR','CANAL_MODERNO','MAYORISTA')),
  canal TEXT NOT NULL CHECK (canal IN ('INTERNO','DISTRIBUIDOR','MODERNO')),
  ciudad TEXT, direccion TEXT, email TEXT, telefono TEXT,
  linea_credito REAL DEFAULT 0, estado TEXT DEFAULT 'ACTIVO');

CREATE TABLE IF NOT EXISTS cat_productos (
  sku TEXT PRIMARY KEY, nombre TEXT NOT NULL, marca TEXT, categoria TEXT,
  presentacion TEXT, unidad TEXT DEFAULT 'CJA', activo INTEGER DEFAULT 1);

CREATE TABLE IF NOT EXISTS cat_precios (
  sku TEXT REFERENCES cat_productos(sku), canal TEXT, precio REAL,
  moneda TEXT DEFAULT 'PEN', vigente_desde TEXT, PRIMARY KEY (sku, canal));

CREATE TABLE IF NOT EXISTS inv_stock (
  sku TEXT REFERENCES cat_productos(sku), almacen TEXT, disponible INTEGER,
  reservado INTEGER DEFAULT 0, PRIMARY KEY (sku, almacen));

CREATE TABLE IF NOT EXISTS inv_reservas (
  reserva_id TEXT PRIMARY KEY, pedido_ref TEXT, almacen TEXT, estado TEXT,
  lineas_json TEXT, creado_en TEXT);

CREATE TABLE IF NOT EXISTS ped_pedidos (
  pedido_id TEXT PRIMARY KEY, cliente_id TEXT REFERENCES cli_clientes(cliente_id),
  canal TEXT, origen TEXT, estado TEXT, subtotal REAL, igv REAL, total REAL,
  reserva_id TEXT, fecha_requerida TEXT, direccion_entrega TEXT, observacion TEXT,
  creado_por TEXT, creado_en TEXT, actualizado_en TEXT);

CREATE TABLE IF NOT EXISTS ped_lineas (
  pedido_id TEXT REFERENCES ped_pedidos(pedido_id), item INTEGER, sku TEXT,
  descripcion TEXT, cantidad INTEGER, precio_unitario REAL, importe REAL,
  PRIMARY KEY (pedido_id, item));

CREATE TABLE IF NOT EXISTS des_despachos (
  despacho_id TEXT PRIMARY KEY, pedido_id TEXT REFERENCES ped_pedidos(pedido_id),
  almacen_origen TEXT, transportista TEXT, placa TEXT, fecha_programada TEXT,
  direccion TEXT, estado TEXT, guia_remision TEXT, creado_en TEXT, actualizado_en TEXT);

CREATE TABLE IF NOT EXISTS ntf_notificaciones (
  notificacion_id TEXT PRIMARY KEY, pedido_id TEXT, destinatario TEXT, medio TEXT,
  evento TEXT, mensaje TEXT, estado TEXT, creado_en TEXT);

CREATE TABLE IF NOT EXISTS aud_operaciones (
  id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_hora TEXT, usuario TEXT, canal TEXT,
  servicio TEXT, operacion TEXT, recurso TEXT, resultado TEXT, correlation_id TEXT);
