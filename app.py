import streamlit as st
import pandas as pd
import datetime
import gspread

# CONFIGURAÇÃO DO APLICATIVO
st.set_page_config(page_title="Crediário - Loja São José", layout="wide", page_icon="🏬")

# LINKS E CONFIGURAÇÃO DA PLANILHA GOOGLE
LINK_ORIGINAL = "https://google.com"
LINK_CSV = "https://google.com"

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

# PROCESSAMENTO DE DADOS
if not df_dados.empty and 'valor' in df_dados.columns and 'data' in df_dados.columns and 'status' in df_dados.columns:
    df_dados['saldo_devedor_atual'] = df_dados.apply(
        lambda r: calcular_valor_atual(r['valor'], r['data'], r['status']), axis=1
    )
else:
    df_dados = pd.DataFrame(columns=['id', 'id_cliente', 'valor', 'data', 'status', 'descricao', 'saldo_devedor_atual'])

# FUNÇÃO PARA GRAVAR NA PLANILHA VIA FORMULÁRIO (INCLUINDO DESCRIÇÃO)
def Adicionar_Linha_Planilha(nome, valor, data_formatada, descricao_itens):
    try:
        gc = gspread.public()
        sh = gc.open_by_url(LINK_ORIGINAL)
        worksheet = sh.get_worksheet(0)
        
        proximo_id = len(df_dados) + 1
        
        # Grava os dados incluindo a descrição na 6ª coluna
        worksheet.append_row([proximo_id, nome, valor, data_formatada, "Pendente", descricao_itens])
        return True
    except Exception as e:
        st.error(f"Erro técnico ao salvar: {e}. Certifique-se de que a planilha está configurada como 'Qualquer pessoa com o link pode editar' e que você criou a coluna 'descricao'.")
        return False

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

# ABA 2: FORMULÁRIO DIDÁTICO DE CADASTRO COM DESCRIÇÃO
with aba2:
    st.header("📝 Cadastrar Nova Conta no Livro")
    st.write("Preencha os campos abaixo para registrar o fiado de um cliente. O sistema salvará na nuvem automaticamente.")
    
    with st.form("form_cadastro"):
        nome_cliente = st.text_input("Nome Completo do Cliente:")
        valor_venda = st.number_input("Valor da Compra (R$):", min_value=1, step=1)
        data_venda = st.date_input("Data da Compra:", datetime.date.today())
        # CAMPO NOVO ADICIONADO AQUI
        descricao_compra = st.text_area("O que foi comprado? (Ex: 1 Calça Jeans, 2 Camisetas)", help="Detalhe os itens aqui para consulta futura dos sócios.")
        
        botao_salvar = st.form_submit_button("💾 Salvar no Sistema")
        
        if botao_salvar:
            if nome_cliente.strip() == "":
                st.error("Por favor, digite o nome do cliente.")
            else:
                data_texto = data_venda.strftime("%Y-%m-%d")
                sucesso = Adicionar_Linha_Planilha(nome_cliente.strip(), int(valor_venda), data_texto, descricao_compra.strip())
                if sucesso:
                    st.success(f"Sucesso! A conta de {nome_cliente} de R$ {valor_venda},00 foi salva.")
                    st.cache_data.clear()
                    st.rerun()

# ABA 3: OPERAÇÃO DE BAIXAS PARCIAIS OU TOTAIS
with aba3:
    st.header("💰 Dar Baixa em Pagamentos")
    st.write("Para fazer alterações, exclusões ou atualizar valores que os clientes pagaram parcialmente, clique no botão seguro abaixo:")
    st.markdown(f' <a href="{LINK_ORIGINAL}" target="_blank" style="padding: 12px 20px; background-color: #2e7d32; color: white; text-decoration: none; font-weight: bold; border-radius: 5px;">🚀 ABRIR PLANILHA COMPLETA</a> ', unsafe_allow_html=True)
    
    st.write("<br>", unsafe_allow_html=True)
    st.subheader("🔍 Histórico Geral de Lançamentos na Planilha (Com Descrição de Itens)")
    
    # Reorganiza para exibir a descrição de forma bonita na tabela de histórico
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
