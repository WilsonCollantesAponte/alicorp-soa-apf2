"""Driver de PRUEBA: Postgres de Neon por HTTPS (puerto 443, endpoint /sql de Neon).

Solo se usa si SOA_DB_DRIVER=neon_http. Sirve para probar contra Neon desde redes
que bloquean el puerto 5432 (por ejemplo, la máquina de desarrollo). En Vercel se usa
psycopg normal (puerto 5432) y este módulo no se carga.
Limitación: cada sentencia se confirma sola (sin transacción interactiva)."""
import json
import re
import urllib.error
import urllib.request
from urllib.parse import urlsplit

# OIDs de tipos Postgres → conversión (el endpoint devuelve los valores como texto)
_CONV = {16: lambda v: v in ("t", "true", True), 20: int, 21: int, 23: int, 700: float, 701: float, 1700: float}
_ALIAS_CAMEL = re.compile(r"\bAS\s+([a-z]+[A-Z]\w*)")
_LIKE = re.compile(r"\bLIKE\b")


def _traducir(sql):
    n = 0

    def marcador(_):
        nonlocal n
        n += 1
        return f"${n}"
    sql = re.sub(r"\?", marcador, sql)
    sql = _ALIAS_CAMEL.sub(r'AS "\1"', sql)
    return _LIKE.sub("ILIKE", sql)


class _Fila(dict):
    def __init__(self, cols, valores):
        super().__init__(zip(cols, valores))
        self._valores = valores

    def __getitem__(self, k):
        return self._valores[k] if isinstance(k, int) else super().__getitem__(k)


class _Cursor:
    def __init__(self, filas):
        self._filas = filas

    def fetchone(self):
        return self._filas[0] if self._filas else None

    def fetchall(self):
        return list(self._filas)


class ConNeonHTTP:
    def __init__(self, url):
        self._url = url
        self._endpoint = f"https://{urlsplit(url).hostname}/sql"

    def _consulta(self, sql, params=()):
        cuerpo = json.dumps({"query": sql, "params": [None if p is None else str(p) for p in params]}).encode()
        req = urllib.request.Request(self._endpoint, data=cuerpo, headers={
            "Neon-Connection-String": self._url, "Neon-Raw-Text-Output": "true", "Content-Type": "application/json"})
        try:
            r = json.load(urllib.request.urlopen(req, timeout=20))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Neon HTTP {e.code}: {e.read()[:300].decode(errors='replace')}") from None
        campos = r.get("fields") or []
        cols = [c["name"] for c in campos]
        conv = [_CONV.get(c.get("dataTypeID"), lambda v: v) for c in campos]
        filas = []
        for fila in r.get("rows") or []:
            vals = [fila.get(c) for c in cols] if isinstance(fila, dict) else list(fila)
            filas.append(_Fila(cols, tuple(None if v is None else f(v) for f, v in zip(conv, vals))))
        return _Cursor(filas)

    def execute(self, sql, params=()):
        if "pg_advisory_xact_lock" in sql:  # sin transacción interactiva no aplica
            return _Cursor([])
        return self._consulta(_traducir(sql), tuple(params))

    def executescript(self, script):
        limpio = "\n".join(l for l in script.splitlines() if not l.strip().startswith("--"))
        for sentencia in (s.strip() for s in limpio.split(";")):
            if sentencia:
                self._consulta(sentencia)

    def commit(self): pass
    def rollback(self): pass
    def close(self): pass
