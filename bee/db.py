import sqlite3
import hashlib
from typing import Dict, List, Tuple, Optional

# Puxa DB_FILE do seu bee/config.py
try:
    from bee.config import DB_FILE
except Exception:
    DB_FILE = "bee_database.db"


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------

def _connect(db_file: Optional[str] = None):
    return sqlite3.connect(db_file or DB_FILE)


def hash_password(password: str) -> str:
    # Usa SHA256 para transformar texto em hash irreversível
    return hashlib.sha256(str.encode(password)).hexdigest()


# --------------------------------------------------------------------------------------
# Init DB
# --------------------------------------------------------------------------------------
def init_db(db_file: Optional[str] = None):
    """Cria todas as tabelas necessárias (idempotente)."""
    conn = _connect(db_file)
    c = conn.cursor()

    # 1. Users
    c.execute("""
              CREATE TABLE IF NOT EXISTS users
              (
                  username
                  TEXT
                  PRIMARY
                  KEY,
                  password
                  TEXT
                  NOT
                  NULL,
                  name
                  TEXT
              )
              """)

    # --- MIGRATION: Adiciona coluna de segurança se não existir ---
    try:
        c.execute("ALTER TABLE users ADD COLUMN security_word TEXT")
    except sqlite3.OperationalError:
        pass  # Coluna já existe

    # 2. User Data
    c.execute("""
              CREATE TABLE IF NOT EXISTS user_data
              (
                  username
                  TEXT
                  PRIMARY
                  KEY,
                  carteira_json
                  TEXT,
                  gastos_json
                  TEXT
              )
              """)
    # 3. Targets
    c.execute("""
              CREATE TABLE IF NOT EXISTS targets
              (
                  username
                  TEXT
                  NOT
                  NULL,
                  classe
                  TEXT
                  NOT
                  NULL,
                  target_pct
                  REAL
                  NOT
                  NULL,
                  PRIMARY
                  KEY
              (
                  username,
                  classe
              )
                  )
              """)
    # 4. Budgets
    c.execute("""
              CREATE TABLE IF NOT EXISTS category_budgets
              (
                  username
                  TEXT
                  NOT
                  NULL,
                  categoria
                  TEXT
                  NOT
                  NULL,
                  budget
                  REAL
                  NOT
                  NULL,
                  PRIMARY
                  KEY
              (
                  username,
                  categoria
              )
                  )
              """)
    # 5. Rules
    c.execute("""
              CREATE TABLE IF NOT EXISTS merchant_rules
              (
                  username
                  TEXT
                  NOT
                  NULL,
                  pattern
                  TEXT
                  NOT
                  NULL,
                  categoria
                  TEXT
                  NOT
                  NULL,
                  active
                  INTEGER
                  NOT
                  NULL
                  DEFAULT
                  1,
                  PRIMARY
                  KEY
              (
                  username,
                  pattern
              )
                  )
              """)
    # 6. Recurring
    c.execute("""
              CREATE TABLE IF NOT EXISTS recurring
              (
                  rec_id
                  INTEGER
                  PRIMARY
                  KEY
                  AUTOINCREMENT,
                  username
                  TEXT
                  NOT
                  NULL,
                  descricao
                  TEXT
                  NOT
                  NULL,
                  categoria
                  TEXT
                  NOT
                  NULL,
                  tipo
                  TEXT
                  NOT
                  NULL,
                  valor
                  REAL
                  NOT
                  NULL,
                  pagamento
                  TEXT
                  NOT
                  NULL,
                  day_of_month
                  INTEGER
                  NOT
                  NULL,
                  active
                  INTEGER
                  NOT
                  NULL
                  DEFAULT
                  1
              )
              """)
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------------------
# Users & Auth
# --------------------------------------------------------------------------------------
def create_user(username: str, password: str, name: str, security_word: str, db_file: Optional[str] = None) -> bool:
    conn = _connect(db_file)
    c = conn.cursor()
    try:
        # Salvamos a senha E a palavra secreta como HASH (ninguém lê, nem o admin)
        pass_hash = hash_password(password)
        sec_hash = hash_password(security_word.strip().lower())  # Padroniza minusculo

        c.execute("INSERT INTO users (username, password, name, security_word) VALUES (?, ?, ?, ?)",
                  (username, pass_hash, name, sec_hash))

        c.execute("INSERT INTO user_data (username, carteira_json, gastos_json) VALUES (?, ?, ?)",
                  (username, "[]", "[]"))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def login_user(username: str, password: str, db_file: Optional[str] = None) -> Optional[str]:
    conn = _connect(db_file)
    c = conn.cursor()
    c.execute("SELECT name FROM users WHERE username = ? AND password = ?",
              (username, hash_password(password)))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def update_password_db(username: str, old_pass: str, new_pass: str, db_file: Optional[str] = None) -> bool:
    conn = _connect(db_file)
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    stored = c.fetchone()
    if stored and stored[0] == hash_password(old_pass):
        c.execute("UPDATE users SET password = ? WHERE username = ?", (hash_password(new_pass), username))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False


