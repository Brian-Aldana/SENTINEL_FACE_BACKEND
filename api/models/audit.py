import json
from flask import request
from db import get_db


def find_all(limit=100):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT al.audit_id, al.action, al.target_table,
                   al.target_id, al.detail, al.ip_address, al.created_at,
                   u.full_name AS usuario_name
            FROM audit_log al
            LEFT JOIN usuarios u ON al.usuario_id = u.usuario_id
            ORDER BY al.created_at DESC LIMIT %s
        """, (limit,))
        rows = cursor.fetchall()
        for r in rows:
            if r.get("created_at"):
                r["created_at"] = r["created_at"].isoformat()
        return rows
    finally:
        cursor.close()
        conn.close()


def find_by_id(audit_id: int):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT al.audit_id, al.action, al.target_table,
                   al.target_id, al.detail, al.ip_address, al.created_at,
                   u.full_name AS usuario_name
            FROM audit_log al
            LEFT JOIN usuarios u ON al.usuario_id = u.usuario_id
            WHERE al.audit_id = %s
        """, (audit_id,))
        row = cursor.fetchone()
        if row and row.get("created_at"):
            row["created_at"] = row["created_at"].isoformat()
        return row
    finally:
        cursor.close()
        conn.close()


def record(usuario_id, action: str, table: str = None,
           target_id: int = None, detail: dict = None):
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO audit_log "
            "(usuario_id, action, target_table, target_id, detail, ip_address) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (usuario_id, action, table, target_id,
             json.dumps(detail) if detail else None,
             request.remote_addr),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()
