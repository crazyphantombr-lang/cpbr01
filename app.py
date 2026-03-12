# Versão: 1.1.2 (Development)
import streamlit as st
import pandas as pd

# 1. Configurações da Página
st.set_page_config(page_title="Dashboard de Processo Seletivo", layout="wide")

# 2. Definição do Cenário de Vagas (Ajustado para 44 vagas)
VAGAS_PADRAO = {
    "AC": 22,
    "LI_EP": 8,
    "LB_EP": 5,
    "LI_PPI": 3,
    "LB_PPI": 3,
    "LI_PCD": 1,
    "LB_PCD": 1,
    "LB_Q": 1
}

def processar_ranqueamento(df, vagas_config):
    """
    Motor matemático com lógica de cotas, deslocamento e filtragem de status.
    """
    # Garante que a nota seja numérica e ordena
    df["Nota final"] = pd.to_numeric(df["Nota final"], errors='coerce').fillna(0)
    df = df.sort_values(by="Nota final", ascending=False).reset_index(drop=True)
    
    df["Status Final"] = "🟡 Lista de Espera"
    df["Ocupando Vaga De"] = "-"
    
    vagas_restantes = vagas_config.copy()
    
    # Passo 1: Ampla Concorrência (AC)
    for index, row in df.iterrows():
        status_req = str(row["Situação do requerimento de matrícula"]).upper()
        
        # Filtro de eliminados/desistentes
        if any(term in status_req for term in ["DESCLASSIFICADO", "DESISTENTE", "REPROVADO", "INDEFERIDO"]):
            df.at[index, "Status Final"] = f"🔴 {row['Situação do requerimento de matrícula']}"
            continue
            
        if vagas_restantes["AC"] > 0:
            df.at[index, "Status Final"] = "🟢 Aprovado - AC"
            df.at[index, "Ocupando Vaga De"] = "AC"
            vagas_restantes["AC"] -= 1

    # Passo 2: Cotas (Respeitando a nova nomenclatura com underline)
    for index, row in df.iterrows():
        if df.at[index, "Status Final"] != "🟡 Lista de Espera":
            continue
            
        cota_candidato = str(row["Cota do candidato"]).strip()
        
        if cota_candidato in vagas_restantes and vagas_restantes[cota_candidato] > 0:
            df.at[index, "Status Final"] = f"🔵 Aprovado - {cota_candidato}"
            df.at[index, "Ocupando Vaga De"] = cota_candidato
            vagas_restantes[cota_candidato] -= 1

    return df

def main():
    st.title("🏆 Dashboard de Resultados por Curso")
    st.markdown("---")

    arquivo_upado = st.file_uploader("Carregue sua planilha Excel (.xlsx)", type=["xlsx"])
    
    if arquivo_upado is not None:
        df_completo = pd.read_excel(arquivo_upado)
        
        # 3. Filtro de Cursos Dinâmico
        lista_cursos = sorted(df_completo["Curso"].unique().tolist())
        curso_selecionado = st.selectbox("🎯 Selecione o Curso para visualizar o ranking:", lista_cursos)
        
        # Filtra a base apenas para o curso escolhido
        df_curso = df_completo[df_completo["Curso"] == curso_selecionado].copy()
        
        # Processa o ranking para este curso específico
        df_resultado = processar_ranqueamento(df_curso, VAGAS_PADRAO)
        
        # 4. Painel de Indicadores (KPIs)
        total_vagas = sum(VAGAS_PADRAO.values())
        aprovados = len(df_resultado[df_resultado["Ocupando Vaga De"] != "-"])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Candidatos no Curso", len(df_resultado))
        col2.metric("Vagas Preenchidas", f"{aprovados} / {total_vagas}")
        col3.metric("Status do Curso", "Vagas Esgotadas" if aprovados >= total_vagas else "Vagas em Aberto")
        
        st.markdown("---")
        
        # 5. Navegação por Abas
        abas_nomes = ["Visão Geral", "Ampla Concorrência"] + [c for c in VAGAS_PADRAO.keys() if c != "AC"]
        tabs = st.tabs(abas_nomes)
        
        cols_view = ["Inscrição", "Nome", "Nota final", "Cota do candidato", "Situação do requerimento de matrícula", "Status Final"]

        with tabs[0]:
            st.subheader(f"Lista Geral - {curso_selecionado}")
            st.dataframe(df_resultado[cols_view], use_container_width=True, hide_index=True)

        with tabs[1]:
            st.subheader("Classificação Ampla Concorrência")
            df_ac = df_resultado[(df_resultado["Ocupando Vaga De"] == "AC") | (df_resultado["Status Final"] == "🟡 Lista de Espera")]
            st.dataframe(df_ac[cols_view], use_container_width=True, hide_index=True)

        for i, cota in enumerate(abas_nomes[2:], start=2):
            with tabs[i]:
                st.subheader(f"Candidatos da Cota: {cota}")
                df_cota = df_resultado[df_resultado["Cota do candidato"] == cota]
                st.dataframe(df_cota[cols_view], use_container_width=True, hide_index=True)
                
    else:
        st.info("💡 Aguardando upload da planilha Excel para iniciar o processamento.")

if __name__ == "__main__":
    main()
