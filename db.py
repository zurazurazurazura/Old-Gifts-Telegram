import sqlite3
from config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            uid INTEGER PRIMARY KEY,
            authed INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_user(uid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT authed FROM users WHERE uid = ?", (uid,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def set_authed(uid, authed):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (uid, authed) VALUES (?, ?)", (uid, 1 if authed else 0))
    conn.commit()
    conn.close()
