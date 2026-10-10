# PROYECTO 3 – Servicios SOA + ESB (Alicorp SOA, APF2)

SRV01–SRV06 (FastAPI, REST/JSON) + ESB ligero + BD compartida (Postgres vía `DATABASE_URL` o SQLite local).

```bash
pip install -r requirements.txt
./scripts/iniciar.sh                      # servicios :8000 + ESB :8080 (dos procesos)
uvicorn app_unificada:app --port 8000     # o: todo en un proceso, igual que en Vercel
python scripts/prueba_humo.py --sin-portales
```
Vercel: Root Directory `ServiciosSOA`, variable `DATABASE_URL`. Ver el README de la raíz.
