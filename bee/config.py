import os

APP_VERSION = "v34.4 (QUICK ADD)"

# project root (um nível acima da pasta bee/)
BEE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BEE_DIR)

ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")

# mantém igual ao teu original (DB na raiz)
DB_FILE = os.path.join(PROJECT_DIR, "bee_database.db")

CARTEIRA_COLS = ["Tipo", "Ativo", "Nome", "Qtd", "Preco_Medio", "Moeda", "Obs"]
GASTOS_COLS = ["Data", "Categoria", "Descricao", "Tipo", "Valor", "Pagamento"]
