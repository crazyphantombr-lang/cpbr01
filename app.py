# Versão: 1.1.1 (Development)
import streamlit as st
import pandas as pd

# 1. Configurações da Página
st.set_page_config(page_title="Dashboard de Processo Seletivo", layout="wide")

# 2. Definição do Cenário de Vagas (Conforme Edital)
VAGAS = {
    "AC": 22,
    "LB PPI": 3,
    "LB Q": 1,
    "LB PCD": 1,
    "LB EP": 5,
    "LI PPI": 3,
    "LI PCD": 1,
    "LI EP": 8,
    "LI Q": 0
}

def processar_ranqueamento(df):
    """
    Motor matemático que aplica a lógica de cotas e deslocamento.
    """
    # Ordena todos os candidatos pela nota final em ordem decrescente
    df = df.sort_values(by="Nota final", ascending=False).reset_index(drop=True)
    
    # Cria colunas para o resultado
    df["Status Final"] = "🟡 Lista de Espera"
    df["Ocupando Vaga De"] = "-"
    
    # Dicionário para controlar vagas restantes
    vagas_restantes = VAGAS.copy()
    
    # Passo 1: Preencher Ampla Concorrência (AC)
    for index, row in df.iterrows():
        status_req = str(row["Situação do requerimento de matrícula"]).upper()
        
        # Ignora quem já está desclassificado ou desistente na planilha base
        if "DESCLASSIFICADO" in status_req or "DESISTENTE" in status_req or "REPROVADO" in status_req:
            df.at[index, "Status Final"] = f"🔴 {row['Situação do requerimento de matrícula']}"
            continue
            
        if vagas_restantes["AC"] > 0:
            df.at[index, "Status Final"] = "🟢 Aprovado - AC"
            df.at[index, "Ocupando Vaga De"] = "AC"
            vagas_restantes["AC"] -= 1

    # Passo 2: Preencher Cotas
    for index, row in df.iterrows():
        # Se já foi aprovado na AC ou foi desclassificado, pula
        if df.at[index, "Status Final"] != "🟡 Lista de Espera":
            continue
            
        cota_candidato = str(row["Cota do candidato"]).strip()
        
        # Verifica se o candidato pertence a uma cota válida e se há vaga
        if cota_candidato in vagas_restantes and vagas_restantes[cota_candidato] > 0:
            df.at[index, "Status Final"] = f"🔵 Aprovado - {cota_candidato}"
            df.at[index, "Ocupando Vaga De"] = cota_candidato
            vagas_restantes[cota_candidato] -= 1

    return df

def main():
    st.title("🏆 Resultado Oficial - Processo Seletivo")
    st.markdown("---")

    # 3. Leitura dos Dados (Agora aceitando Excel)
    arquivo_upado = st.file_uploader("Carregue sua planilha Excel (.xlsx ou .xls) aqui", type=["xlsx", "xls"])
    
    if arquivo_upado is not None:
        # Lê o Excel nativamente
        df_bruto = pd.read_excel(arquivo_upado)
        
        # Processa a lógica
        df_processado = processar_ranqueamento(df_bruto)
        
        # 4. KPIs (Indicadores Visuais)
        total_inscritos = len(df_processado)
        aprovados_ac = len(df_processado[df_processado["Ocupando Vaga De"] == "AC"])
        aprovados_cotas = len(df_processado[(df_processado["Ocupando Vaga De"] != "AC") & (df_processado["Ocupando Vaga De"] != "-")])
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Inscritos", total_inscritos)
        col2.metric("Vagas AC Preenchidas", f"{aprovados_ac} / {VAGAS['AC']}")
        col3.metric("Vagas Cotas Preenchidas", f"{aprovados_cotas} / {sum(VAGAS.values()) - VAGAS['AC']}")
        col4.metric("Vagas Totais Ofertadas", sum(VAGAS.values()))
        
        st.markdown("---")
        
        # 5. Interface de Abas (Tabs)
        # Cria uma lista de abas ignorando a cota LI Q que tem 0 vagas
        abas_nomes = ["Visão Geral", "AC"] + [cota for cota, qtd in VAGAS.items() if cota != "AC" and qtd > 0]
        tabs = st.tabs(abas_nomes)
        
        # Colunas que serão exibidas na tabela final para ficar limpo
        colunas_exibicao = ["Inscrição", "Nome", "Nota final", "Cota do candidato", "Situação do requerimento de matrícula", "Status Final", "Ocupando Vaga De"]
        
        # Preenchendo a Aba "Visão Geral"
        with tabs[0]:
            st.subheader("Ranking Geral")
            st.dataframe(df_processado[colunas_exibicao], use_container_width=True, hide_index=True)
            
        # Preenchendo a Aba "AC"
        with tabs[1]:
            st.subheader("Ampla Concorrência (AC)")
            filtro_ac = df_processado[(df_processado["Ocupando Vaga De"] == "AC") | (df_processado["Status Final"] == "🟡 Lista de Espera")]
            st.dataframe(filtro_ac[colunas_exibicao], use_container_width=True, hide_index=True)
            
        # Preenchendo as Abas de Cotas
        for i, nome_cota in enumerate(abas_nomes[2:], start=2):
            with tabs[i]:
                st.subheader(f"Cota: {nome_cota}")
                # Mostra apenas candidatos que se inscreveram NESTA cota
                filtro_cota = df_processado[df_processado["Cota do candidato"] == nome_cota]
                st.dataframe(filtro_cota[colunas_exibicao], use_container_width=True, hide_index=True)
                
    else:
        st.info("👆 Por favor, faça o upload da sua planilha Excel extraída do sistema para gerar o Dashboard.")

if __name__ == "__main__":
    main()
