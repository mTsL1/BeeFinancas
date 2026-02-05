import streamlit as st
import math
from ..formatters import fmt_money_brl

def render_calculadoras():
    st.markdown("## 🧮 Calculadoras")
    tabs = st.tabs(["Juros", "Alugar/Financiar", "Milhão", "Renda Fixa"])

    with tabs[0]:
        vp = st.number_input("Valor inicial", 1000.0)
        pmt = st.number_input("Aporte mensal", 500.0)
        taxa = st.number_input("Taxa anual (%)", 10.0)
        anos = st.slider("Anos", 1, 50, 10)
        if st.button("Calcular"):
            r = (taxa / 100) / 12
            n = anos * 12
            total = vp * (1 + r) ** n + pmt * (((1 + r) ** n - 1) / r) if r > 0 else vp + pmt * n
            st.success(f"Total: {fmt_money_brl(total, 2)}")

    with tabs[1]:
        c1, c2 = st.columns(2)
        with c1:
            valor_imovel = st.number_input("Valor do imóvel", 500000.0)
            aluguel = st.number_input("Aluguel mensal", 2500.0)
        with c2:
            taxa_fin = st.number_input("Taxa financiamento (% a.a.)", 9.5)
            taxa_inv = st.number_input("Rentabilidade invest (% a.a.)", 11.0)

        if st.button("Simular"):
            custo_fin = valor_imovel * (1 + (taxa_fin / 100) * 1.5)
            pot_inv = (valor_imovel * 0.20) * (1 + (taxa_inv / 100)) ** 30
            st.warning(f"Custo financiamento (estimado): {fmt_money_brl(custo_fin, 2)}")
            st.success(f"Potencial investindo 20% por 30 anos: {fmt_money_brl(pot_inv, 2)}")

    with tabs[2]:
        c1, c2 = st.columns(2)
        invest_mensal = c1.number_input("Aporte mensal", 2000.0)
        taxa_anual = c2.number_input("Rentabilidade anual (%)", 10.0)
        if st.button("Tempo p/ 1 milhão"):
            r = (taxa_anual / 100) / 12
            if invest_mensal <= 0 or r <= 0:
                st.info("Informe aporte e taxa > 0.")
            else:
                n = math.log((1_000_000 * r) / invest_mensal + 1) / math.log(1 + r)
                st.success(f"Tempo: {n / 12:.1f} anos")

    with tabs[3]:
        val = st.number_input("Valor (R$)", 1000.0)
        cdi = st.number_input("CDI (% a.a.)", 13.0)
        if st.button("Retorno 1 ano"):
            total = val * (1 + cdi / 100)
            st.info(f"1 ano: {fmt_money_brl(total, 2)}")
