# Arquivo: fix_db.py
import sqlite3
import os

# Tenta pegar o caminho do DB do seu config, ou usa o padrão
try:
    from bee.config import DB_FILE
except ImportError:
    DB_FILE = "bee_database.db"

print(f"🔧 Consertando banco de dados em: {DB_FILE}")

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# 1. Cria a tabela 'category_budgets' (Erro do Controle/Envelopes)
c.execute("""
    CREATE TABLE IF NOT EXISTS category_budgets (
        username TEXT NOT NULL,
        categoria TEXT NOT NULL,
        budget REAL NOT NULL,
        PRIMARY KEY (username, categoria)
    )
""")
print("✅ Tabela 'category_budgets' verificada.")

# 2. Cria a tabela 'targets' (Erro da Carteira/Alvos)
c.execute("""
    CREATE TABLE IF NOT EXISTS targets (
        username TEXT NOT NULL,
        classe TEXT NOT NULL,
        target_pct REAL NOT NULL,
        PRIMARY KEY (username, classe)
    )
""")
print("✅ Tabela 'targets' verificada.")

# 3. Cria a tabela 'merchant_rules' (Importação CSV)
c.execute("""
    CREATE TABLE IF NOT EXISTS merchant_rules (
        username TEXT NOT NULL,
        pattern TEXT NOT NULL,
        categoria TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY (username, pattern)
    )
""")
print("✅ Tabela 'merchant_rules' verificada.")

# 4. Garante a tabela 'recurring'
try:
    c.execute("""
        CREATE TABLE IF NOT EXISTS recurring (
            rec_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            descricao TEXT NOT NULL,
            categoria TEXT NOT NULL,
            tipo TEXT NOT NULL,
            valor REAL NOT NULL,
            pagamento TEXT NOT NULL,
            day_of_month INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)
    print("✅ Tabela 'recurring' verificada.")
except Exception as e:
    print(f"⚠️ Aviso sobre recurring (pode ignorar se já existia): {e}")

conn.commit()
conn.close()

print("\n🚀 BANCO ATUALIZADO COM SUCESSO!")
print("Agora pode rodar o 'streamlit run main.py' que os erros de 'no such table' vão sumir.")