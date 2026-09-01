import streamlit as st
import pandas as pd
import datetime

# CONFIGURACAO DO APLICATIVO
st.set_page_config(page_title="Crediario - Loja Sao Jose", layout="wide", page_icon="🏬")

# ENDERECO MAE DA PLANILHA GOOGLE (Texto Puro e Seguro)
LINK_PLANILHA_MAE = "https://google.com"
LINK_CSV = "https://google.com"

# 1. CONTROLE DE ACESSO (SENHA)
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("🔑 Sistema de Crediario - Identificacao")
    senha = st.text_input("Digite a senha dos Socios:", type="password")
    if st.button("Acessar Sistema"):
        if senha == "TITITO":
            st.session_state['autenticado'] = True
            st.rerun()
        else:
            st.error("Senha incorreta!")
    st.stop()

# 2. CARREGAMENTO DOS DADOS EM TEMPO REAL
@st.cache_data(ttl=2)
def carregar_dados():
    try:
        df = pd.read_csv(LINK_CSV)
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except Exception as e:
        return pd.DataFrame(columns=['id', 'id_cliente', 'valor', 'data', 'status', 'descricao'])

df_dados = carregar_dados()

# 3. FUNCAO DE JUROS COMPOSTOS (2% ao mes apos 30 dias de carencia)
def calcular_valor_atual(valor_original, data_venda_str, status):
    try:
        valor_original = float(valor_original)
    except:
        return 0
        
    if str(status).strip().lower() == 'pago':
        return 0
    
    try:
        data_venda = pd.to_datetime(data_venda_str).date()
    except:
        return int(round(valor_original))
        
    hoje = datetime.date.today()
    dias_atraso = (hoje - data_venda).days
    
    if dias_atraso <= 30:
        return int(round(valor_original))
    
    dias_efetivos_atraso = dias_atraso - 30
    taxa_diaria = 0.02 / 30
    
    valor_atualizado = valor_original * ((1 + taxa_diaria) ** dias_efetivos_atraso)
    return int(round(valor_atualizado))

# PROCESSAMENTO DE DADOS
if not df_dados.empty and 'valor' in df_dados.columns and 'data' in df_dados.columns and 'status' in df_dados.columns:
    df_dados['status'] = df_dados['status'].fillna('Pendente')
    df_dados['saldo_devedor_atual'] = df_dados.apply(
        lambda r: calcular_valor_atual(r['valor'], r['data'], r['status']), axis=1
    )
else:
    df_dados = pd.DataFrame(columns=['id', 'id_cliente', 'valor', 'data', 'status', 'descricao', 'saldo_devedor_atual'])

# INTERFACE PRINCIPAL
st.title("🏬 Painel de Crediario - Loja Sao Jose")

aba1, aba2, aba3, aba4 = st.tabs([
    "📊 Saldo & Devedores", 
    "📝 Cadastrar Novo Fiado", 
    "💰 Dar Baixa / Pagamentos", 
    "📦 Itens em Falta"
])

# ABA 1: VISUALIZACAO DE QUEM DEVE
with aba1:
    st.header("📊 Resumo Financeiro do Crediario")
    total_fiado_atual = df_dados['saldo_devedor_atual'].sum()
    st.metric(label="💰 Saldo Total de Fiado na Praca (Com Juros)", value=f"R$ {total_fiado_atual},00")
    
    st.subheader("👥 Relacao de Clientes Devedores")
    if total_fiado_atual > 0:
        clientes_devedores = df_dados[df_dados['saldo_devedor_atual'] > 0]
        resumo_clientes = clientes_devedores.groupby('id_cliente')['saldo_devedor_atual'].sum().reset_index()
        resumo_clientes.columns = ['Nome do Cliente', 'Total da Divida Atualizada (R$)']
        st.dataframe(resumo_clientes, use_container_width=True)
    else:
        st.success("Não ha nenhum saldo pendente ou devedor registrado!")

# ABA 2: CADASTRO COM BOTAO OFICIAL DO STREAMLIT
with aba2:
    st.header("📝 Cadastrar Nova Conta no Livro")
    st.write("Clique no botao abaixo para abrir o livro. Va ate a ultima linha em branco da tabela para adicionar o cliente:")
    st.link_button("➕ ABRIR PLANILHA PARA LANÇAR NOVO FIADO", LINK_PLANILHA_MAE, use_container_width=True)

# ABA 3: OPERACAO DE BAIXAS COM BOTAO OFICIAL DO STREAMLIT
with aba3:
    st.header("💰 Dar Baixa em Pagamentos")
    st.write("Clique no botao abaixo para abrir a planilha. Altere o valor restante ou mude o status para 'Pago' diretamente:")
    st.link_button("🟢 ABRIR LIVRO DE CONTAS PARA DAR BAIXAS", LINK_PLANILHA_MAE, use_container_width=True)
    
    st.write("<br>", unsafe_allow_html=True)
    st.subheader("🔍 Historico Geral de Lancamentos")
    if not df_dados.empty:
        colunas_exibicao = [c for c in ['id', 'id_cliente', 'valor', 'data', 'status', 'descricao', 'saldo_devedor_atual'] if c in df_dados.columns]
        st.dataframe(df_dados[colunas_exibicao], use_container_width=True)
    else:
        st.dataframe(df_dados, use_container_width=True)

# ABA 4: ITENS EM FALTA
with aba4:
    st.header("📦 Itens em Falta na Loja")
    if 'itens_falta' not in st.session_state:
        st.session_state['itens_falta'] = []
    
    novo_item = st.text_input("Qual produto esta faltando?")
    if st.button("Adicionar a Lista"):
        if novo_item:
            st.session_state['itens_falta'].append(novo_item)
            st.rerun()
            
    if st.session_state['itens_falta']:
        for idx, item in enumerate(st.session_state['itens_falta']):
            st.write(f"{idx + 1}. {item}")
        if st.button("Limpar Lista"):
            st.session_state['itens_falta'] = []
            st.rerun()
