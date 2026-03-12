# Versão: 1.2.0 (Principal)
import streamlit as st
import pandas as pd

# 1. Configurações Iniciais e Estilo
st.set_page_config(page_title="DASHBOARD PROCESSOS SELETIVOS", layout="wide")

# Dicionário de Vagas (44 totais)
VAGAS_PADRAO = {
    "AC": 22, "LI_EP": 8, "LB_EP": 5, "LI_PPI": 3, "LB_PPI": 3, "LI_PCD": 1, "LB_PCD": 1, "LB_Q": 1
}

# 2. Mapeamento de Status (De-Para)
MAPA_STATUS = {
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

def tratar_status(status_original):
    status_str = str(status_original).strip()
    return MAPA_STATUS.get(status_str, "⚪ Aguardando vaga")

def processar_dados(df):
    """Aplica o mapeamento de status e calcula o preenchimento de vagas"""
    df = df.copy()
    # Limpeza e Tipagem
    df["Nota final"] = pd.to_numeric(df["Nota final"], errors='coerce').fillna(0)
    df["Curso"] = df["Curso"].fillna("Não Informado").astype(str)
    
    # Aplica o De-Para de Status
    df["Status Exibição"] = df["Situação do requerimento de matrícula"].apply(tratar_status)
    
    # Define quem ocupa vaga (Matriculados, Etapa 1 e Em Processo)
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
        
        # --- TABELA DE RESUMO POR CURSO ---
        st.subheader("📋 Resumo de Ocupação por Curso")
        cursos = sorted(df_proc["Curso"].unique())
        resumo_data = []

        for curso in cursos:
            df_c = df_proc[df_proc["Curso"] == curso]
            linha = {"Curso": curso}
            total_curso = 0
            for cota, limite in VAGAS_PADRAO.items():
                qtd_ocupada = len(df_c[(df_c["Cota do candidato"] == cota) & (df_proc["Ocupa Vaga"])])
                linha[cota] = f"{qtd_ocupada}/{limite}"
                total_curso += qtd_ocupada
            linha["Total"] = f"{total_curso}/{sum(VAGAS_PADRAO.values())}"
            resumo_data.append(linha)
        
        st.table(pd.DataFrame(resumo_data))
        st.markdown("---")

        # --- SELEÇÃO DE CURSO ---
        curso_sel = st.selectbox("🎯 Selecione um curso", ["-- Selecione --"] + cursos)

        if curso_sel != "-- Selecione --":
            df_final = df_proc[df_proc["Curso"] == curso_sel].sort_values("Nota final", ascending=False)
            
            # Abas conforme solicitado
            abas_nomes = ["Ranking Geral", "Ampla Concorrência"] + [c for c in VAGAS_PADRAO.keys() if c != "AC"]
            tabs = st.tabs(abas_nomes)
            
            cols = ["Inscrição", "Nome", "Nota final", "Cota do candidato", "Status Exibição"]

            with tabs[0]: # Ranking Geral
                st.subheader(f"Ranking Geral: {curso_sel}")
                st.dataframe(df_final[cols], use_container_width=True, hide_index=True)

            with tabs[1]: # AC
                st.subheader("Classificação Ampla Concorrência")
                df_ac = df_final[(df_final["Cota do candidato"] == "AC") | (df_final["Ocupa Vaga"] == False)]
                st.dataframe(df_ac[cols], use_container_width=True, hide_index=True)

            for i, cota in enumerate(abas_nomes[2:], start=2):
                with tabs[i]:
                    st.subheader(f"Candidatos: {cota}")
                    df_cota = df_final[df_final["Cota do candidato"] == cota]
                    st.dataframe(df_cota[cols], use_container_width=True, hide_index=True)
    else:
        st.info("👋 Bem-vindo! Por favor, carregue sua planilha Excel para visualizar o resumo dos processos.")

if __name__ == "__main__":
    main()
