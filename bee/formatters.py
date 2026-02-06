from datetime import datetime, timezone

def fmt_ptbr_number(x, decimals=2):
    try:
        if x is None:
            return "—"
        x = float(x)
        s = f"{x:,.{decimals}f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return s
    except Exception:
        return "—"

def fmt_money_brl(x, decimals=2):
    return f"R$ {fmt_ptbr_number(x, decimals)}"

def fmt_money_usd(x, decimals=0):
    return f"$ {fmt_ptbr_number(x, decimals)}".replace("$ ", "US$ ")

def human_time_ago(dt: datetime) -> str:
    if not dt:
        return ""
    try:
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        sec = int((now - dt).total_seconds())
        if sec < 60:
            return "agora"
        m = sec // 60
        if m < 60:
            return f"{m}m"
        h = m // 60
        if h < 24:
            return f"{h}h"
        d = h // 24
        return f"{d}d"
    except Exception:
        return ""
