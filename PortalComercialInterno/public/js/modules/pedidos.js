// modules/pedidos, clientes, inventario, despacho (CON01)
const Mod = {
  productos: [],
  async cargarClientes() {
    const cs = await API.get('/clientes');
    document.getElementById('cliente').innerHTML = cs.map(c => `<option value="${c.clienteId}">${c.clienteId} · ${c.razonSocial}${c.estado !== 'ACTIVO' ? ' [' + c.estado + ']' : ''}</option>`).join('');
  },
  async cargarCatalogo() {
    this.productos = await API.get('/catalogo/productos');
    document.getElementById('prod').innerHTML = this.productos.map((p, i) => `<tr><td>${p.sku}</td><td>${p.nombre}</td><td>${p.marca}</td>
      <td class="num">${soles(p.precio)}</td><td class="num"><input class="qty" type="number" min="0" value="0" data-i="${i}" data-sku="${p.sku}"></td><td class="num" id="imp${i}">S/ 0.00</td></tr>`).join('');
    document.querySelectorAll('.qty').forEach(q => q.addEventListener('input', () => this.recalcular()));
  },
  recalcular() {
    let s = 0;
    document.querySelectorAll('.qty').forEach(q => { const p = this.productos[q.dataset.i]; const imp = p.precio * (+q.value || 0); s += imp; document.getElementById('imp' + q.dataset.i).textContent = soles(imp); });
    document.getElementById('tot').textContent = 'Subtotal: ' + soles(s) + ' (sin IGV)';
  },
  async registrar() {
    const lineas = [...document.querySelectorAll('.qty')].filter(q => +q.value > 0).map(q => ({ sku: this.productos[q.dataset.i].sku, cantidad: +q.value }));
    const out = document.getElementById('resultado');
    if (!lineas.length) { out.innerHTML = '<div class="res err">Agrega al menos un producto.</div>'; return; }
    try {
      const p = await API.post('/pedidos', { clienteId: cliente.value, lineas, fechaRequerida: fecha.value || null, observacion: obs.value || null });
      out.innerHTML = `<div class="res"><b>Pedido ${p.pedidoId}</b> ${badge(p.estado)} · ${p.razonSocial}<br>Subtotal ${soles(p.subtotal)} · IGV ${soles(p.igv)} · <b>Total ${soles(p.total)}</b> · Reserva ${p.reservaId}</div>`;
    } catch (e) {
      const d = e.data || {};
      out.innerHTML = `<div class="res err"><b>No se pudo registrar (${e.status}).</b> ${d.pedidoId ? d.pedidoId + ' ' + badge(d.estado) + '<br>' : ''}${d.detalle ? JSON.stringify(d.detalle.faltantes) : e.message}</div>`;
    }
  },
  async listarPedidos() {
    const ps = await API.get('/pedidos');
    document.getElementById('ped').innerHTML = ps.map(p => `<tr><td>${p.pedidoId}</td><td>${p.razonSocial}</td><td>${p.origen}</td><td>${badge(p.estado)}</td><td class="num">${soles(p.total)}</td><td>
      ${p.estado === 'POR_APROBAR' ? `<button class="btn sm sec" onclick="Mod.estado('${p.pedidoId}','CONFIRMADO')">Aprobar</button> ` : ''}
      ${p.estado === 'CONFIRMADO' ? `<button class="btn sm" onclick="Mod.despachar('${p.pedidoId}')">Programar despacho</button> ` : ''}
      ${['POR_APROBAR', 'CONFIRMADO', 'OBSERVADO_SIN_STOCK'].includes(p.estado) ? `<button class="btn sm gh" onclick="Mod.estado('${p.pedidoId}','ANULADO')">Anular</button>` : ''}</td></tr>`).join('');
  },
  async estado(id, estado) {
    try { await API.patch(`/pedidos/${id}/estado`, { estado }); msgPed.innerHTML = `<div class="res">${id} → ${badge(estado)}</div>`; } catch (e) { msgPed.innerHTML = `<div class="res err">${e.message}</div>`; }
    this.listarPedidos();
  },
  async despachar(id) {
    const f = new Date(Date.now() + 3 * 864e5).toISOString().slice(0, 10);
    try { const d = await API.post('/despachos', { pedidoId: id, fechaProgramada: f, placa: 'P1A-123' }); msgPed.innerHTML = `<div class="res">Despacho <b>${d.despachoId}</b> ${badge(d.estado)} para ${d.fechaProgramada} · Guía ${d.guiaRemision} · ${d.transportista}</div>`; } catch (e) { msgPed.innerHTML = `<div class="res err">${e.message}</div>`; }
    this.listarPedidos();
  },
  async stock() {
    const s = await API.get('/inventario/stock?almacen=' + alm.value);
    stk.innerHTML = s.map(x => `<tr><td>${x.sku}</td><td>${x.nombre}</td><td>${x.almacen}</td><td class="num">${x.disponible}</td><td class="num">${x.reservado}</td></tr>`).join('');
  },
  async notif() {
    const n = await API.get('/notificaciones');
    ntf.innerHTML = n.map(x => `<tr><td>${x.pedidoId || '-'}</td><td>${x.evento}</td><td>${x.medio}</td><td>${x.destinatario}</td><td>${badge(x.estado)}</td></tr>`).join('');
  },
};
