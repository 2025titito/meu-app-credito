
import streamlit as st
import pandas as pd
import datetime

# CONFIGURAÇÃO DO APLICATIVO
st.set_page_config(page_title="Crediário - Loja São José", layout="wide", page_icon="🏬")

# LINKS E CONFIGURAÇÃO DA PLANILHA GOOGLE
LINK_ORIGINAL = "https://google.com"
LINK_CSV = "https://google.com"

# LINK DO SEU FORMULARIO GOOGLE (Cole o seu link copiado entre as aspas abaixo)
LINK_FORMULARIO = "https://forms.gle/nsXr4yuL6Aiw2Ypo9"

# 1. CONTROLE DE ACESSO (SENHA)
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("🔑 Sistema de Crediário - Identificação")
    senha = st.text_input("Digite a senha dos Sócios:", type="password")
    if st.button("Acessar Sistema"):
        if senha == "TITITO":
            st.session_state['autenticado'] = True
            st.rerun()
        else:
            st.error("Senha incorreta! Verifique com os outros sócios.")
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

# 3. FUNÇÃO DE JUROS COMPOSTOS (2% ao mês após 30 dias de carência)
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

# PROCESSAMENTO DE DADOS ADAPTADO PARA FORMULÁRIOS GOOGLE
if 'carimbo de data/hora' in df_dados.columns:
    df_dados = df_dados.rename(columns={'carimbo de data/hora': 'id'})

if not df_dados.empty and 'valor' in df_dados.columns and 'data' in df_dados.columns and 'status' in df_dados.columns:
    df_dados['status'] = df_dados['status'].fillna('Pendente')
    df_dados['saldo_devedor_atual'] = df_dados.apply(
        lambda r: calcular_valor_atual(r['valor'], r['data'], r['status']), axis=1
    )
else:
    df_dados = pd.DataFrame(columns=['id', 'id_cliente', 'valor', 'data', 'status', 'descricao', 'saldo_devedor_atual'])

# INTERFACE PRINCIPAL
st.title("🏬 Painel de Crediário - Loja São José")

aba1, aba2, aba3, aba4 = st.tabs([
    "📊 Saldo & Devedores", 
    "📝 Cadastrar Novo Fiado", 
    "💰 Dar Baixa / Pagamentos", 
    "📦 Itens em Falta"
])

# ABA 1: VISUALIZAÇÃO DE QUEM DEVE
with aba1:
    st.header("📊 Resumo Financeiro do Crediário")
    total_fiado_atual = df_dados['saldo_devedor_atual'].sum()
    st.metric(label="💰 Saldo Total de Fiado na Praça (Com Juros)", value=f"R$ {total_fiado_atual},00")
    
    st.subheader("👥 Relação de Clientes Devedores (Valores Corrigidos)")
    if total_fiado_atual > 0:
        clientes_devedores = df_dados[df_dados['saldo_devedor_atual'] > 0]
        resumo_clientes = clientes_devedores.groupby('id_cliente')['saldo_devedor_atual'].sum().reset_index()
        resumo_clientes.columns = ['Nome do Cliente', 'Total da Dívida Atualizada (R$)']
        st.dataframe(resumo_clientes, use_container_width=True)
    else:
        st.success("Não há nenhum saldo pendente ou devedor registrado!")

# ABA 2: FORMULÁRIO GOOGLE EMBUTIDO DIRETO NO APP
with aba2:
    st.header("📝 Cadastrar Nova Conta Fiada")
    st.write("Insira as informações nos campos abaixo para salvar permanentemente na nuvem de forma segura:")
    
    if LINK_FORMULARIO == "COLE_AQUI_O_LINK_DO_SEU_FORMULARIO_GOOGLE":
        st.warning("⚠️ Atenção: Você precisa colar o link do seu formulário Google na linha 12 do código do GitHub para esta tela funcionar!")
    else:
        # Incorpora o formulário de forma transparente e elegante dentro do app
        st.components.v1.iframe(LINK_FORMULARIO, height=650, scrolling=True)
        st.info("💡 **Dica Didática**: Após preencher as perguntas acima e clicar no botão roxo 'Submeter/Enviar' do formulário, mude para a aba '📊 Saldo & Devedores' para acompanhar as atualizações.")

# ABA 3: OPERAÇÃO DE BAIXAS PARCIAIS OU TOTAIS
with aba3:
    st.header("💰 Dar Baixa em Pagamentos")
    st.write("Para fazer alterações, dar baixas parciais ou atualizar valores pagos pelos clientes, clique no botão verde abaixo:")
    st.markdown(f' <a href="{LINK_ORIGINAL}" target="_blank" style="padding: 12px 20px; background-color: #2e7d32; color: white; text-decoration: none; font-weight: bold; border-radius: 5px; display: inline-block;">🚀 ABRIR PLANILHA COMPLETA</a> ', unsafe_allow_html=True)
    
    st.write("<br>", unsafe_allow_html=True)
    st.subheader("🔍 Histórico Geral de Lançamentos na Planilha (Com Descrição de Itens)")
    
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
    
    novo_item = st.text_input("Qual produto está faltando no estoque?")
    if st.button("Adicionar à Lista"):
        if novo_item:
            st.session_state['itens_falta'].append(novo_item)
            st.rerun()
            
    if st.session_state['itens_falta']:
        for idx, item in enumerate(st.session_state['itens_falta']):
            st.write(f"{idx + 1}. {item}")
        if st.button("🗑️ Limpar Lista"):
            st.session_state['itens_falta'] = []
            st.rerun()
