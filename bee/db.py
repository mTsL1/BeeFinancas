import sqlite3
import hashlib
import pandas as pd
from .config import DB_FILE, CARTEIRA_COLS, GASTOS_COLS

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            name TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_data (
            username TEXT PRIMARY KEY,
            carteira_json TEXT,
            gastos_json TEXT
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def create_user(username, password, name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO users (username, password, name) VALUES (?, ?, ?)",
            (username, hash_password(password), name)
        )
        c.execute(
            "INSERT INTO user_data (username, carteira_json, gastos_json) VALUES (?, ?, ?)",
            (username, "{}", "{}")
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "SELECT name FROM users WHERE username = ? AND password = ?",
        (username, hash_password(password))
    )
    data = c.fetchone()
    conn.close()
    return data[0] if data else None

def update_password_db(username, old_pass, new_pass):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    stored = c.fetchone()
    if stored and stored[0] == hash_password(old_pass):
        c.execute("UPDATE users SET password = ? WHERE username = ?",
                  (hash_password(new_pass), username))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def delete_user_db(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username = ?", (username,))
    c.execute("DELETE FROM user_data WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def save_user_data_db(username, carteira_df, gastos_df):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c_json = carteira_df.to_json(orient="records", date_format="iso") if not carteira_df.empty else "{}"
    g_json = gastos_df.to_json(orient="records", date_format="iso") if not gastos_df.empty else "{}"

    c.execute("""
        INSERT INTO user_data (username, carteira_json, gastos_json)
        VALUES (?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
          carteira_json=excluded.carteira_json,
          gastos_json=excluded.gastos_json
    """, (username, c_json, g_json))

    conn.commit()
    conn.close()

def load_user_data_db(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT carteira_json, gastos_json FROM user_data WHERE username = ?", (username,))
    data = c.fetchone()
    conn.close()

    c_df = pd.DataFrame(columns=CARTEIRA_COLS)
    g_df = pd.DataFrame(columns=GASTOS_COLS)

    if data:
        c_json, g_json = data
        try:
            if c_json and c_json != "{}":
                c_df = pd.read_json(c_json, orient="records")
            if g_json and g_json != "{}":
                g_df = pd.read_json(g_json, orient="records")
                if "Data" in g_df.columns:
                    g_df["Data"] = pd.to_datetime(g_df["Data"])
        except Exception:
            pass

    return c_df, g_df
