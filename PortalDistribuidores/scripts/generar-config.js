// Build para Vercel (sitio estático): genera public/config.js a partir de ESB_URL, API_KEY, USUARIO.
const fs = require('fs');
const path = require('path');
const { construirConfig, aScript } = require('../src/config');

const cfg = construirConfig();
fs.writeFileSync(path.join(__dirname, '..', 'public', 'config.js'), aScript(cfg));
console.log(`public/config.js generado → ESB ${cfg.esbUrl} (${cfg.consumidor})`);
