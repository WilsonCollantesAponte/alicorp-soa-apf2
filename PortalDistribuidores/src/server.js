// PROYECTO 2 – CON02 Portal Distribuidores / Canal moderno (Web Consumidora 2).
// Este servidor solo entrega la interfaz web. Toda la lógica de negocio vive en
// los servicios (Proyecto 3) y se consume por HTTP/JSON a través del ESB.
// No hay ninguna conexión a la base de datos en este proyecto.
const express = require('express');
const path = require('path');

const PORT = process.env.PORT || 3002;
const { construirConfig, aScript } = require('./config');
const config = construirConfig();

const app = express();
app.get('/config.js', (_req, res) => {
  res.type('application/javascript').send(aScript(config));
});
app.use(express.static(path.join(__dirname, '..', 'public')));
app.get('/health', (_req, res) => res.json({ estado: 'UP', proyecto: 'PortalDistribuidores', consumidor: config.consumidor }));
app.listen(PORT, () => console.log(`CON02 Portal Distribuidores en http://127.0.0.1:${PORT} → ESB ${config.esbUrl}`));
