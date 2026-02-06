import sqlite3
import os

# Tenta pegar o caminho do DB do seu config, ou usa o padrão
try:
    from bee.config import DB_FILE
except ImportError:
    DB_FILE = "bee_database.db"

print(f"🔧 Corrigindo tabela targets em: {DB_FILE}")

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# 1. Apaga a tabela antiga que tem a coluna errada ("class")
c.execute("DROP TABLE IF EXISTS targets")

# 2. Cria a tabela nova com a coluna certa ("classe")
c.execute("""
    CREATE TABLE targets (
        username TEXT NOT NULL,
        classe TEXT NOT NULL,
        target_pct REAL NOT NULL,
        PRIMARY KEY (username, classe)
    )
""")

conn.commit()
conn.close()

print("✅ Tabela recriada com a coluna 'classe' correta!")
