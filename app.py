# Versão: 1.2.1 (Stable Feature)
import streamlit as st
import pandas as pd

# 1. Configurações Iniciais
st.set_page_config(page_title="DASHBOARD PROCESSOS SELETIVOS", layout="wide")

VAGAS_PADRAO = {
    "AC": 22, "LI_EP": 8, "LB_EP": 5, "LI_PPI": 3, "LB_PPI": 3, "LI_PCD": 1, "LB_PCD": 1, "LB_Q": 1
}

# 2. Lógica de Status Complexa
MAPA_STATUS_FIXO = {
    "Etapa 2 concluída": "🟢 Matriculado",
    "Etapa 1 concluída": "🔵 Etapa 1 concluída",
    "Desistiu da vaga": "🔴 Matrícula cancelada",
    "Matrícula cancelada": "🔴 Matrícula cancelada",
    "Indeferido": "🔴 Matrícula cancelada",
    "Enviou documentação": "🟡 Em processo",
    "Enviou recurso": "🟡 Em processo",
    "Enviar recurso": "🟡 Em processo",
    "Aguardando vaga": "⚪ Aguardando vaga"
}

def determinar_status(row):
    status_orig = str(row["Situação do requerimento de matrícula"]).strip()
    convocacoes = row["Nº de convocações"]
    
    # Se o status existe no mapa fixo, retorna ele
    if status_orig in MAPA_STATUS_FIXO:
        return MAPA_STATUS_FIXO[status_orig]
    
    # Lógica para Status em Branco/Vazio
    if pd.isna(row["Situação do requerimento de matrícula"]) or status_orig.lower() in ['nan', '']:
        if convocacoes > 0:
            return "🔴 Não compareceu"
        else:
            return "⚪ Lista de espera"
            
    return "⚪ Aguardando vaga"

def processar_dados(df):
    df = df.copy()
    # Tratamento de colunas numéricas e strings
    df["Nota final"] = pd.to_numeric(df["Nota final"], errors='coerce').fillna(0)
    df["Nº de convocações"] = pd.to_numeric(df["Nº de convocações"], errors='coerce').fillna(0)
    df["Curso"] = df["Curso"].fillna("Não Informado").astype(str)
    df["Processo seletivo"] = df["Processo seletivo"].fillna("Geral").astype(str)
    
    # Aplica a lógica de status combinada
    df["Status Exibição"] = df.apply(determinar_status, axis=1)
    
    # Define ocupação de vaga
    status_ocupantes = ["🟢 Matriculado", "🔵 Etapa 1 concluída", "🟡 Em processo"]
    df["Ocupa Vaga"] = df["Status Exibição"].isin(status_ocupantes)
    
    return df

def main():
    st.title("📊 DASHBOARD PROCESSOS SELETIVOS")
    st.markdown("---")

    arquivo = st.file_uploader("Carregue a planilha única (.xlsx)", type=["xlsx"])
    
    if arquivo:
        df_raw = pd.read_excel(arquivo)
        df_proc = processar_dados(df_raw)
        
        # --- TABELA DE RESUMO CONSOLIDADA (Todos os processos do mesmo curso) ---
        st.subheader("📋 Resumo Consolidado de Ocupação")
        cursos = sorted(df_proc["Curso"].unique())
        resumo_data = []

        for curso in cursos:
            df_c = df_proc[df_proc["Curso"] == curso]
            linha = {"Curso": curso}
            total_ocupado = 0
            for cota, limite in VAGAS_PADRAO.items():
                qtd = len(df_c[(df_c["Cota do candidato"] == cota) & (df_c["Ocupa Vaga"])])
                linha[cota] = f"{qtd}/{limite}"
                total_ocupado += qtd
            linha["Total"] = f"{total_ocupado}/{sum(VAGAS_PADRAO.values())}"
            resumo_data.append(linha)
        
        st.table(pd.DataFrame(resumo_data))
        st.markdown("---")

        # --- FILTROS DE SELEÇÃO ---
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            curso_sel = st.selectbox("🎯 Selecione um curso", ["-- Selecione --"] + cursos)
        
        if curso_sel != "-- Selecione --":
            df_curso = df_proc[df_proc["Curso"] == curso_sel]
            
            with col_f2:
                procs = sorted(df_curso["Processo seletivo"].unique().tolist())
                proc_sel = st.selectbox("📂 Processo Seletivo", ["Todos"] + procs)
            
            # Aplica filtro de processo seletivo se não for "Todos"
            if proc_sel == "Todos":
                df_final = df_curso.sort_values("Nota final", ascending=False)
            else:
                df_final = df_curso[df_curso["Processo seletivo"] == proc_sel].sort_values("Nota final", ascending=False)
            
            # --- INTERFACE DE RANKING ---
            abas_nomes = ["Ranking Geral", "Ampla Concorrência"] + list(VAGAS_PADRAO.keys())[1:]
            tabs = st.tabs(abas_nomes)
            
            cols_exibicao = ["Inscrição", "Nome", "Nota final", "Cota do candidato", "Processo seletivo", "Status Exibição"]

            with tabs[0]: # Ranking Geral
                st.subheader(f"Ranking Geral - {curso_sel} ({proc_sel})")
                st.dataframe(df_final[cols_exibicao], use_container_width=True, hide_index=True)

            with tabs[1]: # AC
                st.subheader("Classificação AC")
                df_ac = df_final[(df_final["Cota do candidato"] == "AC") | (~df_final["Ocupa Vaga"])]
                st.dataframe(df_ac[cols_exibicao], use_container_width=True, hide_index=True)

            for i, cota in enumerate(abas_nomes[2:], start=2):
                with tabs[i]:
                    st.subheader(f"Candidatos: {cota}")
                    df_cota = df_final[df_final["Cota do candidato"] == cota]
                    st.dataframe(df_cota[cols_exibicao], use_container_width=True, hide_index=True)
    else:
        st.info("👋 Por favor, carregue a planilha Excel para iniciar a análise.")

if __name__ == "__main__":
    main()
