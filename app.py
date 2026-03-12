# Versão: 2.1

import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="DASHBOARD PROCESSOS SELETIVOS", layout="wide")

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

    if pd.isna(row["Situação do requerimento de matrícula"]) or status_orig.lower() in ["nan", ""]:
        return "🔴 Não compareceu" if convocacoes > 0 else "⚪ Lista de espera"

    return "⚪ Aguardando vaga"


def processar_candidatos(df):

    df = df.copy()

    df["Curso"] = df["Curso"].fillna("Não Informado").astype(str).str.strip()
    df["Processo seletivo"] = df["Processo seletivo"].fillna("Geral").astype(str).str.strip()

    df["Cota do candidato"] = df["Cota do candidato"].fillna("AC").astype(str).str.strip()
    df["Cota da vaga garantida"] = df["Cota da vaga garantida"].fillna("AC").astype(str).str.strip()

    df["Nota final"] = pd.to_numeric(df["Nota final"], errors="coerce").fillna(0)
    df["Nº de convocações"] = pd.to_numeric(df["Nº de convocações"], errors="coerce").fillna(0)

    df["Status Exibição"] = df.apply(determinar_status, axis=1)

    status_ocupantes = [
        "🟢 Matriculado",
        "🔵 Etapa 1 concluída",
        "🟡 Em processo"
    ]

    df["Ocupa Vaga"] = df["Status Exibição"].isin(status_ocupantes)

    df = df.sort_values("Nota final", ascending=False)

    df["Ranking Geral"] = range(1, len(df) + 1)

    df["Ranking Cota"] = (
        df.groupby("Cota do candidato")["Nota final"]
        .rank(method="first", ascending=False)
        .astype(int)
    )

    return df


def color_vaga(row):

    status = row.get("Status Exibição", "")
    cota_vaga = row.get("Cota da vaga garantida", None)
    cota_candidato = row.get("Cota do candidato", None)

    # não destacar quem não ocupa vaga
    if "cancelada" in status.lower() or "compareceu" in status.lower():
        return [""] * len(row)

    if cota_vaga == "AC":
        return ["background-color:#dbeafe"] * len(row)

    if cota_candidato is not None and cota_vaga == cota_candidato:
        return ["background-color:#dcfce7"] * len(row)

    return [""] * len(row)


def main():

    st.title("📊 DASHBOARD PROCESSOS SELETIVOS")
    st.markdown("---")

    arquivo = st.file_uploader(
        "Carregue a planilha (.xlsx) com as abas 'ranking' e 'vagas'",
        type=["xlsx"]
    )

    if not arquivo:
        st.info("Aguardando upload da planilha.")
        return

    try:

        df_candidatos_raw = pd.read_excel(arquivo, sheet_name="ranking")
        df_vagas_raw = pd.read_excel(arquivo, sheet_name="vagas")

        df_vagas_raw["Curso"] = df_vagas_raw["Curso"].astype(str).str.strip()
        df_vagas_raw["Processo seletivo"] = df_vagas_raw["Processo seletivo"].astype(str).str.strip()

    except Exception as e:

        st.error(f"Erro ao ler planilha: {e}")
        return

    df_candidatos = processar_candidatos(df_candidatos_raw)

    with st.sidebar:

        st.header("Filtros")

        cursos = sorted(df_candidatos["Curso"].unique())

        curso_sel = st.selectbox(
            "Curso",
            ["-- Selecione --"] + cursos
        )

        if curso_sel != "-- Selecione --":

            df_curso = df_candidatos[df_candidatos["Curso"] == curso_sel]

            processos = sorted(df_curso["Processo seletivo"].unique())

            proc_sel = st.selectbox(
                "Processo seletivo",
                ["Todos"] + processos
            )

        else:

            proc_sel = None

    if curso_sel == "-- Selecione --":
        st.info("Selecione um curso.")
        return

    df_curso_cand = df_candidatos[df_candidatos["Curso"] == curso_sel]

    if proc_sel == "Todos":
        df_final = df_curso_cand
    else:
        df_final = df_curso_cand[df_curso_cand["Processo seletivo"] == proc_sel]

    df_final = df_final.sort_values("Nota final", ascending=False)

    df_final = df_final.reset_index(drop=True)

    df_final["Ranking Geral"] = df_final.index + 1

    df_final["Ranking Cota"] = (
    df_final.groupby("Cota do candidato")["Nota final"]
    .rank(method="first", ascending=False)
    .astype(int)
)

    colunas_cotas = [
        "AC","LB_EP","LB_PCD","LB_PPI","LB_Q",
        "LI_EP","LI_PCD","LI_PPI","LI_Q"
    ]

    if proc_sel == "Todos":

        vagas_pactuadas = df_vagas_raw[
            df_vagas_raw["Curso"] == curso_sel
        ][colunas_cotas].sum().to_dict()

    else:

        vagas_pactuadas = df_vagas_raw[
            (df_vagas_raw["Curso"] == curso_sel) &
            (df_vagas_raw["Processo seletivo"] == proc_sel)
        ][colunas_cotas].sum().to_dict()

    resumo_list = []

    total_ocupado = 0
    total_vagas = sum(vagas_pactuadas.values())

    for cota in colunas_cotas:

        vagas = int(vagas_pactuadas.get(cota, 0))

        ocupadas = len(
            df_final[
                (df_final["Cota da vaga garantida"] == cota) &
                (df_final["Ocupa Vaga"])
            ]
        )

        saldo = vagas - ocupadas

        resumo_list.append({
            "Cota": cota,
            "Ocupadas": ocupadas,
            "Vagas": vagas,
            "Saldo": saldo
        })

        total_ocupado += ocupadas

    df_resumo = pd.DataFrame(resumo_list)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total de vagas", total_vagas)

    with col2:
        st.metric("Vagas ocupadas", total_ocupado)

    with col3:
        st.metric("Saldo", total_vagas - total_ocupado)

    ocupacao = (total_ocupado / total_vagas) if total_vagas > 0 else 0

    st.progress(min(ocupacao, 1))

    if total_ocupado > total_vagas:
        st.warning(f"Excedente de {total_ocupado - total_vagas} matrículas.")

    st.markdown("---")

    st.subheader("Ocupação por cota")

    chart = alt.Chart(df_resumo).mark_bar().encode(
        x="Cota",
        y="Ocupadas",
        tooltip=["Cota", "Ocupadas", "Vagas"]
    )

    st.altair_chart(chart, use_container_width=True)

    st.subheader("Resumo de vagas")

    st.dataframe(
        df_resumo.set_index("Cota").T,
        use_container_width=True
    )

    st.markdown("---")

    abas = ["Ranking Geral"] + colunas_cotas

    tabs = st.tabs(abas)

    with tabs[0]:

        cols = [
            "Ranking Geral",
            "Inscrição",
            "Nome",
            "Nota final",
            "Cota da vaga garantida",
            "Status Exibição"
        ]

        st.dataframe(
            df_final[cols].style.apply(color_vaga, axis=1),
            use_container_width=True,
            hide_index=True
        )

    for i, cota in enumerate(colunas_cotas, start=1):

        with tabs[i]:

            df_cota = df_final[df_final["Cota do candidato"] == cota]

            cols = [
                "Ranking Cota",
                "Inscrição",
                "Nome",
                "Nota final",
                "Cota do candidato",
                "Cota da vaga garantida",
                "Status Exibição"
            ]

            st.dataframe(
                df_cota[cols].style.apply(color_vaga, axis=1),
                use_container_width=True,
                hide_index=True
            )


if __name__ == "__main__":
    main()
