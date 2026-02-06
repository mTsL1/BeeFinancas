# bee/academy/progress.py
import sqlite3
from datetime import date, datetime

try:
    from bee.config import DB_FILE
except Exception:
    DB_FILE = "bee_database.db"


def _connect():
    return sqlite3.connect(DB_FILE)


def init_academy_db():
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS academy_progress (
            username TEXT PRIMARY KEY,
            xp INTEGER NOT NULL DEFAULT 0,
            streak INTEGER NOT NULL DEFAULT 0,
            last_day TEXT,
            correct INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS academy_favorites (
            username TEXT NOT NULL,
            item_type TEXT NOT NULL,
            item_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (username, item_type, item_id)
        )
    """)

    conn.commit()
    conn.close()


def _ensure_user(username: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT username FROM academy_progress WHERE username = ?", (username,))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO academy_progress (username, xp, streak, last_day, correct, total) VALUES (?, 0, 0, NULL, 0, 0)",
            (username,)
        )
        conn.commit()
    conn.close()


def get_progress(username: str) -> dict:
    _ensure_user(username)
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT xp, streak, last_day, correct, total FROM academy_progress WHERE username = ?", (username,))
    xp, streak, last_day, correct, total = cur.fetchone()
    conn.close()
    return {
        "xp": int(xp or 0),
        "streak": int(streak or 0),
        "last_day": last_day,
        "correct": int(correct or 0),
        "total": int(total or 0),
    }


def _days_diff(last_day: str, today: str) -> int:
    try:
        d1 = datetime.strptime(last_day, "%Y-%m-%d").date()
        d2 = datetime.strptime(today, "%Y-%m-%d").date()
        return (d2 - d1).days
    except Exception:
        return 999999


def add_quiz_result(username: str, is_correct: bool, xp_gain_correct: int = 10):
    _ensure_user(username)
    today = date.today().isoformat()

    prog = get_progress(username)
    last_day = prog["last_day"]
    streak = prog["streak"]
    xp = prog["xp"]
    correct = prog["correct"]
    total = prog["total"]

    total += 1

    if not last_day:
        streak = 1
    else:
        diff = _days_diff(last_day, today)
        if diff == 0:
            streak = max(1, streak)
        elif diff == 1:
            streak += 1
        else:
            streak = 1

    if is_correct:
        correct += 1
        xp += int(xp_gain_correct)

    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        UPDATE academy_progress
        SET xp = ?, streak = ?, last_day = ?, correct = ?, total = ?
        WHERE username = ?
    """, (xp, streak, today, correct, total, username))
    conn.commit()
    conn.close()


def is_favorite(username: str, item_type: str, item_id: str) -> bool:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM academy_favorites
        WHERE username = ? AND item_type = ? AND item_id = ?
    """, (username, item_type, item_id))
    row = cur.fetchone()
    conn.close()
    return row is not None


def toggle_favorite(username: str, item_type: str, item_id: str) -> bool:
    now = datetime.now().isoformat(timespec="seconds")
    if is_favorite(username, item_type, item_id):
        conn = _connect()
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM academy_favorites
            WHERE username = ? AND item_type = ? AND item_id = ?
        """, (username, item_type, item_id))
        conn.commit()
        conn.close()
        return False

    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO academy_favorites (username, item_type, item_id, created_at)
        VALUES (?, ?, ?, ?)
    """, (username, item_type, item_id, now))
    conn.commit()
    conn.close()
    return True


def list_favorites(username: str, item_type: str) -> list[str]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT item_id FROM academy_favorites
        WHERE username = ? AND item_type = ?
        ORDER BY created_at DESC
    """, (username, item_type))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]