def reset_password_with_security(username: str, security_word: str, new_password: str,
                                 db_file: Optional[str] = None) -> bool:
    """Reseta a senha se a palavra de segurança bater."""
    conn = _connect(db_file)
    c = conn.cursor()

    c.execute("SELECT security_word FROM users WHERE username = ?", (username,))
    row = c.fetchone()

    if not row or not row[0]:
        conn.close()
        return False  # Usuário não existe ou não tem palavra definida

    stored_sec_hash = row[0]
    input_sec_hash = hash_password(security_word.strip().lower())

    if stored_sec_hash == input_sec_hash:
        # Palavra correta! Atualiza a senha.
        c.execute("UPDATE users SET password = ? WHERE username = ?", (hash_password(new_password), username))
        conn.commit()
        conn.close()
        return True

    conn.close()
    return False


def delete_user_db(username: str, db_file: Optional[str] = None) -> None:
    conn = _connect(db_file)
    c = conn.cursor()
    tables = ["users", "user_data", "targets", "category_budgets", "merchant_rules", "recurring"]
    for t in tables:
        try:
            c.execute(f"DELETE FROM {t} WHERE username = ?", (username,))
        except Exception:
            pass
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------------------
# Wallet & Gastos (Lazy Import do Pandas mantido)
# --------------------------------------------------------------------------------------
def save_user_data_db(username: str, carteira_df, gastos_df, db_file: Optional[str] = None) -> None:
    conn = _connect(db_file)
    c = conn.cursor()

    c_json = carteira_df.to_json(orient="records", date_format="iso") if not carteira_df.empty else "[]"
    g_json = gastos_df.to_json(orient="records", date_format="iso") if not gastos_df.empty else "[]"

    c.execute("""
              INSERT INTO user_data (username, carteira_json, gastos_json)
              VALUES (?, ?, ?) ON CONFLICT(username) DO
              UPDATE SET carteira_json=excluded.carteira_json, gastos_json=excluded.gastos_json
              """, (username, c_json, g_json))
    conn.commit()
    conn.close()


