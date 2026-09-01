import streamlit as st
import pandas as pd
import datetime

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Crediário Loja São José", layout="wide")

# LINKS DA PLANILHA GOOGLE
LINK_ORIGINAL = "https://google.com"
LINK_CSV = "https://google.com"

# AUTENTICAÇÃO SIMPLES
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("🔑 Acesso ao Sistema de Crediário")
    senha = st.text_input("Digite a senha de acesso:", type="password")
    if st.button("Entrar"):
        if senha == "TITITO":
            st.session_state['autenticado'] = True
            st.rerun()
        else:
            st.error("Senha incorreta!")
    st.stop()

# FUNÇÃO PARA CARREGAR DADOS DA PLANILHA
@st.cache_data(ttl=10)
def carregar_dados():
    try:
        df = pd.read_csv(LINK_CSV)
        # Forçar nomes de colunas padrão para evitar erros de leitura
        df.columns = [c.strip().lower() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao ler os dados da Planilha Google: {e}")
        return pd.DataFrame(columns=['id', 'id_cliente', 'valor', 'data', 'status'])

df_vendas = carregar_dados()

# CÁLCULO DE JUROS COMPOSTOS (2% ao mês após 30 dias de carência)
def calcular_valor_atual(valor_original, data_venda_str, status):
    if str(status).strip().lower() == 'pago':
        return int(round(valor_original))
    
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

# INTERFACE PRINCIPAL
st.title("🏬 Sistema de Crediário - Loja São José")

aba1, aba2, aba3 = st.tabs(["📊 Crediário & Consultas", "➕ Lançamentos e Operações", "📦 Itens em Falta"])

with aba1:
    st.header("Histórico de Lançamentos")
    if not df_vendas.empty:
        df_exibicao = df_vendas.copy()
        if 'valor' in df_exibicao.columns and 'data' in df_exibicao.columns and 'status' in df_exibicao.columns:
            df_exibicao['valor_atualizado_r$'] = df_exibicao.apply(
                lambda row: calcular_valor_atual(row['valor'], row['data'], row['status']), axis=1
            )
        st.dataframe(df_exibicao, use_container_width=True)
        
        # Relatório rápido de cobrança
        st.subheader("📋 Relatório de Cobrança (Clientes em Atraso)")
        if 'status' in df_exibicao.columns:
            atrasados = df_exibicao[df_exibicao['status'].str.strip().str.lower() != 'pago']
            if not atrasados.empty:
                st.dataframe(atrasados, use_container_width=True)
            else:
                st.success("Parabéns! Nenhuma conta em atraso identificada.")
    else:
        st.info("Nenhum dado encontrado ou a planilha está vazia.")

with aba2:
    st.header("Lançamentos de Compra Fiado e Pagamentos")
    st.info("💡 Como o aplicativo atual lê a planilha como 'Apenas Leitura pública', use o link no rodapé abaixo para adicionar, alterar ou dar baixa em pagamentos diretamente na planilha do Google Sheets.")

with aba3:
    st.header("Gerenciamento Local de Itens em Falta")
    if 'itens_falta' not in st.session_state:
        st.session_state['itens_falta'] = []
    
    novo_item = st.text_input("Nome do item em falta:")
    if st.button("Adicionar Item"):
        if novo_item:
            st.session_state['itens_falta'].append(novo_item)
            st.success(f"'{novo_item}' adicionado à lista local!")
            st.rerun()
            
    if st.session_state['itens_falta']:
        st.write("### Lista Atual:")
        for item in st.session_state['itens_falta']:
            st.write(f"- {item}")
        if st.button("Limpar Lista de Faltas"):
            st.session_state['itens_falta'] = []
            st.rerun()
    else:
        st.info("Nenhum item marcado como em falta no momento.")

# RODAPÉ COM O LINK CORRIGIDO DA PLANILHA
st.markdown("---")
st.markdown(f"👉 [**Clique aqui para abrir e gerenciar sua Planilha Google diretamente**]({LINK_ORIGINAL})")
