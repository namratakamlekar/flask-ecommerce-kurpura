import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database", "kurpura.db")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_all(sql, args=()):
    conn = connect()
    rows = [dict(row) for row in conn.execute(sql, args).fetchall()]
    conn.close()
    return rows


def get_one(sql, args=()):
    rows = get_all(sql, args)
    return rows[0] if rows else None


def run(sql, args=()):
    conn = connect()
    cursor = conn.execute(sql, args)
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id
