import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Loja Sao Jose", layout="wide")

# --- CONFIGURAÇÃO DE SEGURANÇA (SENHA) ---
SENHA_CORRETA = "TITITO"

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

def tela_login():
    st.title("🔒 Acesso ao Sistema de Crediário")
    senha = st.text_input("Digite a senha de acesso:", type="password")
    if st.button("Entrar"):
        if senha == SENHA_CORRETA:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta. Tente novamente.")

if not st.session_state["autenticado"]:
    tela_login()
    st.stop()

# --- FUNÇÕES DE BANCO DE DADOS (JSON) ---
ARQUIVO_DADOS = "dados_credito.json"
ARQUIVO_COMPRAS = "lista_compras.json"
ARQUIVO_CAIXA = "historico_caixa.json"

def carregar_json(arquivo):
    if os.path.exists(arquivo):
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def salvar_json(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

dados = carregar_json(ARQUIVO_DADOS)
compras = carregar_json(ARQUIVO_COMPRAS)
caixa_dados = carregar_json(ARQUIVO_CAIXA)

# --- FUNÇÃO PARA CALCULAR JUROS COM CARÊNCIA ---
def calcular_saldo_atual(valor_original, data_venda_str):
    data_venda = datetime.strptime(data_venda_str, "%Y-%m-%d").date()
    hoje = date.today()
    dias_atraso = (hoje - data_venda).days
    
    if dias_atraso <= 30:
        return float(valor_original), dias_atraso, False
    
    dias_com_juros = dias_atraso - 30
    taxa_mensal = 0.02
    taxa_diaria = (1 + taxa_mensal) ** (1 / 30) - 1
    
    valor_atualizado = valor_original * ((1 + taxa_diaria) ** dias_com_juros)
    
    return round(valor_atualizado, 2), dias_atraso, True

# --- PROCESSAMENTO DOS DADOS PARA O PAINEL ---
total_fiado_na_rua = sum(v["valor"] for v in dados if v["status"] == "Pendente")
total_recebido = sum(v.get("valor_pago", 0.0) for v in dados if v["status"] == "Pago")
total_vencido_com_juros = 0.0

for venda in dados:
    if venda["status"] == "Pendente":
        valor_atual, _, critico = calcular_saldo_atual(venda["valor"], venda["data"])
        if critico:
            total_vencido_com_juros += valor_atual

# --- INTERFACE DO USUÁRIO ---
st.title("🔒 Crediário e Gestão - Loja São José")

# Painel de Faturamento no Topo
col1, col2, col3 = st.columns(3)
col1.metric(label="Total Fiado na Rua (Original)", value=f"R$ {total_fiado_na_rua:,.2f}")
col2.metric(label="Total Recebido (Histórico)", value=f"R$ {total_recebido:,.2f}")
col3.metric(label="Total Vencido Atualizado (Com Juros)", value=f"R$ {total_vencido_com_juros:,.2f}")

st.markdown("---")

# Criação das 5 Abas Solicitadas pelos Sócios
(aba_lancar, aba_relatorio, aba_baixa, aba_compras, aba_caixa) = st.tabs([
    "📝 Lançar Venda", 
    "📋 Relatório de Cobrança", 
    "✅ Dar Baixa em Pagamento",
    "🛒 Itens em Falta",
    "📊 Fechamento de Caixa"
])

# ABA 1: LANÇAR VENDA (Com campo para descrever o item comprado)
with aba_lancar:
    st.subheader("Registrar Novo Fiado")
    with st.form("form_venda", clear_on_submit=True):
        id_cliente = st.number_input("ID do Cliente (Consulte seu Excel físico):", min_value=1, step=1)
        valor_venda = st.number_input("Valor da Venda (R$):", min_value=0.01, step=0.01)
        data_venda = st.date_input("Data da Venda:", value=date.today())
        descricao_venda = st.text_input("Descrição dos Itens (Opcional):", placeholder="Ex: Calça Jeans e Camiseta")
        
        botao_salvar = st.form_submit_button("Salvar Registro")
        
        if botao_salvar:
            nova_venda = {
                "id_venda": len(dados) + 1,
                "id_cliente": int(id_cliente),
                "valor": float(valor_venda),
                "data": str(data_venda),
                "descricao": str(descricao_venda),
                "status": "Pendente",
                "valor_pago": 0.0,
                "data_pagamento": ""
            }
            dados.append(nova_venda)
            salvar_json(ARQUIVO_DADOS, dados)
            st.success(f"Venda para o Cliente {id_cliente} gravada com sucesso!")
            st.rerun()

# ABA 2: RELATÓRIO DE COBRANÇA (Filtro por ID + Descrição)
with aba_relatorio:
    st.subheader("Situação Atual dos Clientes")
    
    busca_id = st.text_input("🔍 Buscar por ID do Cliente (Deixe vazio para ver todos):", placeholder="Ex: Cliente 5")
    
    tabela_exibicao = []
    existe_critico = False
    
    for venda in dados:
        if venda["status"] == "Pendente":
            texto_cliente = f"Cliente {venda['id_cliente']}"
            
            # Aplica o filtro de busca se o usuário digitar algo
            if busca_id and busca_id.lower() not in texto_cliente.lower():
                continue
                
            valor_atual, dias, critico = calcular_saldo_atual(venda["valor"], venda["data"])
            status_texto = "🔴 CRÍTICO (+30 dias)" if critico else "🟢 No Prazo"
            if critico:
                existe_critico = True
                
            tabela_exibicao.append({
                "ID Venda": venda["id_venda"],
                "ID Cliente": texto_cliente,
                "Descrição": venda.get("descricao", "Não informada"),
                "Data da Venda": venda["data"],
                "Valor Original": f"R$ {venda['valor']:.2f}",
                "Valor Atualizado": f"R$ {valor_atual:.2f}",
                "Dias de Atraso": dias,
                "Alerta": status_texto
            })
            
    if tabela_exibicao:
        if existe_critico:
            st.error("⚠️ ATENÇÃO: Existem contas na rua com mais de 30 dias de atraso acumulando juros!")
        df = pd.DataFrame(tabela_exibicao)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma conta pendente encontrada.")

# ABA 3: DAR BAIXA EM PAGAMENTO (Atualizada)
with aba_baixa:
    st.subheader("Quitar Conta de Cliente")
    vendas_pendentes_lista = [
        f"Venda {v['id_venda']} - Cliente {v['id_cliente']} ({v.get('descricao', 'Sem descrição')}) - Orig: R$ {v['valor']:.2f}" 
        for v in dados if v["status"] == "Pendente"
    ]
    
    if vendas_pendentes_lista:
        venda_selecionada = st.selectbox("Escolha a venda para dar baixa:", vendas_pendentes_lista)
        
        # Extrai o ID da venda limpando o texto de forma simples e segura
        # Pega a parte antes do primeiro traço '-' e remove a palavra 'Venda '
        id_venda_baixa = int(venda_selecionada.split(" - ")[0].replace("Venda ", ""))
        
        venda_objeto = next(v for v in dados if v["id_venda"] == id_venda_baixa)
        valor_sugerido, _, _ = calcular_saldo_atual(venda_objeto["valor"], venda_objeto["data"])
        
        valor_recebido_input = st.number_input("Valor Recebido (R$):", min_value=0.00, value=float(valor_sugerido), step=0.01)
        
        if st.button("Confirmar Pagamento"):
            for v in dados:
                if v["id_venda"] == id_venda_baixa:
                    v["status"] = "Pago"
                    v["valor_pago"] = float(valor_recebido_input)
                    v["data_pagamento"] = str(date.today())
                    break
            salvar_json(ARQUIVO_DADOS, dados)
            st.success("Baixa registrada com sucesso!")
            st.rerun()
    else:
        st.info("Não há contas pendentes para dar baixa.")

# ABA 4: ITENS EM FALTA (Substitui a folha de papel)
with aba_compras:
    st.subheader("🛒 Lista de Compras Compartilhada")
    
    with st.form("form_compras", clear_on_submit=True):
        novo_item = st.text_input("O que está faltando na loja?", placeholder="Ex: Arroz Tipo 1 ou Detergente Y")
        quem_pediu = st.text_input("Quem anotou / Solicitado por:", placeholder="Ex: Titito")
        botao_lista = st.form_submit_button("Adicionar à Lista")
        
        if botao_lista and novo_item:
            compras.append({
                "id_item": len(compras) + 1,
                "item": novo_item,
                "solicitante": quem_pediu,
                "data": str(date.today()),
                "status": "Pendente"
            })
            salvar_json(ARQUIVO_COMPRAS, compras)
            st.success("Item adicionado à lista de compras!")
            st.rerun()
            
    st.write("---")
    st.markdown("### 📋 Itens que precisam ser comprados:")
    
    itens_ativos = [c for c in compras if c["status"] == "Pendente"]
    
    if itens_ativos:
        for idx, item in enumerate(itens_ativos):
            col_txt, col_btn = st.columns([4, 1])
            col_txt.markdown(f"**📌 {item['item']}** — *Anotado por {item['solicitante']} em {item['data']}*")
            
            if col_btn.button(f"Comprado ✅", key=f"btn_compra_{item['id_item']}_{idx}"):
                for c in compras:
                    if c["id_item"] == item["id_item"]:
                        c["status"] = "Comprado"
                        break
                salvar_json(ARQUIVO_COMPRAS, compras)
                st.rerun()
    else:
        st.info("A lista está vazia! Todos os produtos estão abastecidos.")

# ABA 5: FECHAMENTO DE CAIXA DIÁRIO (Substitui a Planilha Excel)
with aba_caixa:
    st.subheader("📊 Registrar Fechamento de Caixa Diário")
    
    with st.form("form_caixa", clear_on_submit=True):
        data_caixa = st.date_input("Data do Movimento:", value=date.today())
        v_dinheiro = st.number_input("Vendas em Dinheiro (R$):", min_value=0.00, step=0.01)
        v_pix = st.number_input("Vendas em PIX (R$):", min_value=0.00, step=0.01)
        v_cartao = st.number_input("Vendas em Cartão (R$):", min_value=0.00, step=0.01)
