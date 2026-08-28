import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date

# 1. CONFIGURAÇÕES VISUAIS
st.set_page_config(page_title="Controle de Crediário", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; }
    .stButton>button:hover { background-color: #1b5e20; color: white; }
    .alerta-critico { background-color: #ffebee; color: #c62828; padding: 15px; border-radius: 5px; border-left: 5px solid #c62828; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# 2. CONEXÃO COM O GOOGLE SHEETS (LINK ATUALIZADO DA LOJA SÃO JOSÉ)
URL_DA_PLANILHA = "https://google.com"

def carregar_dados():
    try:
        # Lê os dados em tempo real da planilha online
        df = pd.read_csv(URL_DA_PLANILHA)
        # Limpa espaços em branco nos nomes das colunas
        df.columns = df.columns.str.strip()
        # Converte para o formato de lista do app
        return df.to_dict(orient='records')
    except Exception as e:
        return []

# Busca sempre os dados mais recentes da planilha ao abrir a página
st.session_state.vendas = carregar_dados()

# 3. CONTROLE DE ACESSO (TELA DE LOGIN)
def tela_login():
    st.title("🔑 Acesso ao Sistema")
    SENHA_CORRETA = "loja123" 
    senha_digitada = st.text_input("Digite a senha da loja:", type="password")
    if st.button("Entrar"):
        if senha_digitada == SENHA_CORRETA:
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Senha incorreta. Tente novamente.")

if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    tela_login()
    st.stop()

# 4. FUNÇÃO DE CÁLCULO DE JUROS
def calcular_valores_atuais(venda):
    if str(venda.get('status', '')).strip().lower() == 'pago':
        return 0.0, 0.0, 0.0
        
    try:
        valor_original = float(venda.get('valor', 0))
    except:
        return 0.0, 0.0, 0.0
        
    try:
        data_venda = datetime.strptime(str(venda.get('data', '')).strip(), "%Y-%m-%d").date()
    except:
        # Se a data estiver errada ou em outro formato, assume o valor original sem juros
        return valor_original, 0.0, valor_original
        
    hoje = date.today()
    dias_atraso = (hoje - data_venda).days
    juros_acumulados = 0.0
    
    if dias_atraso > 30:
        dias_com_juros = dias_atraso - 30
        taxa_mensal = 0.02
        taxa_diaria = (1 + taxa_mensal) ** (1 / 30) - 1
        valor_com_juros = valor_original * ((1 + taxa_diaria) ** dias_com_juros)
        juros_acumulados = valor_com_juros - valor_original
    
    total_atualizado = valor_original + juros_acumulados
    return valor_original, juros_acumulados, total_atualizado

# 5. CÁLCULO DOS INDICADORES DO PAINEL
total_na_rua = 0.0
total_recebido = 0.0
total_vencido_com_juros = 0.0
alertas_criticos = []

for v in st.session_state.vendas:
    # Ignora linhas completamente vazias da planilha
    if pd.isna(v.get('id')):
        continue
        
    status_venda = str(v.get('status', '')).strip().lower()
    try:
        valor_venda = float(v.get('valor', 0))
    except:
        valor_venda = 0.0
        
    if status_venda == 'pago':
        total_recebido += valor_venda
    else:
        v_orig, v_jur, v_tot = calcular_valores_atuais(v)
        total_na_rua += v_orig
        try:
            dias = (date.today() - datetime.strptime(str(v.get('data', '')).strip(), "%Y-%m-%d").date()).days
            if dias > 30:
                total_vencido_com_juros += v_tot
                alertas_criticos.append({'id_cliente': v.get('id_cliente'), 'dias': dias, 'valor': v_tot})
        except:
            pass

# 6. INTERFACE DO USUÁRIO
st.title("🏪 Sistema de Controle de Crediário")

col1, col2, col3 = st.columns(3)
col1.metric("💰 Total Fiado na Rua (Original)", f"R$ {total_na_rua:,.2f}")
col2.metric("✅ Total Recebido", f"R$ {total_recebido:,.2f}")
col3.metric("🚨 Total Vencido (+30 dias com Juros)", f"R$ {total_vencido_com_juros:,.2f}")

st.divider()
aba_lancar, aba_relatorio, aba_baixa = st.tabs(["📝 Lançar Venda", "📋 Relatório de Cobrança", "💵 Dar Baixa em Pagamento"])

# ABA 1: COMO ADICIONAR DADOS
with aba_lancar:
    st.subheader("Registrar Nova Venda no Fiado")
    st.info("Para garantir que os dados fiquem salvos para sempre, adicione as novas linhas diretamente na sua Planilha Google. O aplicativo irá puxar os dados de lá instantaneamente para todos os sócios.")
    st.markdown(f"[👉 Clique aqui para abrir a sua Planilha Google](https://docs.google.com/spreadsheets/d/1fExWOzkkBk9qGpaaDP_pfnwnjiV90FSTAgnTOvAxgqs/)")
    
    st.markdown("""
    **Como preencher uma nova linha na planilha:**
    * **id:** Digite um número sequencial (ex: 1 para a primeira venda, 2 para a segunda...).
    * **id_cliente:** Digite apenas o número do cliente (ex: `1` para o Cliente 1).
    * **valor:** O valor da venda usando ponto no lugar da vírgula (ex: `150.50`).
    * **data:** A data da venda no formato Ano-Mês-Dia (ex: `2026-08-28`).
    * **status:** Escreva sempre `Pendente` para contas abertas.
    """)

# ABA 2: RELATÓRIO DE COBRANÇA
with aba_relatorio:
    st.subheader("Contas em Atraso Crítico (> 30 dias)")
    if alertas_criticos:
        for al in alertas_criticos:
            st.markdown(f"""
            <div class="alerta-critico">
                ⚠️ <b>Cliente {al['id_cliente']}</b> está com a conta atrasada há <b>{al['dias']} dias</b>.<br>
                Valor atualizado com juros: <b>R$ {al['valor']:,.2f}</b>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Nenhum cliente em atraso crítico no momento.")
        
    st.subheader("Todos os Fiados Ativos")
    dados_tabela = []
    for v in st.session_state.vendas:
        if pd.isna(v.get('id')):
            continue
        if str(v.get('status', '')).strip().lower() == 'pendente':
            v_orig, v_jur, v_tot = calcular_valores_atuais(v)
            dados_tabela.append({
                "Cód. Venda": int(v.get('id')),
                "ID Cliente": f"Cliente {int(v.get('id_cliente'))}",
                "Data da Compra": v.get('data'),
                "Valor Original": f"R$ {v_orig:,.2f}",
                "Juros Acumulados": f"R$ {v_jur:,.2f}",
                "Total Atualizado": f"R$ {v_tot:,.2f}"
            })
            
    if dados_tabela:
        st.dataframe(pd.DataFrame(dados_tabela), use_container_width=True)
    else:
        st.write("Não há contas pendentes.")

# ABA 3: COMO DAR BAIXA
with aba_baixa:
    st.subheader("Dar Baixa (Receber Dinheiro)")
    st.write("Para dar baixa em um pagamento, basta abrir a sua Planilha Google e mudar o texto da coluna **status** daquela venda de `Pendente` para `Pago`.")
    st.write("O aplicativo recalculará o faturamento e removerá o cliente da lista de cobrança no mesmo segundo!")
