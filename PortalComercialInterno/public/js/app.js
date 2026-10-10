const usados = new Set();
document.getElementById('usr').textContent = '👤 ' + APP_CONFIG.usuario + ' · ' + APP_CONFIG.consumidor;
document.addEventListener('esb:respuesta', (e) => {
  const m = e.detail; if (m.servicio) usados.add(m.servicio);
  document.getElementById('meta').textContent = JSON.stringify(m, null, 2);
  document.getElementById('svcUsados').innerHTML = [...usados].sort().map(s => `<span>${s}</span>`).join('');
});
const vistas = { registrar: () => {}, pedidos: () => Mod.listarPedidos(), stock: () => Mod.stock(), notif: () => Mod.notif() };
document.querySelectorAll('#tabs button').forEach(b => b.onclick = () => {
  document.querySelectorAll('#tabs button').forEach(x => x.classList.toggle('act', x === b));
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('hidden', t.id !== 't-' + b.dataset.t));
  vistas[b.dataset.t]();
});
document.getElementById('enviar').onclick = () => Mod.registrar();
document.getElementById('alm').onchange = () => Mod.stock();
(async () => { await Mod.cargarClientes(); await Mod.cargarCatalogo(); })();
