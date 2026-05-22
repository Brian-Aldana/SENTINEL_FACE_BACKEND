import os
import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool

_pool: MySQLConnectionPool | None = None


def _get_pool() -> MySQLConnectionPool:
    global _pool
    if _pool is None:
        _pool = MySQLConnectionPool(
            pool_name="sentinel_pool",
            pool_size=int(os.getenv("DB_POOL_SIZE") or 10),
            pool_reset_session=True,
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            port=int(os.getenv("DB_PORT") or 3306),
        )
    return _pool


def get_db():
    """Obtiene una conexión del pool. Debe cerrarse con conn.close() para devolverla al pool."""
    return _get_pool().get_connection()