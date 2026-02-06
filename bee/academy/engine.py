# bee/academy/engine.py
from datetime import date
import hashlib
import random

LEVELS = [
    (0, "Iniciante 🐣"),
    (150, "Aprendiz 🐝"),
    (350, "Intermediário 📈"),
    (650, "Avançado 🧠"),
    (1000, "Pro 🏆"),
    (1500, "Lenda Bee 👑"),
]

def calc_level(xp: int):
    xp = int(xp or 0)
    current_name = LEVELS[0][1]
    current_floor = 0

    for floor, name in LEVELS:
        if xp >= floor:
            current_floor = floor
            current_name = name

    floors = [f for f, _ in LEVELS]
    higher = [f for f in floors if f > current_floor]
    next_floor = higher[0] if higher else None

    if next_floor is None:
        return current_name, None, 1.0

    span = max(1, next_floor - current_floor)
    progress = (xp - current_floor) / span
    progress = min(1.0, max(0.0, progress))
    return current_name, next_floor, progress


def _seed_from_user_day(username: str, day: str) -> int:
    raw = f"{username}::{day}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return int(digest[:8], 16)


def daily_question_id(username: str, question_ids: list[str], day: str | None = None) -> str:
    if not question_ids:
        return ""
    if day is None:
        day = date.today().isoformat()
    seed = _seed_from_user_day(username or "guest", day)
    rng = random.Random(seed)
    return rng.choice(question_ids)
