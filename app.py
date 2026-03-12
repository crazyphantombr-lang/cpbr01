# Versão: 1.3.0 (Principal)
import streamlit as st
import pandas as pd

# 1. Configurações de Página
st.set_page_config(page_title="DASHBOARD PROCESSOS SELETIVOS", layout="wide")

# 2. Mapeamento de Status
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
    if status_orig in MAPA_STATUS_FIXO:
        return MAPA_STATUS_FIXO[status_orig]
    if pd.isna(row["Situação do requerimento de matrícula"]) or status_orig.lower() in ['nan', '']:
        return "🔴 Não compareceu" if convocacoes > 0 else "⚪ Lista de espera"
    return "⚪ Aguardando vaga"

def processar_candidatos(df):
    df = df.copy()
    df["Nota final"] = pd.to_numeric(df["Nota final"], errors='coerce').fillna(0)
    df["Nº de convocações"] = pd.to_numeric(df["Nº de convocações"], errors='coerce').fillna(0)
    df["Curso"] = df["Curso"].fillna("Não Informado").astype(str).strip()
    df["Processo seletivo"] = df["Processo seletivo"].fillna("Geral").astype(str).strip()
    df["Status Exibição"] = df.apply(determinar_status, axis=1)
    status_ocupantes = ["🟢 Matriculado", "🔵 Etapa 1 concluída", "🟡 Em processo"]
    df["Ocupa Vaga"] = df["Status Exibição"].isin(status_ocupantes)
    return df

def main():
    st.title("📊 DASHBOARD PROCESSOS SELETIVOS")
    st.markdown("---")

    arquivo = st.file_uploader("Carregue a planilha (.xlsx) com as abas de candidatos e 'vagas'", type=["xlsx"])
    
    if arquivo:
        # Leitura das abas
        try:
            df_candidatos_raw = pd.read_excel(arquivo) # Assume primeira aba como candidatos
            df_vagas_raw = pd.read_excel(arquivo, sheet_name="vagas")
        except Exception as e:
            st.error(f"Erro ao ler as abas. Verifique se existe uma aba chamada 'vagas'. Erro: {e}")
            return

        df_candidatos = processar_candidatos(df_candidatos_raw)
        
        # --- FILTROS ---
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            cursos = sorted(df_candidatos["Curso"].unique())
            curso_sel = st.selectbox("🎯 Selecione um curso", ["-- Selecione --"] + cursos)
        
        if curso_sel != "-- Selecione --":
            df_curso_cand = df_candidatos[df_candidatos["Curso"] == curso_sel]
            
            with col_f2:
                procs = sorted(df_curso_cand["Processo seletivo"].unique().tolist())
                proc_sel = st.selectbox("📂 Processo Seletivo", ["Todos"] + procs)
            
            # --- LÓGICA DINÂMICA DE VAGAS (Aba 'vagas') ---
            colunas_cotas = ["AC", "LB_EP", "LB_PCD", "LB_PPI", "LB_Q", "LI_EP", "LI_PCD", "LI_PPI", "LI_Q"]
            
            # Filtra as vagas pactuadas
            if proc_sel == "Todos":
                vagas_pactuadas = df_vagas_raw[df_vagas_raw["Curso"] == curso_sel][colunas_cotas].sum().to_dict()
                df_final = df_curso_cand.sort_values("Nota final", ascending=False)
            else:
                vagas_pactuadas = df_vagas_raw[(df_vagas_raw["Curso"] == curso_sel) & 
                                               (df_vagas_raw["Processo seletivo"] == proc_sel)][colunas_cotas].sum().to_dict()
                df_final = df_curso_cand[df_curso_cand["Processo seletivo"] == proc_sel].sort_values("Nota final", ascending=False)

            # --- QUADRO RESUMO REATIVO ---
            st.subheader(f"📋 Resumo de Ocupação: {curso_sel} ({proc_sel})")
            resumo_list = []
            total_ocupado = 0
            total_vagas_pacto = sum(vagas_pactuadas.values())

            for cota in colunas_cotas:
                vaga_limite = int(vagas_pactuadas.get(cota, 0))
                qtd_real = len(df_final[(df_final["Cota do candidato"] == cota) & (df_final["Ocupa Vaga"])])
                resumo_list.append({"Cota": cota, "Ocupadas": qtd_real, "Total": vaga_limite, "Status": f"{qtd_real}/{vaga_limite}"})
                total_ocupado += qtd_real
            
            # Exibe resumo em colunas para economizar espaço
            st.dataframe(pd.DataFrame(resumo_list).set_index("Cota").T, use_container_width=True)
            st.info(f"**Total Geral do Filtro:** {total_ocupado} vagas ocupadas de {total_vagas_pacto} disponíveis.")

            # --- RANKING E ABAS ---
            st.markdown("---")
            abas_nomes = ["Ranking Geral", "Ampla Concorrência"] + colunas_cotas[1:]
            tabs = st.tabs(abas_nomes)
            cols_view = ["Inscrição", "Nome", "Nota final", "Cota do candidato", "Processo seletivo", "Status Exibição"]

            with tabs[0]:
                st.dataframe(df_final[cols_view], use_container_width=True, hide_index=True)

            for i, cota in enumerate(abas_nomes[1:], start=1):
                with tabs[i]:
                    filtro_cota = "AC" if i == 1 else abas_nomes[i]
                    df_cota = df_final[df_final["Cota do candidato"] == filtro_cota]
                    st.dataframe(df_cota[cols_view], use_container_width=True, hide_index=True)
    else:
        st.info("👋 Aguardando upload da planilha com as abas de candidatos e 'vagas'.")

if __name__ == "__main__":
    main()
