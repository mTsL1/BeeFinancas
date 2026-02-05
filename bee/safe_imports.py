# Centraliza imports opcionais (igual você fazia)
try:
    import yfinance as yf
except Exception:
    yf = None

try:
    import plotly.graph_objects as go
    import plotly.express as px
except Exception:
    go = None
    px = None

try:
    from dateutil import parser as dtparser
except Exception:
    dtparser = None

try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None
