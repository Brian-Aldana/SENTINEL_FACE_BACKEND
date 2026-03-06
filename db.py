import os
import mysql.connector


def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "db"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "sentinel_db"),
        port=int(os.getenv("DB_PORT", 3306)),
    )