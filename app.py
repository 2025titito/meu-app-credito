import streamlit as st
import pandas as pd
import datetime

# CONFIGURAÇÃO DO APLICATIVO
st.set_page_config(page_title="Crediário - Loja São José", layout="wide", page_icon="🏬")

# LINKS DA SUA PLANILHA GOOGLE (Ajustados para leitura correta)
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

# 2. CARREGAMENTO DOS DADOS EM TEMPO REAL (Sem hibernação de dados)
@st.cache_data(ttl=5)  # Atualiza a cada 5 segundos para os sócios verem em tempo real
def carregar_dados():
    try:
        df = pd.read_csv(LINK_CSV)
        # Padroniza o nome das colunas para evitar conflitos de digitação
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao conectar com a Planilha Google: {e}")
        return pd.DataFrame(columns=['id', 'id_cliente', 'valor', 'data', 'status'])

df_dados = carregar_dados()

# 3. FUNÇÃO MATEMÁTICA DE JUROS COMPOSTOS (2% ao mês após 30 dias de carência)
def calcular_valor_atual(valor_original, data_venda_str, status):
    try:
        valor_original = float(valor_original)
    except:
        return 0
        
    if str(status).strip().lower() == 'pago':
        return 0  # Se já foi totalmente pago, o saldo devedor atual desta linha é zero
    
    try:
        data_venda = pd.to_datetime(data_venda_str).date()
    except:
        return int(round(valor_original))
        
    hoje = datetime.date.today()
    dias_atraso = (hoje - data_venda).days
    
    # Se está dentro da carência de 30 dias, não cobra juros
    if dias_atraso <= 30:
        return int(round(valor_original))
    
    # Calcula os juros baseados nos dias que passaram do prazo de 30 dias
    dias_efetivos_atraso = dias_atraso - 30
    taxa_diaria = 0.02 / 30
    
    valor_atualizado = valor_original * ((1 + taxa_diaria) ** dias_efetivos_atraso)
    return int(round(valor_atualizado))

# 4. TRATAMENTO DOS DADOS PARA O SISTEMA
if not df_dados.empty and 'valor' in df_dados.columns and 'data' in df_dados.columns and 'status' in df_dados.columns:
    # Calcula o valor devedor atual de cada lançamento
    df_dados['saldo_devedor_atual'] = df_dados.apply(
        lambda r: calcular_valor_atual(r['valor'], r['data'], r['status']), axis=1
    )
else:
    df_dados = pd.DataFrame(columns=['id', 'id_cliente', 'valor', 'data', 'status', 'saldo_devedor_atual'])

# INTERFACE PRINCIPAL DO APP
st.title("🏬 Painel de Crediário - Loja São José")
st.write("Gerenciamento compartilhado entre os 3 sócios em tempo real.")

# Abas solicitadas
aba1, aba2, aba3, aba4 = st.tabs([
    "📊 Saldo & Devedores", 
    "📝 Lançar e Baixar Contas", 
    "📋 Histórico de Pagamentos", 
    "📦 Itens em Falta"
])

# ABA 1: SALDO DE FIADO E RELAÇÃO DE DEVEDORES INDIVIDUALIZADOS
with aba1:
    st.header("📊 Resumo Financeiro do Crediário")
    
    total_fiado_atual = df_dados['saldo_devedor_atual'].sum()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="💰 Saldo Total de Fiado na Praça (Com Juros)", value=f"R$ {total_fiado_atual},00")
    
    st.subheader("👥 Relação de Clientes Devedores (Individualizados)")
    if total_fiado_atual > 0:
        # Agrupa e soma as dívidas pelo nome do cliente
        clientes_devedores = df_dados[df_dados['saldo_devedor_atual'] > 0]
        resumo_clientes = clientes_devedores.groupby('id_cliente')['saldo_devedor_atual'].sum().reset_index()
        resumo_clientes.columns = ['Nome do Cliente', 'Total da Dívida Atualizada (R$)']
        
        st.dataframe(resumo_clientes, use_container_width=True)
    else:
        st.success("Não há nenhum saldo pendente ou devedor registrado!")

# ABA 2: LANÇAMENTOS DE COMPRAS FIADO E BAIXAS PARCIAIS
with aba2:
    st.header("📝 Atualizar o Livro de Contas")
    st.write("Como os dados precisam ficar salvos permanentemente para os 3 sócios, clique no botão abaixo para abrir a Planilha Mãe e realizar as seguintes ações:")
    
    st.markdown("""
    * **Para cadastrar uma nova conta**: Adicione uma nova linha preenchendo o `id_cliente` (Nome), `valor`, `data` (ano-mês-dia) e coloque o `status` como *Pendente*.
    * **Para dar baixa parcial ou total**: Altere o `valor` restante da dívida diretamente na linha do cliente ou mude o `status` para *Pago* quando ele liquidar tudo.
    """)
    
    st.markdown(f' <a href="{LINK_ORIGINAL}" target="_blank" style="padding: 15px 25px; background-color: #2e7d32; color: white; text-decoration: none; font-weight: bold; border-radius: 5px;">🚀 ABRIR PLANILHA GOOGLE EM TEMPO REAL</a> ', unsafe_allow_html=True)
    st.write("")
    
    st.subheader("🔍 Visualizar Lançamentos Brutos Atuais")
    st.dataframe(df_dados, use_container_width=True)

# ABA 3: RELAÇÃO DE QUEM EFETUOU PAGAMENTO
with aba3:
    st.header("📋 Histórico de Contas Quitadas")
    if not df_dados.empty and 'status' in df_dados.columns:
        pagos = df_dados[df_dados['status'].str.strip().str.lower() == 'pago']
        if not pagos.empty:
            st.write("Abaixo estão listados os clientes que realizaram pagamentos totais de seus lançamentos:")
            st.dataframe(pagos[['id_cliente', 'valor', 'data']], use_container_width=True)
        else:
            st.info("Nenhum pagamento total registrado no sistema ainda.")
    else:
        st.info("Sem dados de pagamentos disponíveis.")

# ABA 4: RELAÇÃO DE ITENS EM FALTA (Gerenciamento Local)
with aba4:
    st.header("📦 Itens em Falta na Loja")
    if 'itens_falta' not in st.session_state:
        st.session_state['itens_falta'] = []
    
    col_add1, col_add2 = st.columns([3, 1])
    with col_add1:
        novo_item = st.text_input("Qual produto está faltando no estoque?", key="input_item")
    with col_add2:
        st.write("<br>", unsafe_allow_html=True)
        if st.button("Adicionar à Lista"):
            if novo_item:
                st.session_state['itens_falta'].append(novo_item)
                st.rerun()
                
    if st.session_state['itens_falta']:
        st.write("### Lista de Produtos Cadastrados pelos Sócios:")
        for idx, item in enumerate(st.session_state['itens_falta']):
            st.write(f" {idx + 1}. {item}")
            
        if st.button("🗑️ Limpar Toda a Lista de Faltas"):
            st.session_state['itens_falta'] = []
            st.rerun()
    else:
        st.info("Excelente! Nenhum item em falta listado no momento.")

# RODAPÉ DE SEGURANÇA
st.markdown("---")
st.caption("ℹ️ Aplicativo sincronizado com a nuvem do Google Drive. Todas as atualizações feitas na planilha se refletem aqui para os 3 sócios.")
