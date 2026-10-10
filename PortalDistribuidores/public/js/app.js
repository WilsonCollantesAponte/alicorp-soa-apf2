const usados = new Set();
APP_CONFIG.cliente = document.getElementById('dist').value;
document.getElementById('dist').onchange = (e) => { APP_CONFIG.cliente = e.target.value; Tienda.carrito = {}; Tienda.pintar(); activa(); };
document.addEventListener('esb:respuesta', (e) => {
  const m = e.detail; if (m.servicio) usados.add(m.servicio);
  document.getElementById('meta').textContent = JSON.stringify(m, null, 2);
  document.getElementById('svcUsados').innerHTML = [...usados].sort().map(s => `<span>${s}</span>`).join('');
});
const vistas = { catalogo: () => Tienda.catalogo(), mis: () => Tienda.mis(), cuenta: () => Tienda.cuenta() };
let actual = 'catalogo';
function activa() { vistas[actual](); }
document.querySelectorAll('#tabs button').forEach(b => b.onclick = () => {
  actual = b.dataset.t;
  document.querySelectorAll('#tabs button').forEach(x => x.classList.toggle('act', x === b));
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('hidden', !(t.id === 't-' + actual || (actual === 'catalogo' && t.id === 't-carrito'))));
  activa();
});
document.getElementById('enviar').onclick = () => Tienda.enviar();
Tienda.catalogo();
