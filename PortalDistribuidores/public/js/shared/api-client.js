// shared/api-client: único punto de salida hacia la capa de servicios (vía ESB).
const API = (() => {
  const cfg = window.APP_CONFIG;
  let ultimaMeta = null;
  async function llamar(metodo, ruta, cuerpo) {
    const res = await fetch(`${cfg.esbUrl}${ruta}`, {
      method: metodo,
      headers: { 'Content-Type': 'application/json', 'X-Api-Key': cfg.apiKey, 'X-Usuario': cfg.usuario,
                 ...(cfg.cliente ? { 'X-Cliente': cfg.cliente } : {}) },
      body: cuerpo ? JSON.stringify(cuerpo) : undefined,
    });
    const sobre = await res.json();
    ultimaMeta = { status: res.status, metodo, ruta, ...sobre.meta };
    document.dispatchEvent(new CustomEvent('esb:respuesta', { detail: ultimaMeta }));
    if (!sobre.ok) { const e = new Error(typeof sobre.data?.error === 'string' ? sobre.data.error : JSON.stringify(sobre.data?.error || sobre.data)); e.data = sobre.data; e.status = res.status; throw e; }
    return sobre.data;
  }
  return { get: (r) => llamar('GET', r), post: (r, b) => llamar('POST', r, b), patch: (r, b) => llamar('PATCH', r, b), meta: () => ultimaMeta };
})();
const soles = (n) => 'S/ ' + Number(n).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const badge = (e) => `<span class="badge b-${e}">${e.replaceAll('_', ' ')}</span>`;
