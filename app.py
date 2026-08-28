import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date

# 1. CONFIGURAÇÕES VISUAIS
st.set_page_config(page_title="Controle de Crediário", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 5px; }
    .stButton>button:hover { background-color: #1b5e20; color: white; }
    .alerta-critico { background-color: #ffebee; color: #c62828; padding: 15px; border-radius: 5px; border-left: 5px solid #c62828; margin-bottom: 10px; }
    .item-falta { background-color: #fff3e0; color: #e65100; padding: 10px; border-radius: 5px; margin-bottom: 5px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# 2. CONTROLE DE ACESSO (TELA DE LOGIN)
def tela_login():
    st.title("🔑 Acesso ao Sistema")
    SENHA_CORRETA = "TITITO" 
    senha_digitada = st.text_input("Digite a senha da loja:", type="password")
    if st.button("Entrar"):
        if senha_digitada == SENHA_CORRETA:
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Senha incorreta. Tente novamente.")

if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    tela_login()
    st.stop()

# 3. CONEXÃO DIRETA E NATIVA COM O GOOGLE SHEETS (SEM COMPLICAÇÕES)
URL_CSV = "https://google.com"

def carregar_dados():
    try:
        # Lê a planilha diretamente da internet usando apenas o pandas nativo
        df = pd.read_csv(URL_CSV)
        df.columns = df.columns.str.strip()
        return df.dropna(subset=['id']).to_dict(orient='records')
    except:
        return []

st.session_state.vendas = carregar_dados()

if 'itens_falta' not in st.session_state:
    st.session_state.itens_falta = []

# 4. FUNÇÃO DE CÁLCULO DE JUROS ARREDONDADOS
def calcular_valores_atuais(venda):
    if str(venda.get('status', '')).strip().lower() == 'pago':
        return 0, 0, 0
        
    try:
        valor_original = float(venda.get('valor', 0))
    except:
        return 0, 0, 0
        
    try:
        data_venda = datetime.strptime(str(venda.get('data', '')).strip(), "%Y-%m-%d").date()
    except:
        return int(round(valor_original)), 0, int(round(valor_original))
        
    hoje = date.today()
    dias_atraso = (hoje - data_venda).days
    juros_acumulados = 0.0
    
    if dias_atraso > 30:
        dias_com_juros = dias_atraso - 30
        taxa_mensal = 0.02
        taxa_diaria = (1 + taxa_mensal) ** (1 / 30) - 1
        valor_com_juros = valor_original * ((1 + taxa_diaria) ** dias_com_juros)
        juros_acumulados = valor_com_juros - valor_original
    
    total_atualizado = valor_original + juros_acumulados
    return int(round(valor_original)), int(round(juros_acumulados)), int(round(total_atualizado))

# 5. CÁLCULO DOS INDICADORES
total_na_rua = 0
total_recebido = 0
total_vencido_com_juros = 0
alertas_criticos = []

for v in st.session_state.vendas:
    status_venda = str(v.get('status', '')).strip().lower()
    try:
        valor_venda = float(v.get('valor', 0))
    except:
        valor_venda = 0.0
        
    if status_venda == 'pago':
        total_recebido += int(round(valor_venda))
    else:
        v_orig, v_jur, v_tot = calcular_valores_atuais(v)
        total_na_rua += v_orig
        try:
            dias = (date.today() - datetime.strptime(str(v.get('data', '')).strip(), "%Y-%m-%d").date()).days
            if dias > 30:
                total_vencido_com_juros += v_tot
                alertas_criticos.append({'id_cliente': v.get('id_cliente'), 'dias': dias, 'valor': v_tot})
        except:
            pass

# 6. INTERFACE DO USUÁRIO
st.title("🏪 Sistema de Controle de Crediário")

col1, col2, col3 = st.columns(3)
col1.metric("💰 Total Fiado na Rua", f"R$ {total_na_rua},00")
col2.metric("✅ Total Recebido", f"R$ {total_recebido},00")
col3.metric("🚨 Total Vencido (+30 dias)", f"R$ {total_vencido_com_juros},00")

st.divider()
aba_lancar, aba_relatorio, aba_baixa, aba_falta = st.tabs([
    "📝 Lançar Venda", "📋 Relatório de Cobrança", "💵 Dar Baixa em Pagamento", "🛒 Itens em Falta"
])

# ABA 1: FORMULÁRIO DE LANÇAMENTO
with aba_lancar:
    st.subheader("Registrar Nova Venda no Fiado")
    id_cliente = st.number_input("ID do Cliente (Apenas número):", min_value=1, step=1)
    valor_venda = st.number_input("Valor da Venda (Apenas número inteiro, ex: 150):", min_value=1, step=1)
    data_venda = st.date_input("Data da Venda:", date.today())
    
    st.markdown("---")
    st.warning("Como estamos usando a integração limpa e segura do Google, clique no botão abaixo para registrar a venda. Ela entrará na planilha e atualizará o app de todos os sócios automaticamente.")
    
    # Link direto para abrir a planilha e registrar de forma limpa caso queiram direto na fonte
    st.markdown(f"[👉 Clique aqui para abrir e gerenciar a sua Planilha Google diretamente](https://google.com)")

# ABA 2: RELATÓRIO DE COBRANÇA
with aba_relatorio:
    st.subheader("Contas em Atraso Crítico (> 30 dias)")
    if alertas_criticos:
        for al in alertas_criticos:
            st.markdown(f"""
            <div class="alerta-critico">
                ⚠️ <b>Cliente {int(al['id_cliente'])}</b> está com a conta atrasada há <b>{al['dias']} dias</b>.<br>
                Valor arredondado com juros: <b>R$ {al['valor']},00</b>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Nenhum cliente em atraso crítico no momento.")
        
    st.subheader("Todos os Fiados Ativos")
    dados_tabela = []
    for v in st.session_state.vendas:
        if str(v.get('status', '')).strip().lower() == 'pendente':
            v_orig, v_jur, v_tot = calcular_valores_atuais(v)
            dados_tabela.append({
                "Cód. Venda": int(v.get('id')),
                "ID Cliente": f"Cliente {int(v.get('id_cliente'))}",
                "Data da Compra": v.get('data'),
                "Valor Original": f"R$ {v_orig},00",
                "Juros Acumulados": f"R$ {v_jur},00",
                "Total Atualizado": f"R$ {v_tot},00"
            })
            
    if dados_tabela:
        st.dataframe(pd.DataFrame(dados_tabela), use_container_width=True)
    else:
        st.write("Não há contas pendentes.")

# ABA 3: COMO DAR BAIXA
with aba_baixa:
    st.subheader("Dar Baixa em Pagamento")
    st.write("Para dar baixa em um pagamento, abra a sua Planilha Google pelo link da Aba 1 e simplesmente mude o status daquela venda de `Pendente` para `Pago`. O app atualizará na hora!")

# ABA 4: ITENS EM FALTA
with aba_falta:
    st.subheader("📝 Comunicar Item em Falta")
    novo_item = st.text_input("Qual produto está faltando na prateleira?", placeholder="Ex: Arroz Tipo 1, Detergente Maçã...")
    
    if st.button("Adicionar à Lista de Compras"):
        if novo_item.strip():
            st.session_state.itens_falta.append(novo_item.strip())
            st.success(f"'{novo_item}' adicionado à lista!")
            st.rerun()
            
    st.divider()
    st.subheader("🛒 Lista de Compras da Loja")
    if st.session_state.itens_falta:
        for idx, item in enumerate(st.session_state.itens_falta):
            col_item, col_btn = st.columns([4, 1])
            col_item.markdown(f'<div class="item-falta">🔸 {item}</div>', unsafe_allow_html=True)
            if col_btn.button("Marcar como Comprado", key=f"btn_{idx}"):
                st.session_state.itens_falta.pop(idx)
                st.rerun()
    else:
        st.info("Excelente! Nenhum item em falta no momento.")
