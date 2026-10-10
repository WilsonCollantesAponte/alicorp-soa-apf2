# PROYECTO 2 – CON02 Portal Distribuidores / Canal moderno (Web Consumidora 2)

Usuario: distribuidor o cliente del canal moderno. Proyecto independiente (Node.js + Express + HTML/JS).
No accede a la base de datos: consume los servicios por HTTP/JSON a través del ESB, con su propia API key.
Envía los pedidos en el formato del distribuidor (`codigo`/`cant`); el ESB los transforma al modelo canónico.

```bash
npm install
npm start            # http://127.0.0.1:3002  (requiere ESB en :8080)
```

### Despliegue en Vercel (sitio estático)
Root Directory: esta carpeta. `vercel.json` ya define `npm run build` → `public/`.
El build genera `public/config.js` desde `ESB_URL` (URL del proyecto ServiciosSOA, p. ej. `https://<servicios>.vercel.app`), `API_KEY` y `USUARIO`.
