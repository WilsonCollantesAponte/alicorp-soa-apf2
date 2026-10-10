# PROYECTO 1 – CON01 Portal Comercial Interno (Web Consumidora 1)

Usuario: analista / vendedor interno de Alicorp. Proyecto independiente (Node.js + Express + HTML/JS).
No accede a la base de datos: consume SRV01–SRV06 únicamente por HTTP/JSON a través del ESB.

```bash
npm install
npm start            # http://127.0.0.1:3001  (requiere ESB en :8080)
```
Variables (ver `.env.example`): `PORT`, `ESB_URL`, `API_KEY`, `USUARIO`.

### Despliegue en Vercel (sitio estático)
Root Directory: esta carpeta. `vercel.json` ya define `npm run build` → `public/`.
El build genera `public/config.js` desde `ESB_URL` (URL del proyecto ServiciosSOA, p. ej. `https://<servicios>.vercel.app`), `API_KEY` y `USUARIO`.
