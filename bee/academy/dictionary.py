# bee/academy/dictionary.py
# Dicionário de abreviações e indicadores de mercado

from __future__ import annotations

from typing import List, Dict, Optional

DICTIONARY: List[Dict[str, str]] = [
    # ---- VALUATION ----
    {
        "id": "dict_pl",
        "term": "P/L",
        "topic": "Valuation",
        "definition": "Preço/Lucro. Diz quantos anos de lucro (aprox.) você está pagando no preço atual.",
        "why_it_matters": "Ajuda a comparar valuation entre empresas do mesmo setor. P/L muito alto pode indicar expectativa forte ou exagero.",
        "how_to_use": "Compare com histórico da empresa e com concorrentes. Nunca use sozinho.",
        "formula": "P/L = Preço da ação / Lucro por ação (LPA)",
        "notes": "Em empresas cíclicas o P/L pode enganar. Se o lucro caiu, o P/L sobe artificialmente."
    },
    {
        "id": "dict_pvp",
        "term": "P/VP",
        "topic": "Valuation",
        "definition": "Preço/Valor Patrimonial. Compara o preço de mercado com o valor contábil por ação.",
        "why_it_matters": "Útil para bancos/seguradoras e empresas com patrimônio relevante.",
        "how_to_use": "P/VP abaixo de 1 pode indicar desconto — ou problema no negócio. Compare com o setor.",
        "formula": "P/VP = Preço da ação / Valor Patrimonial por ação (VPA)",
        "notes": "Em empresas de tecnologia, o VP pode não refletir ativos intangíveis."
    },
    {
        "id": "dict_ev_ebitda",
        "term": "EV/EBITDA",
        "topic": "Valuation",
        "definition": "Enterprise Value dividido pelo EBITDA. Mostra valuation considerando dívida e caixa.",
        "why_it_matters": "Comparação mais justa entre empresas com diferentes níveis de endividamento.",
        "how_to_use": "Use para comparar empresas do mesmo setor. Menor nem sempre é melhor.",
        "formula": "EV/EBITDA = (Valor de mercado + Dívida - Caixa) / EBITDA",
        "notes": "EBITDA não é lucro. Pode mascarar capex alto."
    },

    # ---- RENTABILIDADE ----
    {
        "id": "dict_roe",
        "term": "ROE",
        "topic": "Rentabilidade",
        "definition": "Return on Equity. Retorno sobre o patrimônio líquido.",
        "why_it_matters": "Mostra eficiência em gerar lucro usando o capital dos acionistas.",
        "how_to_use": "Compare com empresas do mesmo setor e veja consistência ao longo dos anos.",
        "formula": "ROE = Lucro líquido / Patrimônio líquido",
        "notes": "ROE pode subir artificialmente se a empresa aumenta dívida e reduz patrimônio."
    },
    {
        "id": "dict_roa",
        "term": "ROA",
        "topic": "Rentabilidade",
        "definition": "Return on Assets. Retorno gerado em cima dos ativos totais.",
        "why_it_matters": "Útil para ver eficiência operacional geral.",
        "how_to_use": "Compare com concorrentes. Setores intensivos em ativos tendem a ter ROA menor.",
        "formula": "ROA = Lucro líquido / Ativos totais",
        "notes": "Depende bastante do setor."
    },
    {
        "id": "dict_margem_liquida",
        "term": "Margem Líquida",
        "topic": "Rentabilidade",
        "definition": "Percentual do faturamento que vira lucro líquido.",
        "why_it_matters": "Mostra poder de precificação e eficiência da empresa.",
        "how_to_use": "Procure margens estáveis/crescentes ao longo do tempo.",
        "formula": "Margem líquida = Lucro líquido / Receita",
        "notes": "Empresas de varejo costumam ter margem menor."
    },

    # ---- ENDIVIDAMENTO ----
    {
        "id": "dict_divliq_ebitda",
        "term": "Dívida Líq./EBITDA",
        "topic": "Endividamento",
        "definition": "Quantos anos de EBITDA a empresa precisa para pagar a dívida líquida (aprox.).",
        "why_it_matters": "Mede alavancagem. Muito alto pode indicar risco em juros altos.",
        "how_to_use": "Compare por setor. Observe tendência (caindo é bom).",
        "formula": "Dívida Líquida/EBITDA = (Dívida - Caixa) / EBITDA",
        "notes": "Setores estáveis toleram mais dívida que setores voláteis."
    },
    {
        "id": "dict_liquidez_corrente",
        "term": "Liquidez Corrente",
        "topic": "Endividamento",
        "definition": "Capacidade de pagar obrigações de curto prazo com ativos de curto prazo.",
        "why_it_matters": "Indica folga (ou aperto) no curto prazo.",
        "how_to_use": "Acima de 1 geralmente é ok, mas depende do setor.",
        "formula": "Liquidez corrente = Ativo circulante / Passivo circulante",
        "notes": "Muito alta também pode indicar capital mal alocado."
    },

    # ---- DIVIDENDOS ----
    {
        "id": "dict_dy",
        "term": "DY (Dividend Yield)",
        "topic": "Dividendos",
        "definition": "Percentual do preço atual que a empresa pagou em dividendos no período (geralmente 12 meses).",
        "why_it_matters": "Ajuda a comparar retorno em proventos.",
        "how_to_use": "Olhe sustentabilidade: payout, geração de caixa e consistência.",
        "formula": "DY = Dividendos por ação (12m) / Preço da ação",
        "notes": "DY alto demais pode ser armadilha se o lucro cair."
    },
    {
        "id": "dict_payout",
        "term": "Payout",
        "topic": "Dividendos",
        "definition": "Percentual do lucro que a empresa distribui aos acionistas.",
        "why_it_matters": "Mostra política de distribuição e espaço para reinvestimento.",
        "how_to_use": "Payout muito alto pode reduzir crescimento; muito baixo pode indicar retenção.",
        "formula": "Payout = Dividendos / Lucro",
        "notes": "Alguns setores têm payout estruturalmente maior."
    },

    # ---- ANÁLISE TÉCNICA ----
    {
        "id": "dict_rsi",
        "term": "RSI",
        "topic": "Análise Técnica",
        "definition": "Relative Strength Index. Indicador que tenta medir sobrecompra/sobrevenda.",
        "why_it_matters": "Ajuda a identificar momentos de força/exaustão no preço (não é garantia).",
        "how_to_use": "RSI > 70 costuma ser sobrecompra; RSI < 30 sobrevenda (regra geral). Combine com tendência e suporte/resistência.",
        "formula": "RSI (14) baseado na média de ganhos/perdas do período",
        "notes": "Em tendência forte, RSI pode ficar alto/baixo por muito tempo."
    },
    {
        "id": "dict_mm",
        "term": "MM (Média Móvel)",
        "topic": "Análise Técnica",
        "definition": "Média do preço em um período (ex.: 9, 21, 200). Suaviza o ruído.",
        "why_it_matters": "Ajuda a ver tendência e pontos de suporte/resistência dinâmicos.",
        "how_to_use": "Use cruzamentos (ex.: MM curta cruzando MM longa) como sinal auxiliar.",
        "formula": "MM = média dos preços nos últimos N períodos",
        "notes": "Atrasada por natureza (lag)."
    },
    {
        "id": "dict_suporte_resistencia",
        "term": "Suporte / Resistência",
        "topic": "Análise Técnica",
        "definition": "Níveis onde o preço historicamente encontra dificuldade para cair (suporte) ou subir (resistência).",
        "why_it_matters": "Ajuda em entradas/saídas e gerenciamento de risco.",
        "how_to_use": "Procure regiões de toque repetido. Confirme com volume e tendência.",
        "formula": "",
        "notes": "São zonas, não linhas exatas."
    },

    # ---- OUTROS ----
    {
        "id": "dict_beta",
        "term": "Beta",
        "topic": "Risco",
        "definition": "Mede a sensibilidade do ativo em relação ao mercado (ex.: IBOV).",
        "why_it_matters": "Beta alto tende a oscilar mais que o mercado; beta baixo, menos.",
        "how_to_use": "Use para balancear risco da carteira.",
        "formula": "Beta = cov(ativo, mercado) / var(mercado)",
        "notes": "Depende da janela de tempo."
    },
    {
        "id": "dict_volatilidade",
        "term": "Volatilidade",
        "topic": "Risco",
        "definition": "Medida de variação do preço. Maior volatilidade = mais oscilação.",
        "why_it_matters": "Define risco de curto prazo e tamanho ideal de posição.",
        "how_to_use": "Ativos mais voláteis pedem menor % na carteira se você quer estabilidade.",
        "formula": "",
        "notes": "Não é a mesma coisa que risco de falência (crédito)."
    },
]


def topics_in_dictionary() -> List[str]:
    topics = sorted({d.get("topic", "").strip() for d in DICTIONARY if d.get("topic")})
    return [t for t in topics if t]


def search_dictionary(query: str = "", topic: Optional[str] = None) -> List[Dict[str, str]]:
    q = (query or "").strip().lower()

    def match(item: Dict[str, str]) -> bool:
        if topic and item.get("topic") != topic:
            return False
        if not q:
            return True
        hay = " ".join([
            item.get("term", ""),
            item.get("definition", ""),
            item.get("why_it_matters", ""),
            item.get("how_to_use", ""),
            item.get("notes", ""),
            item.get("formula", ""),
        ]).lower()
        # busca simples (contém)
        return q in hay or q.replace("/", "") in hay or q.replace(".", "") in hay

    results = [d for d in DICTIONARY if match(d)]
    # ordena por termo
    results.sort(key=lambda x: x.get("term", ""))
    return results
