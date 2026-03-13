import streamlit as st
import pandas as pd

st.set_page_config(page_title="DASHBOARD PROCESSOS SELETIVOS", layout="wide")

MAX_ROWS = None

MAPA_STATUS = {
    "Etapa 2 concluída": "🟢 Matriculado",
    "Etapa 1 concluída": "🔵 Etapa 1 concluída",
    "Desistiu da vaga": "🔴 Desistiu da vaga",
    "Matrícula cancelada": "🔴 Matrícula cancelada",
    "Indeferido": "🔴 Indeferido",
    "Não compareceu": "🔴 Não compareceu",
    "Enviou documentação": "🟡 Em processo",
    "Enviou recurso": "🟡 Em processo",
    "Enviar recurso": "🟡 Em processo",
    "Convocado": "🟡 Em processo",
    "Enviar substituição de documentos": "🟡 Em processo",
    "Aguardando vaga": "⚪ Aguardando vaga"
}

STATUS_ENCERRADO = [
    "🔴 Desistiu da vaga",
    "🔴 Matrícula cancelada",
    "🔴 Indeferido",
    "🔴 Não compareceu"
]

STATUS_OCUPA_VAGA = [
    "🟢 Matriculado",
    "🔵 Etapa 1 concluída"
]

COTAS = ["AC","LB_EP","LB_PCD","LB_PPI","LB_Q","LI_EP","LI_PCD","LI_PPI","LI_Q"]


def status_exibicao(row):
    s = str(row["Situação do requerimento de matrícula"]).strip()
    conv = row["Nº de convocações"]

    if s in MAPA_STATUS:
        return MAPA_STATUS[s]

    if pd.isna(row["Situação do requerimento de matrícula"]) or s.lower() in ["","nan"]:
        return "🔴 Não compareceu" if conv > 0 else "⚪ Lista de espera"

    return "⚪ Aguardando vaga"


def processar(df):

    df = df.copy()

    df["Curso"] = df["Curso"].fillna("").astype(str).str.strip()
    df["Processo seletivo"] = df["Processo seletivo"].fillna("").astype(str).str.strip()
    df["Cota do candidato"] = df["Cota do candidato"].fillna("AC").astype(str).str.strip()

    if "Cota da vaga garantida" not in df.columns:
        df["Cota da vaga garantida"] = ""

    df["Cota da vaga garantida"] = df["Cota da vaga garantida"].fillna("").astype(str).str.strip()

    df["Nota final"] = pd.to_numeric(df["Nota final"], errors="coerce").fillna(0)
    df["Nº de convocações"] = pd.to_numeric(df["Nº de convocações"], errors="coerce").fillna(0)

    df["Status"] = df.apply(status_exibicao, axis=1)

    df["Ocupa vaga"] = df["Status"].isin(STATUS_OCUPA_VAGA)

    df["Ranking geral"] = (
        df.groupby(["Curso","Processo seletivo"])["Nota final"]
        .rank(method="first", ascending=False)
    )

    df["Ranking cota"] = (
        df.groupby(["Curso","Processo seletivo","Cota do candidato"])["Nota final"]
        .rank(method="first", ascending=False)
    )

    return df


def centralizar(df):

    return (
        df.style
        .set_properties(**{"text-align":"center"})
        .set_table_styles(
            [
                {"selector":"th","props":[("text-align","center")]}
            ]
        )
    )


def centralizar_exceto_nome(df):

    sty = df.style.set_table_styles(
        [
            {"selector":"th","props":[("text-align","center")]}
        ]
    )

    for col in df.columns:
        if col == "Nome":
            sty = sty.set_properties(subset=[col], **{"text-align":"left"})
        else:
            sty = sty.set_properties(subset=[col], **{"text-align":"center"})

    return sty


def cor_saldo(val):

    if val > 0:
        return "color:green;font-weight:bold"
    if val < 0:
        return "color:red;font-weight:bold"
    return ""


