// Configuración del portal (CON02). Única fuente: variables de entorno.
// La usan el servidor local (src/server.js) y el build estático de Vercel (scripts/generar-config.js).
// El portal solo conoce la URL del ESB: nunca la base de datos.
function normalizarEsb(url) {
  const u = (url || 'http://127.0.0.1:8080').trim().replace(/\/+$/, '');
  return u.endsWith('/esb/v1') ? u : `${u}/esb/v1`; // acepta la URL base o la URL con /esb/v1
}

function construirConfig(env = process.env) {
  return {
    consumidor: env.CONSUMIDOR || 'CON02',
    nombre: 'Portal Distribuidores',
    esbUrl: normalizarEsb(env.ESB_URL),
    apiKey: env.API_KEY || 'con02-demo-key',
    usuario: env.USUARIO || 'usuario.distribuidor',
  };
}

const aScript = (cfg) => `window.APP_CONFIG = ${JSON.stringify(cfg)};\n`;

module.exports = { construirConfig, aScript };
