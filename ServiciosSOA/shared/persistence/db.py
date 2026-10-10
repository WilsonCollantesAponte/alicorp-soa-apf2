"""Acceso a la BD compartida. Único punto de persistencia del Proyecto 3.

Soporta dos motores con la MISMA interfaz que usan los servicios (tx(), rows()):
  - PostgreSQL (Neon en la nube) cuando existe la variable DATABASE_URL.
  - SQLite local (data/alicorp_soa.db) cuando no existe (desarrollo sin red).
Los servicios escriben SQL con marcadores '?'; el adaptador los traduce a '%s'
para psycopg. Los portales nunca usan este módulo."""
import os
import re
import sqlite3
from contextlib import contextmanager
from config import DB_PATH, BASE_DIR, DB_MOTOR, DATABASE_URL

SCHEMA = BASE_DIR / "shared" / "persistence" / "schema.sql"
ES_POSTGRES = DB_MOTOR == "postgres"


# ---------------------------------------------------------------- PostgreSQL
class _Fila(dict):
    """Fila que se lee por nombre (f['col']) o por posición (f[0]), igual que sqlite3.Row."""
    def __init__(self, cols, valores):
        super().__init__(zip(cols, valores))
        self._valores = valores

    def __getitem__(self, k):
        return self._valores[k] if isinstance(k, int) else super().__getitem__(k)


def _fila_factory(cursor):
    cols = [c.name for c in (cursor.description or [])]
    return lambda valores: _Fila(cols, valores)


_LIKE = re.compile(r"\bLIKE\b")
_ALIAS_CAMEL = re.compile(r"\bAS\s+([a-z]+[A-Z]\w*)")


def _traducir(sql: str) -> str:
    # '?' → '%s' (ningún SQL del proyecto usa '?' ni '%' literales dentro de cadenas);
    # LIKE de SQLite es insensible a mayúsculas → ILIKE en Postgres;
    # alias camelCase (AS clienteId) → entre comillas, porque Postgres los pasa a minúsculas.
    sql = sql.replace("%", "%%").replace("?", "%s")
    sql = _ALIAS_CAMEL.sub(r'AS "\1"', sql)
    return _LIKE.sub("ILIKE", sql)


class _ConPG:
    """Envoltura mínima de psycopg con la API de sqlite3 que usan los servicios."""
    def __init__(self, con):
        self._con = con

    def execute(self, sql, params=()):
        cur = self._con.cursor(row_factory=_fila_factory)
        cur.execute(_traducir(sql), tuple(params))
        return cur

    def executescript(self, script):
        with self._con.cursor() as cur:
            cur.execute(script)

    def commit(self): self._con.commit()
    def rollback(self): self._con.rollback()
    def close(self): self._con.close()


def _schema_pg(sql: str) -> str:
    # El esquema está escrito en SQL portable; solo cambian 2 tipos.
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    return re.sub(r"\bREAL\b", "DOUBLE PRECISION", sql)


# ---------------------------------------------------------------- común
def connect():
    if ES_POSTGRES and os.getenv("SOA_DB_DRIVER") == "neon_http":  # solo pruebas, ver neon_http.py
        from shared.persistence.neon_http import ConNeonHTTP
        return ConNeonHTTP(DATABASE_URL)
    if ES_POSTGRES:
        import psycopg  # prepare_threshold=None: compatible con el pooler (PgBouncer) de Neon
        return _ConPG(psycopg.connect(DATABASE_URL, connect_timeout=10, prepare_threshold=None))
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


@contextmanager
def tx():
    con = connect()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def rows(cur):
    return [dict(r) for r in cur.fetchall()]


def init_db(con=None):
    """Crea las tablas si no existen (CREATE TABLE IF NOT EXISTS)."""
    script = SCHEMA.read_text(encoding="utf-8")
    script = _schema_pg(script) if ES_POSTGRES else script
    if con is not None:
        con.executescript(script)
        return
    with tx() as c:
        c.executescript(script)


def motor() -> str:
    return DB_MOTOR