def load_user_data_db(username: str, db_file: Optional[str] = None):
    import pandas as pd  # Lazy import

    conn = _connect(db_file)
    c = conn.cursor()
    c.execute("SELECT carteira_json, gastos_json FROM user_data WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()

    carteira_cols = ["Tipo", "Ativo", "Nome", "Qtd", "Preco_Medio", "Moeda", "Obs"]
    gastos_cols = ["Data", "Categoria", "Descricao", "Tipo", "Valor", "Pagamento"]

    c_df = pd.DataFrame(columns=carteira_cols)
    g_df = pd.DataFrame(columns=gastos_cols)

    if not row:
        return c_df, g_df

    c_json, g_json = row

    try:
        if c_json and c_json != "[]":
            c_df = pd.read_json(c_json, orient="records")
    except Exception:
        pass

    try:
        if g_json and g_json != "[]":
            g_df = pd.read_json(g_json, orient="records")
            if "Data" in g_df.columns:
                g_df["Data"] = pd.to_datetime(g_df["Data"], errors="coerce", dayfirst=True)
    except Exception:
        pass

    for col in carteira_cols:
        if col not in c_df.columns:
            c_df[col] = ""
    c_df = c_df[carteira_cols]

    for col in gastos_cols:
        if col not in g_df.columns:
            g_df[col] = ""
    g_df = g_df[gastos_cols]

    return c_df, g_df


# --------------------------------------------------------------------------------------
# Targets, Budgets, Rules, Recurring
# --------------------------------------------------------------------------------------
def load_targets_db(username: str, db_file: Optional[str] = None) -> Dict[str, float]:
    conn = _connect(db_file)
    c = conn.cursor()
    try:
        c.execute("SELECT classe, target_pct FROM targets WHERE username = ?", (username,))
        rows = c.fetchall()
    except sqlite3.OperationalError:
        return {}
    conn.close()
    if not rows:
        return {"Ação/ETF": 60.0, "Renda Fixa": 30.0, "Cripto": 5.0, "Caixa": 5.0}
    return {r[0]: float(r[1]) for r in rows}


def save_targets_db(username: str, targets: Dict[str, float], db_file: Optional[str] = None) -> None:
    conn = _connect(db_file)
    c = conn.cursor()
    for classe, pct in targets.items():
        c.execute("""
                  INSERT INTO targets (username, classe, target_pct)
                  VALUES (?, ?, ?) ON CONFLICT(username, classe) DO
                  UPDATE SET target_pct=excluded.target_pct
                  """, (username, str(classe), float(pct)))
    conn.commit()
    conn.close()


def get_budgets_db(username: str, db_file: Optional[str] = None) -> Dict[str, float]:
    conn = _connect(db_file)
    c = conn.cursor()
    try:
        c.execute("SELECT categoria, budget FROM category_budgets WHERE username = ?", (username,))
        rows = c.fetchall()
    except sqlite3.OperationalError:
        return {}
    conn.close()
    return {r[0]: float(r[1]) for r in rows}


def set_budget_db(username: str, categoria: str, budget: float, db_file: Optional[str] = None) -> None:
    conn = _connect(db_file)
    c = conn.cursor()
    c.execute("""
              INSERT INTO category_budgets (username, categoria, budget)
              VALUES (?, ?, ?) ON CONFLICT(username, categoria) DO
              UPDATE SET budget=excluded.budget
              """, (username, str(categoria), float(budget)))
    conn.commit()
    conn.close()


def list_rules_db(username: str, db_file: Optional[str] = None) -> List[Dict]:
    conn = _connect(db_file)
    c = conn.cursor()
    try:
        c.execute("SELECT pattern, categoria, active FROM merchant_rules WHERE username = ? ORDER BY pattern ASC",
                  (username,))
        rows = c.fetchall()
    except sqlite3.OperationalError:
        return []
    conn.close()
    return [{"pattern": r[0], "categoria": r[1], "active": int(r[2])} for r in rows]


def add_rule_db(username: str, pattern: str, categoria: str, active: int = 1, db_file: Optional[str] = None) -> None:
    conn = _connect(db_file)
    c = conn.cursor()
    c.execute("""
              INSERT INTO merchant_rules (username, pattern, categoria, active)
              VALUES (?, ?, ?, ?) ON CONFLICT(username, pattern) DO
              UPDATE SET categoria=excluded.categoria, active=excluded.active
              """, (username, str(pattern).strip().lower(), str(categoria), int(active)))
    conn.commit()
    conn.close()


def list_recurring_db(username: str, db_file: Optional[str] = None) -> List[Dict]:
    conn = _connect(db_file)
    c = conn.cursor()
    try:
        c.execute("""
                  SELECT rec_id,
                         descricao,
                         categoria,
                         tipo,
                         valor,
                         pagamento,
                         day_of_month,
                         active
                  FROM recurring
                  WHERE username = ?
                  ORDER BY active DESC, day_of_month ASC, descricao ASC
                  """, (username,))
        rows = c.fetchall()
    except sqlite3.OperationalError:
        return []
    conn.close()
    out = []
    for r in rows:
        out.append({
            "id": int(r[0]), "rec_id": int(r[0]), "descricao": r[1], "categoria": r[2],
            "tipo": r[3], "valor": float(r[4]), "pagamento": r[5], "day_of_month": int(r[6]),
            "active": int(r[7]),
        })
    return out


def add_recurring_db(username: str, descricao: str, categoria: str, tipo: str, valor: float, pagamento: str,
                     day_of_month: int, active: int = 1, db_file: Optional[str] = None) -> None:
    conn = _connect(db_file)
    c = conn.cursor()
    c.execute("""
              INSERT INTO recurring (username, descricao, categoria, tipo, valor, pagamento, day_of_month, active)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?)
              """,
              (username, str(descricao), str(categoria), str(tipo), float(valor), str(pagamento), int(day_of_month),
               int(active)))
    conn.commit()
    conn.close()


def set_recurring_active_db(username: str, rec_id: int, active: int, db_file: Optional[str] = None) -> None:
    conn = _connect(db_file)
    c = conn.cursor()
    c.execute("UPDATE recurring SET active = ? WHERE username = ? AND rec_id = ?", (int(active), username, int(rec_id)))
    conn.commit()
    conn.close()