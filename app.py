import streamlit as st
import pandas as pd
import gspread
from datetime import datetime

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

# URL e credenciais da planilha
URL_PLANILHA = "https://google.com"
URL_CSV = "https://google.com"


# Função para carregar dados via CSV (leitura em tempo real)
def carregar_dados():
    try:
        df = pd.read_csv(URL_CSV)
        df['data'] = pd.to_datetime(df['data']).dt.date
        df['valor'] = pd.to_numeric(df['valor'])
        return df
    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
        return pd.DataFrame(columns=["id", "id_cliente", "valor", "data", "status", "descricao"])

# Função para calcular juros compostos (2% ao mês após 30 dias de carência)
def calcular_valor_atual(row):
    if row['status'].strip().lower() == 'pago':
        return 0
    
    data_compra = row['data']
    hoje = datetime.now().date()
    dias_atraso = (hoje - data_compra).days
    
    if dias_atraso <= 30:
        return int(round(row['valor']))
    
    # Juros compostos proporcionais aos dias após a carência
    # 2% ao mês = (1 + 0.02) ** (meses) -> meses = (dias - 30) / 30
    dias_com_juros = dias_atraso - 30
    meses = dias_com_juros / 30.0
    valor_final = row['valor'] * ((1 + 0.02) ** meses)
    return int(round(valor_final))

# Inicializar gspread para escrita
def conectar_gspread():
    try:
        # Nota: gspread.public() funciona para planilhas públicas sem arquivo JSON de credenciais
        gc = gspread.public()
        sh = gc.open_by_url(URL_PLANILHA)
        return sh.get_worksheet(0)
    except Exception as e:
        st.error(f"Erro de conexão com gspread: {e}")
        return None

# Carrega os dados atuais
df_dados = carregar_dados()

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
    if not df_dados.empty:
        # Aplica o cálculo de juros em cada linha
        df_dados['valor_atual'] = df_dados.apply(calcular_valor_atual, axis=1)
        
        saldo_total = df_dados['valor_atual'].sum()
        st.metric(label="Saldo Total na Praça (com Juros)", value=f"R$ {saldo_total}")
        
        st.subheader("Dívidas por Cliente")
        # Agrupa por cliente trazendo apenas quem tem saldo devedor
        df_clientes = df_dados.groupby('id_cliente')['valor_atual'].sum().reset_index()
        df_clientes = df_clientes[df_clientes['valor_atual'] > 0]
        st.dataframe(df_clientes, use_container_width=True)
    else:
        st.info("Nenhum registro encontrado.")

# ---------------------------------------------------------
# ABA 2: CADASTRAR NOVO FIADO (Espaço corrigido para lançamento)
# ---------------------------------------------------------
with aba2:
    st.header("Lançar Novo Fiado")
    
    # Formulário estruturado garantindo o espaço visual dos campos
    with st.form("form_novo_fiado", clear_on_submit=True):
        id_cliente = st.text_input("Quem comprou? (Nome/ID do Cliente):")
        valor = st.number_input("Valor do Fiado (R$):", min_value=1, step=1)
        data_compra = st.date_input("Data da Compra:", value=datetime.now().date())
        descricao = st.text_area("Descrição / O que foi comprado:")
        
        botao_salvar = st.form_submit_with_clicks = st.form_submit_button("Gravar Fiado na Planilha")
        
        if botao_salvar:
            if id_cliente and valor > 0:
                aba_sheet = conectar_gspread()
                if aba_sheet:
                    # Gera um ID simples com base na quantidade de linhas existentes
                    novo_id = len(df_dados) + 1
                    novo_registro = [
                        str(novo_id), 
                        id_cliente, 
                        str(valor), 
                        data_compra.strftime("%Y-%m-%d"), 
                        "Pendente", 
                        descricao
                    ]
                    try:
                        aba_sheet.append_row(novo_registro)
                        st.success(f"Sucesso! Fiado de R$ {valor} para {id_cliente} foi gravado!")
                    except Exception as e:
                        st.error(f"Erro ao salvar na planilha: {e}")
            else:
                st.warning("Por favor, preencha o nome do cliente e o valor.")

# ---------------------------------------------------------
# ABA 3: DAR BAIXA / PAGAMENTOS
# ---------------------------------------------------------
with aba3:
    st.header("Dar Baixa ou Alterar Valores")
    st.write("Para fazer baixas parciais, alterar o status para **'Pago'** ou consultar detalhes, use o link direto para a planilha mãe:")
    
    # Botão visual para redirecionamento direto
    st.link_button("Abrir Planilha Mãe (Google Sheets)", URL_PLANILHA)

# ---------------------------------------------------------
# ABA 4: ITENS EM FALTA (Gerenciamento Local)
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
        for idx, item in enumerate(st.session_state.itens_falta):
            st.write(f"- {item}")