def main():

    st.title("📊 DASHBOARD PROCESSOS SELETIVOS")

    arquivo = st.file_uploader(
        "Carregue a planilha (.xlsx) com as abas 'ranking' e 'vagas'",
        type=["xlsx"]
    )

    if not arquivo:
        return

    df_raw = pd.read_excel(arquivo, sheet_name="ranking")
    df_vagas = pd.read_excel(arquivo, sheet_name="vagas")

    df_vagas["Curso"] = df_vagas["Curso"].astype(str).str.strip()
    df_vagas["Processo seletivo"] = df_vagas["Processo seletivo"].astype(str).str.strip()

    df = processar(df_raw)

    cursos = sorted(df["Curso"].unique())

    with st.sidebar:

        curso_sel = st.selectbox(
            "Curso",
            ["-- Selecionar --"] + cursos
        )

    if curso_sel == "-- Selecionar --":

        st.subheader("RESUMO GERAL")

        resumo = (
            df.groupby("Curso")
            .agg(
                Matriculados=("Status", lambda x: (x=="🟢 Matriculado").sum()),
                Em_processo=("Status", lambda x: (x=="🟡 Em processo").sum())
            )
            .reset_index()
        )

        resumo.columns = ["Curso","Matriculados","Em processo"]

        st.dataframe(
            centralizar(resumo),
            use_container_width=True
        )

        return

    df_curso = df[df["Curso"]==curso_sel]

    processos = sorted(df_curso["Processo seletivo"].unique())

    with st.sidebar:

        proc_sel = st.selectbox(
            "Processo seletivo",
            ["Todos"] + processos
        )

        ocultar_encerrados = st.checkbox(
            "Ocultar candidatos com processo encerrado"
        )

    if ocultar_encerrados:
        df_vis = df[~df["Status"].isin(STATUS_ENCERRADO)]
    else:
        df_vis = df.copy()

    df_curso = df[df["Curso"]==curso_sel]
    df_curso_vis = df_vis[df_vis["Curso"]==curso_sel]

    if proc_sel != "Todos":
        df_curso = df_curso[df_curso["Processo seletivo"]==proc_sel]
        df_curso_vis = df_curso_vis[df_curso_vis["Processo seletivo"]==proc_sel]

    st.subheader(f"Ocupação de vagas — {curso_sel}")

    if proc_sel == "Todos":

        vagas = df_vagas[df_vagas["Curso"]==curso_sel][COTAS].sum()

    else:

        vagas = df_vagas[
            (df_vagas["Curso"]==curso_sel)
            & (df_vagas["Processo seletivo"]==proc_sel)
        ][COTAS].sum()

    ocupadas = []

    for c in COTAS:

        qtd = len(
            df_curso[
                (df_curso["Cota da vaga garantida"]==c)
                & (df_curso["Ocupa vaga"])
            ]
        )

        ocupadas.append(qtd)

    dist = pd.DataFrame({
        "Modalidade":COTAS,
        "Ocupadas":ocupadas,
        "Vagas":vagas.values
    })

    dist["Saldo"] = dist["Vagas"] - dist["Ocupadas"]

    st.subheader("Distribuição de vagas por modalidade")

    tabela_dist = centralizar(dist)
    tabela_dist = tabela_dist.applymap(cor_saldo, subset=["Saldo"])

    st.dataframe(
        tabela_dist,
        use_container_width=True
    )

    if proc_sel == "Todos":

        st.subheader("Lista de candidatos")

        st.write(
            "Lista de todos os candidatos de todos os processos seletivos neste curso. "
            "A listagem é apresentada em ordem alfabética e não representa classificação."
        )

        df_lista = df_curso_vis.sort_values("Nome")

        st.write(f"Exibindo {len(df_lista)} candidatos")

        cols = [
            "Inscrição",
            "Nome",
            "Nota final",
            "Cota do candidato",
            "Cota da vaga garantida",
            "Status"
        ]

        df_view = df_lista[cols].copy()

        df_view.columns = [
            "Inscrição",
            "Nome",
            "Nota final",
            "Cota do candidato",
            "Tipo de vaga utilizada",
            "Status"
        ]

        st.dataframe(
            centralizar_exceto_nome(df_view),
            use_container_width=True,
            hide_index=True
        )

        return

    abas = ["Lista de candidatos"] + COTAS

    tabs = st.tabs(abas)

    with tabs[0]:

        st.write(
            f"Lista de todos os candidatos do processo seletivo '{proc_sel}' "
            "neste curso, em ordem de classificação."
        )

        df_lista = df_curso_vis.sort_values("Ranking geral")

        st.write(f"Exibindo {len(df_lista)} candidatos")

        cols = [
            "Ranking geral",
            "Inscrição",
            "Nome",
            "Nota final",
            "Cota do candidato",
            "Cota da vaga garantida",
            "Status"
        ]

        df_view = df_lista[cols].copy()

        df_view.columns = [
            "Ranking geral",
            "Inscrição",
            "Nome",
            "Nota final",
            "Cota do candidato",
            "Tipo de vaga utilizada",
            "Status"
        ]

        st.dataframe(
            centralizar_exceto_nome(df_view),
            use_container_width=True,
            hide_index=True
        )

    for i,c in enumerate(COTAS, start=1):

        with tabs[i]:

            st.write(
                "Linhas em verde indicam candidatos que ocuparam vaga desta cota. "
                "Os demais matriculados entraram por sua própria nota ou outra modalidade."
            )

            df_cota = df_curso_vis[df_curso_vis["Cota do candidato"]==c]

            df_cota = df_cota.sort_values("Ranking cota")

            st.write(f"Candidatos nesta cota: {len(df_cota)}")

            cols = [
                "Ranking cota",
                "Inscrição",
                "Nome",
                "Nota final",
                "Cota do candidato",
                "Cota da vaga garantida",
                "Status"
            ]

            df_view = df_cota[cols].copy()

            df_view.columns = [
                "Ranking cota",
                "Inscrição",
                "Nome",
                "Nota final",
                "Cota do candidato",
                "Tipo de vaga utilizada",
                "Status"
            ]

            st.dataframe(
                centralizar_exceto_nome(df_view),
                use_container_width=True,
                hide_index=True
            )


if __name__ == "__main__":
    main()
