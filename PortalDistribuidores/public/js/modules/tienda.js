// modules/catalogo, mis-pedidos, tracking (CON02)
const Tienda = {
  cat: [], carrito: {},
  async catalogo() {
    this.cat = await API.get('/catalogo/productos');
    document.getElementById('cat').innerHTML = this.cat.map((p, i) => `<div class="prod"><div class="m">${p.marca} · ${p.categoria}</div><div class="n">${p.nombre}</div>
      <div class="p">${soles(p.precio)}</div><div class="r"><input class="qty" type="number" min="1" value="10" id="q${i}" data-sku="${p.sku}"><button class="btn sm" id="b-${p.sku}" onclick="Tienda.agregar(${i})">Agregar</button></div></div>`).join('');
  },
  agregar(i) { const p = this.cat[i]; this.carrito[p.sku] = (this.carrito[p.sku] || 0) + (+document.getElementById('q' + i).value || 0); this.pintar(); },
  pintar() {
    let s = 0; const filas = Object.entries(this.carrito).map(([sku, c]) => { const p = this.cat.find(x => x.sku === sku); s += p.precio * c; return `<tr><td>${sku}</td><td>${p.nombre}</td><td class="num">${c}</td><td class="num">${soles(p.precio * c)}</td></tr>`; });
    car.innerHTML = filas.join('') || '<tr><td colspan="4">Vacío</td></tr>'; tot.textContent = 'Subtotal: ' + soles(s) + ' (sin IGV)';
  },
  async enviar() {
    // Formato propio del distribuidor (codigo/cant). El ESB lo convierte al modelo canónico.
    const pedido = { codigoDistribuidor: APP_CONFIG.cliente, items: Object.entries(this.carrito).map(([codigo, cant]) => ({ codigo, cant })),
                     entrega: { fecha: fecha.value || null }, comentario: com.value || null };
    if (!pedido.items.length) { resultado.innerHTML = '<div class="res err">El pedido está vacío.</div>'; return; }
    try {
      const p = await API.post('/pedidos', pedido);
      resultado.innerHTML = `<div class="res">¡Pedido enviado! <b>${p.pedidoId}</b> ${badge(p.estado)} · Total ${soles(p.total)} (IGV incluido). Te avisaremos por WhatsApp.</div>`;
      this.carrito = {}; this.pintar();
    } catch (e) { const d = e.data || {}; resultado.innerHTML = `<div class="res err"><b>Pedido no aceptado (${e.status})</b> ${d.pedidoId ? d.pedidoId + ' ' + badge(d.estado) : ''}<br>${d.detalle ? d.detalle.mensaje + ': ' + d.detalle.faltantes.map(f => `${f.sku} pediste ${f.solicitado}, hay ${f.disponible}`).join('; ') : e.message}</div>`; }
  },
  async mis() {
    const ps = await API.get('/pedidos');
    mis.innerHTML = ps.map(p => `<tr><td>${p.pedidoId}</td><td>${p.creadoEn.replace('T', ' ')}</td><td>${badge(p.estado)}</td><td class="num">${soles(p.total)}</td><td><button class="btn sm sec" onclick="Tienda.tracking('${p.pedidoId}','${p.estado}')">Tracking</button></td></tr>`).join('') || '<tr><td colspan="5">Sin pedidos</td></tr>';
  },
  async tracking(id, estado) {
    const ds = await API.get('/despachos?pedidoId=' + id);
    const d = ds[0];
    const pasos = [['Pedido registrado', true], ['Confirmado y stock reservado', ['CONFIRMADO', 'EN_DESPACHO', 'ENTREGADO'].includes(estado)], ['Despacho programado', !!d], ['En ruta', d && ['EN_RUTA', 'ENTREGADO'].includes(d.estado)], ['Entregado', d && d.estado === 'ENTREGADO']];
    track.innerHTML = `<div class="res" style="background:#f8fafc;border-color:#0F5132"><b>Tracking ${id}</b>${d ? ` · ${d.despachoId} · ${d.transportista} · placa ${d.placa || '-'} · fecha ${d.fechaProgramada} · guía ${d.guiaRemision}` : ''}
      ${pasos.map(([t, on]) => `<div class="step"><div class="dot ${on ? 'on' : ''}"></div>${t}</div>`).join('')}</div>`;
  },
  async cuenta() {
    const c = await API.get('/clientes');
    cuenta.innerHTML = `<table><tr><th>Código</th><td>${c.clienteId}</td><th>RUC</th><td>${c.ruc}</td></tr><tr><th>Razón social</th><td>${c.razonSocial}</td><th>Tipo</th><td>${c.tipo}</td></tr>
      <tr><th>Dirección</th><td>${c.direccion}</td><th>Línea de crédito</th><td>${soles(c.lineaCredito)}</td></tr></table>`;
    const n = await API.get('/notificaciones?destinatario=' + encodeURIComponent(c.email));
    ntf.innerHTML = n.map(x => `<tr><td>${x.pedidoId || '-'}</td><td>${x.evento}</td><td>${x.medio}</td><td>${x.mensaje}</td></tr>`).join('') || '<tr><td colspan="4">Sin notificaciones</td></tr>';
  },
};
