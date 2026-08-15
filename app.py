import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

# --- CONFIGURAÇÃO DE ACESSO ---
SENHA_CORRETA = "TITITO"  # 👈 DIGITE SUA SENHA SEGURA AQUI (MANTENHA AS ASPAS)
ARQUIVO_DADOS = "dados_credito.json"

st.set_page_config(page_title="Controle Seguro", layout="wide")

def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r") as f: return json.load(f)
        except: return []
    return []

def salvar_dados(dados):
    with open(ARQUIVO_DADOS, "w") as f: json.dump(dados, f, indent=4)

if "vendas" not in st.session_state:
    st.session_state.vendas = carregar_dados()

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔒 Sistema de Controle Restrito")
    senha_digitada = st.text_input("Digite sua senha de acesso:", type="password")
    if st.button("Entrar"):
        if senha_digitada == SENHA_CORRETA:
            st.session_state.autenticado = True
            st.rerun()
        else: st.error("Senha incorreta!")
    st.stop()

st.title("📈 Painel de Controle de Crediário")

# --- PROCESSAMENTO DOS DADOS PARA O RESUMO GERAL ---
total_na_rua = 0.0      
total_recebido = 0.0    
total_atrasado_c_juros = 0.0  
lista_exibicao = []
clientes_criticos = [] 
hoje = datetime.now().date()

for i, venda in enumerate(st.session_state.vendas):
    data_venc = datetime.strptime(venda["vencimento"], "%Y-%m-%d").date()
    val_orig = venda["valor"]
    
    if venda["status"] == "Em aberto":
        total_na_rua += val_orig
        if hoje > data_venc:
            dias_atraso = (hoje - data_venc).days
            
            # REGRA: Juros só começam a partir do 31º dia de atraso
            if dias_atraso > 30:
                dias_com_juros = dias_atraso - 30
                val_atualizado = val_orig * ((1 + 0.02) ** (dias_com_juros / 30))
                situacao = f"⚠️ Crítico ({dias_atraso} dias de atraso)"
                clientes_criticos.append(f"Cliente {venda['id']} ({dias_atraso} dias)")
            else:
                val_atualizado = val_orig
                situacao = f"⚠️ Atrasado Tolerado ({dias_atraso} dias)"
                
            total_atrasado_c_juros += val_atualizado
        else:
            dias_atraso = 0
            val_atualizado = val_orig
            situacao = "✅ Em dia"
    else:
        total_recebido += val_orig
        dias_atraso = 0
        val_atualizado = val_orig
        situacao = "💰 Pago"

    lista_exibicao.append({
        "Índice": i, 
        "Código Cliente (ID)": venda["id"], 
        "Valor Original": f"R$ {val_orig:.2f}", 
        "Vencimento": data_venc.strftime("%d/%m/%Y"), 
        "Dias de Atraso": dias_atraso, 
        "Situação": situacao, 
        "Valor Atualizado": f"R$ {val_atualizado:.2f}"
    })

# --- EXIBIÇÃO DOS DASHBOARDS NO TOPO ---
st.markdown("### 📊 Posição Geral da Loja")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="💵 Total Fiado na Rua (Valor Original)", value=f"R$ {total_na_rua:.2f}")
with col2:
    st.metric(label="✅ Total Recebido (Baixas)", value=f"R$ {total_recebido:.2f}")
with col3:
    st.metric(label="⚠️ Total Vencido Atualizado (Atrasos + Juros)", value=f"R$ {total_atrasado_c_juros:.2f}")

# --- ALERTA DE CLIENTES COM MAIS DE 30 DIAS EM ATRASO ---
if clientes_criticos:
    st.error(f"🚨 **Cobrança Urgente! Clientes com mais de 30 dias de atraso (Juros Ativos):**\n" + ", ".join(clientes_criticos))

st.markdown("---")

# --- ABAS DE NAVEGAÇÃO ---
aba_cadastro, aba_relatorio = st.tabs(["➡️ Lançar Nova Venda", "📋 Relatório de Cobrança"])

with aba_cadastro:
    st.header("Cadastrar Novo Registro")
    id_cliente = st.number_input("Código do Cliente (ID do Excel):", min_value=1, step=1)
    valor_venda = st.number_input("Valor da Venda (R$):", min_value=0.01, step=0.50, format="%.2f")
    data_vencimento = st.date_input("Data de Vencimento:")
    
    if st.button("Salvar Registro"):
        nova_venda = {"id": int(id_cliente), "valor": float(valor_venda), "vencimento": data_vencimento.strftime("%Y-%m-%d"), "status": "Em aberto"}
        st.session_state.vendas.append(nova_venda)
        salvar_dados(st.session_state.vendas)
        st.success(f"Registro do Cliente {id_cliente} salvo.")
        st.rerun()

with aba_relatorio:
    st.header("Situação detalhada dos Pagamentos")
    if not st.session_state.vendas:
        st.info("Nenhuma venda cadastrada ainda.")
    else:
        df = pd.DataFrame(lista_exibicao)
        filtro = st.radio("Filtrar tabela por:", ["Todos", "Apenas Atrasados/Críticos", "Apenas em Dia", "Apenas Pagos"])
        if filtro == "Apenas Atrasados/Críticos": df = df[df["Situação"].str.contains("Atrasado|Crítico")]
        elif filtro == "Apenas em Dia": df = df[df["Situação"] == "✅ Em dia"]
        elif filtro == "Apenas Pagos": df = df[df["Situação"] == "💰 Pago"]
            
        st.dataframe(df.drop(columns=["Índice"]), use_container_width=True)

        st.subheader("Dar Baixa em Pagamento")
        
        # Correção do erro técnico de separação do Índice aqui:
        opcoes_baixar = {f"Cliente {row['Código Cliente (ID)']} (Original: {row['Valor Original']}) - Item {row['Índice']}": row['Índice'] for _, row in df.iterrows() if "Pago" not in row['Situação']}
        
        if opcoes_baixar:
            selecionado = st.selectbox("Selecione o registro para dar baixa:", list(opcoes_baixar.keys()))
            idx_original = opcoes_baixar[selecionado]
            
            if st.button("Confirmar Recebimento"):
                st.session_state.vendas[idx_original]["status"] = "Pago"
                salvar_dados(st.session_state.vendas)
                st.success("Pagamento registrado com sucesso!")
                st.rerun()
