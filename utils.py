# =============================
# CORES PADRÃO DO APP
# =============================

COR_AMARELO = "#FFD700"
COR_PRETO = "black"
COR_BRANCO = "white"
COR_CINZA = "#222222"
COR_CINZA_CLARO = "#444444"


# =============================
# FORMATADORES
# =============================

def fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}"


def parse_float(text: str) -> float:
    if not text:
        return 0.0
    t = text.replace("R$", "").replace(" ", "")
    t = t.replace(".", "").replace(",", ".")
    return float(t)


def parse_int(text: str) -> int:
    if not text:
        return 0
    return int(text)
