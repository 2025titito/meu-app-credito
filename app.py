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

# URLs configuradas apontando para a aba correta
URL_PLANILHA = "https://google.com"
URL_CSV = "https://google.com"

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

# Inicializar gspread para escrita na aba correta
def conectar_gspread():
    try:
        gc = gspread.public()
        sh = gc.open_by_url(URL_PLANILHA)
        return sh.worksheet("Respostas do Formulário 1")
    except Exception as e:
        st.error(f"Erro de conexão com gspread: {e}")
        return None

# Carrega os dados atuais
df_dados = carregar_dados()

# Aplica juros se a planilha não estiver vazia
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
                aba_sheet = conectar_gspread()
                if aba_sheet:
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
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar na planilha: {e}")
            else:
                st.warning("Por favor, preencha o nome do cliente e o valor.")

# ---------------------------------------------------------
# ABA 3: DAR BAIXA / PAGAMENTOS (Nova tela direto no App)
# ---------------------------------------------------------
with aba3:
    st.header("Dar Baixa em Pagamentos")
    
    # Filtra apenas quem deve no momento para facilitar a escolha dos sócios
    if not df_dados.empty and 'status' in df_dados.columns:
        df_devedores = df_dados[df_dados['valor_atual'] > 0]
        
        if not df_devedores.empty:
            st.write("Selecione o cliente abaixo que veio fazer o pagamento total:")
            
            # Lista única de clientes devedores para selecionar
            lista_clientes = sorted(df_devedores['id_cliente'].unique())
            
            with st.form("form_dar_baixa", clear_on_submit=True):
                cliente_selecionado = st.selectbox("Escolha o Cliente:", lista_clientes)
                
                botao_quitar = st.form_submit_button("Quitar Todas as Dívidas deste Cliente")
                
                if botao_quitar:
                    aba_sheet = conectar_gspread()
                    if aba_sheet:
                        try:
                            # Procura todas as linhas desse cliente na planilha para mudar para 'Pago'
                            celulas = aba_sheet.findall(cliente_selecionado)
                            
                            # Percorre as células encontradas e altera a coluna 'status' (Coluna 5 ou E)
                            linhas_atualizadas = 0
                            for celula in celulas:
                                if celula.col == 2: # Garante que achou na coluna id_cliente
                                    aba_sheet.update_cell(celula.row, 5, "Pago")
                                    linhas_atualizadas += 1
                            
                            st.success(f"Ótimo! Todas as contas de '{cliente_selecionado}' foram marcadas como PAGAS!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao atualizar status na planilha: {e}")
        else:
            st.info("Não há nenhuma dívida pendente na praça no momento.")
    else:
        st.info("Planilha vazia.")

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
