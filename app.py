# Versão 3.0

import streamlit as st
import pandas as pd

st.set_page_config(page_title="DASHBOARD PROCESSOS SELETIVOS", layout="wide")

MAPA_STATUS_FIXO = {
    "Etapa 2 concluída": "🟢 Matriculado",
    "Etapa 1 concluída": "🔵 Etapa 1 concluída",
    "Desistiu da vaga": "🔴 Desistiu da vaga",
    "Matrícula cancelada": "🔴 Matrícula cancelada",
    "Indeferido": "🔴 Indeferido",
    "Não compareceu": "🔴 Não compareceu",
    "Enviou documentação": "🟡 Em processo",
    "Enviou recurso": "🟡 Em processo",
    "Enviar recurso": "🟡 Em processo",
    "Enviar substituição de documentos": "🟡 Em processo",
    "Convocado": "🟡 Em processo",
    "Aguardando vaga": "⚪ Aguardando vaga"
}

def determinar_status(row):

    status_orig = str(row["Situação do requerimento de matrícula"]).strip()
    convocacoes = row["Nº de convocações"]

    if status_orig in MAPA_STATUS_FIXO:
        return MAPA_STATUS_FIXO[status_orig]

    if pd.isna(row["Situação do requerimento de matrícula"]) or status_orig.lower() in ["nan",""]:
        return "🔴 Não compareceu" if convocacoes > 0 else "⚪ Lista de espera"

    return "⚪ Aguardando vaga"


def processar_candidatos(df):

    df = df.copy()

    df["Curso"] = df["Curso"].fillna("Não Informado").astype(str).str.strip()
    df["Processo seletivo"] = df["Processo seletivo"].fillna("Geral").astype(str).str.strip()

    df["Cota do candidato"] = df["Cota do candidato"].fillna("AC").astype(str).str.strip()

    df["Cota da vaga garantida"] = df["Cota da vaga garantida"].astype(str).str.strip()
    df.loc[df["Cota da vaga garantida"].isin(["", "nan"]), "Cota da vaga garantida"] = ""

    df["Nota final"] = pd.to_numeric(df["Nota final"], errors="coerce").fillna(0)
    df["Nº de convocações"] = pd.to_numeric(df["Nº de convocações"], errors="coerce").fillna(0)

    df["Status Exibição"] = df.apply(determinar_status, axis=1)

    df["Ocupa Vaga"] = df["Status Exibição"] == "🟢 Matriculado"
    df["Em Processo"] = df["Status Exibição"] == "🟡 Em processo"

    return df


def color_vaga(row):

    status = row.get("Status Exibição", "")
    cota_vaga = row.get("Cota da vaga garantida", None)
    cota_candidato = row.get("Cota do candidato", None)

    if "cancelada" in status.lower() or "compareceu" in status.lower():
        return [""] * len(row)

    if status == "🟢 Matriculado" and cota_vaga == cota_candidato and cota_vaga != "":
        return ["background-color:#dcfce7"] * len(row)

    return [""] * len(row)


def centralizar_tabela(df, coluna_nome="Nome"):

    estilos = []
    for col in df.columns:
        if col == coluna_nome:
            estilos.append({"selector": f"th.col_heading.level0.col{df.columns.get_loc(col)}",
                            "props": [("text-align", "left")]})
        else:
            estilos.append({"selector": f"th.col_heading.level0.col{df.columns.get_loc(col)}",
                            "props": [("text-align", "center")]})
    return df


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

    st.subheader("Resumo geral")

    total_matriculados = (df_candidatos["Status Exibição"] == "🟢 Matriculado").sum()
    total_processo = (df_candidatos["Status Exibição"] == "🟡 Em processo").sum()

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Matriculados", total_matriculados)

    with col2:
        st.metric("Em processo", total_processo)

    resumo_cursos = (
        df_candidatos
        .groupby("Curso")
        .agg(
            Matriculados=("Status Exibição", lambda x: (x == "🟢 Matriculado").sum()),
            Em_Processo=("Status Exibição", lambda x: (x == "🟡 Em processo").sum())
        )
        .reset_index()
    )

    st.dataframe(resumo_cursos, use_container_width=True)

    st.markdown("---")

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
        return

    df_curso_cand = df_candidatos[df_candidatos["Curso"] == curso_sel]

    if proc_sel == "Todos":
        df_final = df_curso_cand.sort_values("Nome")
    else:
        df_final = df_curso_cand[df_curso_cand["Processo seletivo"] == proc_sel] \
            .sort_values("Nota final", ascending=False)

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
            "Modalidade": cota,
            "Ocupadas": ocupadas,
            "Vagas": vagas,
            "Saldo": saldo
        })

        total_ocupado += ocupadas

    df_resumo = pd.DataFrame(resumo_list)

    st.subheader(f"Ocupação de vagas — {curso_sel}")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total de vagas", total_vagas)

    with col2:
        st.metric("Matriculados", total_ocupado)

    with col3:
        st.metric("Saldo", total_vagas - total_ocupado)

    if total_ocupado > total_vagas:
        st.warning(f"Excedente de {total_ocupado - total_vagas} matrículas.")

    st.subheader("Distribuição de vagas por modalidade")

    st.dataframe(
        df_resumo.set_index("Modalidade").T,
        use_container_width=True
    )

    st.markdown("---")

    abas = ["Lista de candidatos"] + colunas_cotas
    tabs = st.tabs(abas)

    with tabs[0]:

        if proc_sel == "Todos":

            st.info(
                "Lista de todos os candidatos de todos os processos seletivos neste curso. "
                "A listagem é apresentada em ordem alfabética e não representa classificação."
            )

            cols = [
                "Inscrição",
                "Nome",
                "Processo seletivo",
                "Nota final",
                "Cota da vaga garantida",
                "Status Exibição"
            ]

        else:

            st.info(
                f"Lista de todos os candidatos do processo seletivo '{proc_sel}' neste curso, "
                "em ordem de classificação."
            )

            cols = [
                "Ranking Geral",
                "Inscrição",
                "Nome",
                "Nota final",
                "Cota da vaga garantida",
                "Status Exibição"
            ]

        df_show = df_final[cols].rename(
            columns={"Cota da vaga garantida": "Tipo de vaga utilizada"}
        )

        st.dataframe(
            df_show.style.apply(color_vaga, axis=1),
            use_container_width=True,
            hide_index=True
        )

    for i, cota in enumerate(colunas_cotas, start=1):

        with tabs[i]:

            st.info(
                "Linhas em verde indicam candidatos que ocuparam vaga desta cota. "
                "Os demais matriculados entraram por sua própria nota "
                "(ampla concorrência) ou por outra modalidade de cota."
            )

            df_cota = df_final[df_final["Cota do candidato"] == cota]

            if proc_sel == "Todos":

                cols = [
                    "Inscrição",
                    "Nome",
                    "Nota final",
                    "Cota do candidato",
                    "Cota da vaga garantida",
                    "Status Exibição"
                ]

            else:

                cols = [
                    "Ranking Cota",
                    "Inscrição",
                    "Nome",
                    "Nota final",
                    "Cota do candidato",
                    "Cota da vaga garantida",
                    "Status Exibição"
                ]

            df_show = df_cota[cols].rename(
                columns={"Cota da vaga garantida": "Tipo de vaga utilizada"}
            )

            st.dataframe(
                df_show.style.apply(color_vaga, axis=1),
                use_container_width=True,
                hide_index=True
            )


if __name__ == "__main__":
    main()
