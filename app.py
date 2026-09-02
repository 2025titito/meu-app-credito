import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração da página limpa e larga
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

# Configuração estável de links de dados da loja
ID_PLANILHA = "1fExWOzkkBk9qGpaaDP_pfnwnjiV90FSTAgnTOvAxgqs"
GID_AHA = "2113690102"

# Formato estável de exportação em CSV puro para evitar erros de conexão
URL_CSV = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?format=csv&gid={GID_AHA}"

# Inicialização segura do estado local caso a rede falhe temporariamente
if "banco_local_backup" not in st.session_state:
    st.session_state.banco_local_backup = pd.DataFrame(columns=["id", "id_cliente", "valor", "data", "status", "descricao"])

# Função otimizada para carregar dados sem travar a tela em erros de rede
def carregar_dados_estavel():
    try:
        # Tenta ler o CSV aplicando um tempo limite de conexão
        df = pd.read_csv(URL_CSV, timeout=5)
        df.columns = [str(col).strip().lower() for col in df.columns]
        
        if 'data' in df.columns and 'valor' in df.columns:
            df['data'] = pd.to_datetime(df['data']).dt.date
            df['valor'] = pd.to_numeric(df['valor']).fillna(0)
            st.session_state.banco_local_backup = df.copy()
            return df
    except Exception:
        # Se a rede da nuvem cair, usa o último backup estável da sessão automaticamente
        pass
    return st.session_state.banco_local_backup

# Função para calcular juros compostos (2% ao mês após 30 dias de carência)
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

# Carrega a base de dados
df_dados = carregar_dados_estavel()

if not df_dados.empty and 'data' in df_dados.columns:
    df_dados['valor_atual'] = df_dados.apply(calcular_valor_atual, axis=1)
else:
    df_dados['valor_atual'] = 0

# Criação das 4 Abas Visuais do Sistema
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
        st.info("Nenhum registro ativo encontrado no momento.")

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
        
        botao_salvar = st.form_submit_button("Gravar Fiado no Sistema")
        
        if botao_salvar:
            if id_cliente and valor > 0:
                # Cria a linha estruturada temporária em cache para visualização imediata
                nova_linha = pd.DataFrame([{
                    "id": len(df_dados) + 1,
                    "id_cliente": id_cliente,
                    "valor": valor,
                    "data": data_compra,
                    "status": "Pendente",
                    "descricao": descricao,
                    "valor_atual": valor
                }])
                st.session_state.banco_local_backup = pd.concat([st.session_state.banco_local_backup, nova_linha], ignore_index=True)
                st.success(f"Sucesso! Registro de R$ {valor} para '{id_cliente}' lançado localmente na sessão.")
                st.rerun()
            else:
                st.warning("Por favor, preencha o nome do cliente e o valor.")

# ---------------------------------------------------------
# ABA 3: DAR BAIXA / PAGAMENTOS (Tela interna sem ícones externos)
# ---------------------------------------------------------
with aba3:
    st.header("Dar Baixa em Pagamentos")
    st.write("Dê baixa total nas contas dos clientes diretamente por esta tela, sem precisar acessar planilhas externas:")
    
    if not df_dados.empty and 'id_cliente' in df_dados.columns:
        # Filtra registros que possuem valores devendo maiores que zero
        df_devedores = df_dados[df_dados['valor_atual'] > 0]
        
        if not df_devedores.empty:
            lista_clientes = sorted(df_devedores['id_cliente'].unique())
            
            # Formulário nativo interno para processar a baixa
            with st.form("form_baixa_interna", clear_on_submit=True):
                cliente_selecionado = st.selectbox("Selecione o Cliente para dar Baixa:", lista_clientes)
                
                botao_confirmar_baixa = st.form_submit_button("Confirmar Quitação Integral")
                
                if botao_confirmar_baixa:
                    # Altera o status de pendente para pago dentro da memória local estável
                    st.session_state.banco_local_backup.loc[
                        st.session_state.banco_local_backup['id_cliente'] == cliente_selecionado, 'status'
                    ] = "Pago"
                    
                    st.success(f"Pronto! Todas as contas vigentes de '{cliente_selecionado}' foram marcadas como PAGAS!")
                    st.rerun()
        else:
            st.info("Não há nenhuma dívida pendente registrada no momento.")
    else:
        st.info("Não há devedores listados no sistema.")

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
