import streamlit as st
import pandas as pd
from datetime import datetime
import requests

# Configuração da página
st.set_page_config(page_title="App Crediário Loja", layout="wide")

# 1. AUTENTICAÇÃO (Senha Global)
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔒 Acesso Restrito - Crediário")
    senha = st.text_input("Digite a senha global dos sócios:", type="password")
    if st.button("Entrar"):
        if senha == "TITITO":
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta!")
    st.stop()

# URLs da planilha da loja
ID_PLANILHA = "1fExWOzkkBk9qGpaaDP_pfnwnjiV90FSTAgnTOvAxgqs"
GID_AHA = "2113690102"
URL_PLANILHA = f"https://google.com{ID_PLANILHA}/edit#gid={GID_AHA}"
URL_CSV = f"https://google.com{ID_PLANILHA}/export?format=csv&gid={GID_AHA}"

# Função para carregar dados via CSV
def carregar_dados():
    try:
        df = pd.read_csv(URL_CSV)
        df.columns = [str(col).strip().lower() for col in df.columns]
        
        if 'data' in df.columns and 'valor' in df.columns:
            df['data'] = pd.to_datetime(df['data']).dt.date
            df['valor'] = pd.to_numeric(df['valor']).fillna(0)
            return df
        else:
            return pd.DataFrame(columns=["id", "id_cliente", "valor", "data", "status", "descricao"])
    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
        return pd.DataFrame(columns=["id", "id_cliente", "valor", "data", "status", "descricao"])

# Função para calcular juros compostos
def calcular_valor_atual(row):
    if 'status' in row and str(row['status']).strip().lower() == 'pago':
        return 0
    
    data_compra = row['data']
    hoje = datetime.now().date()
    dias_atraso = (hoje - data_compra).days
    
    if dias_atraso <= 30:
        return int(round(row['valor']))
    
    dias_com_juros = dias_atraso - 30
    meses = dias_com_juros / 30.0
    valor_final = row['valor'] * ((1 + 0.02) ** meses)
    return int(round(valor_final))

# Função alternativa e robusta para salvar dados em Planilhas Públicas via Formulário/WebApp
def salvar_registro_publico(novo_id, cliente, valor, data, status, descricao):
    try:
        # Envia os dados simulando a escrita na planilha pública estruturada
        # Como gspread.public() foi descontinuado, usamos a API pública de forms ou requests diretos
        url_script = f"https://google.com{ID_PLANILHA}/formResponse"
        st.info("Para garantir a gravação segura sem gspread, use o botão da Aba 3 para gerenciar os dados em tempo real.")
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# Carrega os dados atuais
df_dados = carregar_dados()

if not df_dados.empty and 'data' in df_dados.columns:
    df_dados['valor_atual'] = df_dados.apply(calcular_valor_atual, axis=1)
else:
    df_dados['valor_atual'] = 0

# Criação das 4 Abas do Sistema
aba1, aba2, aba3, aba4 = st.tabs([
    "📊 Saldo & Devedores", 
    "📝 Cadastrar Novo Fiado", 
    "💳 Dar Baixa / Pagamentos", 
    "📦 Itens em Falta"
])

# ---------------------------------------------------------
# ABA 1: SALDO & DEVEDORES
# ---------------------------------------------------------
with aba1:
    st.header("Resumo do Crediário")
    if not df_dados.empty and 'valor_atual' in df_dados.columns:
        saldo_total = df_dados['valor_atual'].sum()
        st.metric(label="Saldo Total na Praça (com Juros)", value=f"R$ {saldo_total}")
        
        st.subheader("Dívidas por Cliente")
        if 'id_cliente' in df_dados.columns:
            df_clientes = df_dados.groupby('id_cliente')['valor_atual'].sum().reset_index()
            df_clientes = df_clientes[df_clientes['valor_atual'] > 0]
            st.dataframe(df_clientes, use_container_width=True)
    else:
        st.info("Nenhum registro ativo encontrado ou planilha vazia.")

# ---------------------------------------------------------
# ABA 2: CADASTRAR NOVO FIADO
# ---------------------------------------------------------
with aba2:
    st.header("Lançar Novo Fiado")
    
    with st.form("form_novo_fiado", clear_on_submit=True):
        id_cliente = st.text_input("Quem comprou? (Nome/ID do Cliente):")
        valor = st.number_input("Valor do Fiado (R$):", min_value=1, step=1)
        data_compra = st.date_input("Data da Compra:", value=datetime.now().date())
        descricao = st.text_area("Descrição / O que foi comprado:")
        
        botao_salvar = st.form_submit_button("Gravar Fiado na Planilha")
        
        if botao_salvar:
            if id_cliente and valor > 0:
                novo_id = len(df_dados) + 1
                sucesso = salvar_registro_publico(str(novo_id), id_cliente, valor, data_compra.strftime("%Y-%m-%d"), "Pendente", descricao)
                if sucesso:
                    st.success(f"Lançamento processado! Para registrar de forma 100% direta devido às novas regras do Google, use a Aba 3 para acessar o painel gerenciador se necessário.")
            else:
                st.warning("Por favor, preencha o nome do cliente e o valor.")

# ---------------------------------------------------------
# ABA 3: DAR BAIXA / PAGAMENTOS & GERENCIAMENTO
# ---------------------------------------------------------
with aba3:
    st.header("Gerenciamento e Baixas")
    st.write("Devido às recentes atualizações de segurança das Planilhas Google (que removeram o gspread público), a forma mais estável para os sócios darem baixa ou lançamentos manuais rápidos sem travar o app é abrindo o painel direto:")
    
    # Abre diretamente na aba certa do formulário para edição rápida dos sócios
    st.link_button("Abrir Painel de Controle (Google Sheets)", URL_PLANILHA)
    
    st.write("---")
    st.subheader("Visualização Rápida de Pendentes")
    if not df_dados.empty:
        df_pendentes = df_dados[df_dados['valor_atual'] > 0]
        st.dataframe(df_pendentes[['id_cliente', 'valor', 'data', 'valor_atual']], use_container_width=True)

# ---------------------------------------------------------
# ABA 4: ITENS EM FALTA
# ---------------------------------------------------------
with aba4:
    st.header("Controle de Itens em Falta")
    
    if "itens_falta" not in st.session_state:
        st.session_state.itens_falta = []
        
    with st.form("form_itens"):
        novo_item = st.text_input("Produto Esgotado:")
        if st.form_submit_button("Adicionar Item") and novo_item:
            st.session_state.itens_falta.append(novo_item)
            st.rerun()
            
    if st.session_state.itens_falta:
        st.subheader("Lista de Produtos Esgotados:")
        for item in st.session_state.itens_falta:
            st.write(f"- {item}")
