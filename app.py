import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

SENHA_CORRETA = "1234"
ARQUIVO_DADOS = "dados_credito.json"

st.set_page_config(page_title="Controle Seguro", layout="wide")

def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r") as f: return json.load(f)
        except: return []
    return []

def salvar_dados(dados):
    with open(ARQUIVO_DADOS, "w") as f: json.dump(dados, f, indent=4)

if "vendas" not in st.session_state:
    st.session_state.vendas = carregar_dados()

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔒 Sistema de Controle Restrito")
    senha_digitada = st.text_input("Digite sua senha de acesso:", type="password")
    if st.button("Entrar"):
        if senha_digitada == SENHA_CORRETA:
            st.session_state.autenticado = True
            st.rerun()
        else: st.error("Senha incorreta!")
    st.stop()

st.title("📈 Painel de Controle de Crediário")
aba_cadastro, aba_relatorio = st.tabs(["➡️ Lançar Nova Venda", "📊 Relatório de Cobrança"])

with aba_cadastro:
    st.header("Cadastrar Novo Registro")
    id_cliente = st.number_input("Código do Cliente (ID do Excel):", min_value=1, step=1)
    valor_venda = st.number_input("Valor da Venda (R$):", min_value=0.01, step=0.50, format="%.2f")
    data_vencimento = st.date_input("Data de Vencimento:")
    
    if st.button("Salvar Registro"):
        nova_venda = {"id": int(id_cliente), "valor": float(valor_venda), "vencimento": data_vencimento.strftime("%Y-%m-%d"), "status": "Em aberto"}
        st.session_state.vendas.append(nova_venda)
        salvar_dados(st.session_state.vendas)
        st.success(f"Registro do Cliente {id_cliente} salvo.")

with aba_relatorio:
    st.header("Situação dos Pagamentos")
    if not st.session_state.vendas:
        st.info("Nenhuma venda cadastrada ainda.")
    else:
        lista_exibicao = []
        hoje = datetime.now().date()
        for i, venda in enumerate(st.session_state.vendas):
            data_venc = datetime.strptime(venda["vencimento"], "%Y-%m-%d").date()
            if venda["status"] == "Em aberto":
                if hoje > data_venc:
                    dias_atraso = (hoje - data_venc).days
                    valor_atualizado = venda["valor"] * ((1 + 0.02) ** (dias_atraso / 30))
                    situacao = f"⚠️ Atrasado ({dias_atraso} dias)"
                else:
                    dias_atraso = 0
                    valor_atualizado = venda["valor"]
                    situacao = "✅ Em dia"
            else:
                dias_atraso = 0
                valor_atualizado = venda["valor"]
                situacao = "💰 Pago"

            lista_exibicao.append({"Índice": i, "Código Cliente (ID)": venda["id"], "Valor Original": f"R$ {venda['valor']:.2f}", "Vencimento": data_venc.strftime("%d/%m/%Y"), "Dias de Atraso": dias_atraso, "Situação": situacao, "Valor Atualizado (c/ Juros)": f"R$ {valor_atualizado:.2f}"})
            
        df = pd.DataFrame(lista_exibicao)
        filtro = st.radio("Filtrar por:", ["Todos", "Apenas Atrasados", "Apenas em Dia"])
        if filtro == "Apenas Atrasados": df = df[df["Situação"].str.contains("Atrasado")]
        elif filtro == "Apenas em Dia": df = df[df["Situação"] == "✅ Em dia"]
            
        st.dataframe(df.drop(columns=["Índice"]), use_container_width=True)
