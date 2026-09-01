import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

# CONFIGURAÇÃO DO APLICATIVO
st.set_page_config(page_title="Crediário - Loja São José", layout="wide", page_icon="🏬")

# URL DA PLANILHA GOOGLE
URL_PLANILHA = "https://google.com"

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

# 2. CONEXÃO DIRETA COM O GOOGLE SHEETS (LEITURA E ESCRITA SEM CHAVES CONFIGURADAS)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_dados = conn.read(spreadsheet=URL_PLANILHA, ttl="2s")
    df_dados.columns = [str(c).strip().lower() for c in df_dados.columns]
except Exception as e:
    st.error(f"Erro ao conectar com a Planilha: {e}")
    df_dados = pd.DataFrame(columns=['id', 'id_cliente', 'valor', 'data', 'status', 'descricao'])

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

# PROCESSAMENTO DOS JUROS
if not df_dados.empty and 'valor' in df_dados.columns and 'data' in df_dados.columns and 'status' in df_dados.columns:
    df_dados['saldo_devedor_atual'] = df_dados.apply(
        lambda r: calcular_valor_atual(r['valor'], r['data'], r['status']), axis=1
    )
else:
    df_dados['saldo_devedor_atual'] = 0

# INTERFACE PRINCIPAL
st.title("🏬 Painel de Crediário - Loja São José")

aba1, aba2, aba3, aba4 = st.tabs([
    "📊 Saldo & Devedores", 
    "📝 Cadastrar Novo Fiado", 
    "💰 Consultar Histórico / Baixas", 
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

# ABA 2: FORMULÁRIO DE CADASTRO DIRETO NO APP (SEM ABRIR A PLANILHA)
with aba2:
    st.header("📝 Cadastrar Nova Conta Fiada")
    st.write("Preencha os dados abaixo. Ao clicar em salvar, as informações irão direto para a planilha na nuvem.")
    
    with st.form("form_cadastro_direto"):
        nome_cliente = st.text_input("Nome Completo do Cliente:")
        valor_venda = st.number_input("Valor da Compra (R$):", min_value=1, step=1)
        data_venda = st.date_input("Data da Compra:", datetime.date.today())
        descricao_compra = st.text_area("O que foi comprado? (Ex: 1 Calça Jeans, 2 Camisetas)")
        
        botao_salvar = st.form_submit_button("💾 Salvar no Sistema")
        
        if botao_salvar:
            if nome_cliente.strip() == "":
                st.error("Por favor, preencha o nome do cliente.")
            else:
                try:
                    # Cria a nova linha estruturada
                    nova_linha = pd.DataFrame([{
                        "id": int(len(df_dados) + 1),
                        "id_cliente": nome_cliente.strip(),
                        "valor": int(valor_venda),
                        "data": data_venda.strftime("%Y-%m-%d"),
                        "status": "Pendente",
                        "descricao": descricao_compra.strip()
                    }])
                    
                    # Junta com os dados existentes e atualiza a planilha mãe
                    df_atualizado = pd.concat([df_dados.drop(columns=['saldo_devedor_atual'], errors='ignore'), nova_linha], ignore_index=True)
                    conn.update(spreadsheet=URL_PLANILHA, data=df_atualizado)
                    
                    st.success(f"Excelente! A conta de {nome_cliente} de R$ {valor_venda},00 foi gravada com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar direto: {e}. Verifique se a planilha está com acesso de 'Editor' liberado para qualquer pessoa com o link.")

# ABA 3: CONSULTAR HISTÓRICO GERAL
with aba3:
    st.header("💰 Histórico Geral e Controle de Lançamentos")
    st.write("Abaixo estão listados todos os registros armazenados no seu livro virtual. Se precisar apagar ou dar baixa manual, use o link de segurança:")
    st.markdown(f'👉 [Abrir Planilha Google Mãe para Alterações/Exclusões]({URL_PLANILHA})')
    
    st.write("<br>", unsafe_allow_html=True)
    if not df_dados.empty:
        colunas_exibicao = [c for c in ['id', 'id_cliente', 'valor', 'data', 'status', 'descricao', 'saldo_devedor_atual'] if c in df_dados.columns]
        st.dataframe(df_dados[colunas_exibicao], use_container_width=True)
    else:
        st.info("Nenhum registro encontrado.")

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
