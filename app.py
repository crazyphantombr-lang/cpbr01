# ================================
# DASHBOARD PROCESSOS SELETIVOS
# Versão 2.0
# ================================

import streamlit as st
import pandas as pd

VERSAO_APP = "2.0"

st.set_page_config(page_title="DASHBOARD PROCESSOS SELETIVOS", layout="wide")

# ---------------- CSS ----------------
st.markdown("""
<style>
.main {
    background-color: #f8f9fa;
}
.section-title {
    color: #1f77b4;
    font-weight: 700;
    margin-top: 2rem;
}
thead tr th {
    text-align:center !important;
}
tbody tr td {
    text-align:center !important;
}
tbody tr td:nth-child(3) {
    text-align:left !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------- MAPAS ----------------

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

# ---------------- STATUS ----------------

def status_exibicao(row):

    s = str(row["Situação do requerimento de matrícula"]).strip()
    conv = row["Nº de convocações"]

    if s in MAPA_STATUS:
        return MAPA_STATUS[s]

    if pd.isna(row["Situação do requerimento de matrícula"]) or s.lower() in ["","nan"]:
        return "🔴 Não compareceu" if conv > 0 else "⚪ Lista de espera"

    return "⚪ Aguardando vaga"


# ---------------- PROCESSAMENTO ----------------

def processar(df):

    df = df.copy()

    for col in ["Curso","Processo seletivo","Cota do candidato"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    if "Cota da vaga garantida" not in df.columns:
        df["Cota da vaga garantida"] = ""

    df["Nota final"] = pd.to_numeric(df["Nota final"], errors="coerce").fillna(0)
    df["Nº de convocações"] = pd.to_numeric(df["Nº de convocações"], errors="coerce").fillna(0)

    df["Status"] = df.apply(status_exibicao, axis=1)

    df["Ocupa vaga"] = df["Status"].isin(STATUS_OCUPA_VAGA)

    # Ranking geral FIXO
    df["Ranking geral"] = (
        df.groupby(["Curso","Processo seletivo"])["Nota final"]
        .rank(method="first", ascending=False)
        .astype(int)
    )

    # Ranking da cota FIXO
    df["Ranking cota"] = (
        df.groupby(["Curso","Processo seletivo","Cota do candidato"])["Nota final"]
        .rank(method="first", ascending=False)
        .astype(int)
    )

    return df


# ---------------- ESTILO ----------------

def style_candidatos(df):

    def highlight(row):

        if row["Status"] == "🟢 Matriculado":
            return ["background-color:#e6ffed"] * len(row)

        if row["Status"] == "🟡 Em processo":
            return ["background-color:#fffbe6"] * len(row)

        if row["Status"] in STATUS_ENCERRADO:
            return ["background-color:#fff1f0"] * len(row)

        return [""] * len(row)

    return (
        df.style
        .apply(highlight, axis=1)
        .set_properties(**{"text-align":"center"})
        .set_properties(subset=["Nome"], **{"text-align":"left"})
    )


# ---------------- RESUMO ----------------

def render_resumo_geral(df):

    st.markdown("<h2 class='section-title'>Visão Consolidada</h2>", unsafe_allow_html=True)

    resumo = df.groupby("Curso").agg(
        Matriculados=("Status", lambda x: (x=="🟢 Matriculado").sum()),
        Em_processo=("Status", lambda x: (x=="🟡 Em processo").sum())
    ).reset_index()

    c1,c2,c3 = st.columns(3)

    c1.metric("Total de Matriculados", int(resumo["Matriculados"].sum()))
    c2.metric("Total em Processo", int(resumo["Em_processo"].sum()))
    c3.metric("Cursos Ativos", len(resumo))

    st.dataframe(
        resumo,
        use_container_width=True,
        hide_index=True
    )


# ---------------- OCUPAÇÃO ----------------

def render_ocupacao(df_vis, df_vagas, curso_sel, proc_sel):

    st.markdown("<h3 class='section-title'>Ocupação por Modalidade</h3>", unsafe_allow_html=True)

    if proc_sel == "Todos":
        vagas = df_vagas[df_vagas["Curso"]==curso_sel][COTAS].sum()
    else:
        vagas = df_vagas[
            (df_vagas["Curso"]==curso_sel) &
            (df_vagas["Processo seletivo"]==proc_sel)
        ][COTAS].sum()

    ocupadas = []

    for c in COTAS:
        qtd = len(
            df_vis[
                (df_vis["Cota da vaga garantida"]==c) &
                (df_vis["Ocupa vaga"])
            ]
        )
        ocupadas.append(qtd)

    df_dist = pd.DataFrame({
        "Modalidade":COTAS,
        "Vagas":vagas.values,
        "Ocupadas":ocupadas
    })

    df_dist["Saldo"] = df_dist["Vagas"] - df_dist["Ocupadas"]

    with st.expander("Ver detalhamento de vagas"):

        modo = st.radio(
            "Modo de visualização",
            ["Gráfico","Tabela"],
            horizontal=True
        )

        if modo == "Gráfico":

            cols = st.columns(3)

            for i,c in enumerate(COTAS):

                with cols[i%3]:

                    v = int(df_dist.loc[df_dist["Modalidade"]==c,"Vagas"])
                    o = int(df_dist.loc[df_dist["Modalidade"]==c,"Ocupadas"])

                    perc = o/v if v>0 else 0

                    st.write(f"**{c}**")
                    st.progress(min(perc,1.0), text=f"{o}/{v}")

        else:

            def cor_saldo(val):

                if val > 0:
                    return "color:green;font-weight:bold"

                if val < 0:
                    return "color:red;font-weight:bold"

                return ""

            st.dataframe(
                df_dist.style.applymap(cor_saldo, subset=["Saldo"]),
                use_container_width=True,
                hide_index=True
            )


# ---------------- LISTA ----------------

def render_lista(df_vis, proc_sel, cota_sel):

    st.markdown("<h3 class='section-title'>Lista de candidatos</h3>", unsafe_allow_html=True)

    busca = st.text_input("🔎 Buscar candidato")

    if busca:
        df_vis = df_vis[df_vis["Nome"].str.contains(busca, case=False, na=False)]

    st.write(f"Exibindo {len(df_vis)} candidatos")

    if proc_sel == "Todos":

        st.info(
            "Lista de todos os candidatos de todos os processos seletivos neste curso, em ordem alfabética."
        )

        df_vis = df_vis.sort_values("Nome")

        cols = [
            "Inscrição",
            "Nome",
            "Nota final",
            "Cota do candidato",
            "Cota da vaga garantida",
            "Status"
        ]

    else:

        st.info(
            f"Lista de todos os candidatos do processo seletivo '{proc_sel}' neste curso, em ordem de classificação."
        )

        if cota_sel == "Todas":
            df_vis = df_vis.sort_values("Ranking geral")
            cols = [
                "Ranking geral",
                "Inscrição",
                "Nome",
                "Nota final",
                "Cota do candidato",
                "Cota da vaga garantida",
                "Status"
            ]

        else:
            df_vis = df_vis.sort_values("Ranking cota")
            cols = [
                "Ranking cota",
                "Inscrição",
                "Nome",
                "Nota final",
                "Cota do candidato",
                "Cota da vaga garantida",
                "Status"
            ]

    df_view = df_vis[cols].copy()

    df_view.rename(
        columns={"Cota da vaga garantida":"Tipo de vaga utilizada"},
        inplace=True
    )

    st.dataframe(
        style_candidatos(df_view),
        use_container_width=True,
        hide_index=True
    )


# ---------------- DETALHE CURSO ----------------

def render_detalhe_curso(df, df_vagas, curso_sel):

    df_curso = df[df["Curso"]==curso_sel]

    processos = sorted(df_curso["Processo seletivo"].unique())

    with st.sidebar:

        proc_sel = st.selectbox("Processo seletivo", ["Todos"] + processos)

        if proc_sel != "Todos":
            cota_sel = st.selectbox("Filtro de cota", ["Todas"] + COTAS)
        else:
            cota_sel = "Todas"

        ocultar = st.checkbox("Ocultar candidatos com processo encerrado")

    df_vis = df_curso.copy()

    if ocultar:
        df_vis = df_vis[~df_vis["Status"].isin(STATUS_ENCERRADO)]

    if proc_sel != "Todos":
        df_vis = df_vis[df_vis["Processo seletivo"]==proc_sel]

    if cota_sel != "Todas":
        df_vis = df_vis[df_vis["Cota do candidato"]==cota_sel]

    st.divider()

    render_ocupacao(df_vis, df_vagas, curso_sel, proc_sel)

    render_lista(df_vis, proc_sel, cota_sel)


# ---------------- MAIN ----------------

def main():

    st.title("📊 Gestão de Processos Seletivos")
    st.caption(f"Versão {VERSAO_APP}")

    arquivo = st.file_uploader("Upload da planilha (.xlsx)", type=["xlsx"])

    if not arquivo:
        st.info("Carregue a planilha para iniciar o painel.")
        return

    try:

        df_raw = pd.read_excel(arquivo, sheet_name="ranking")
        df_vagas = pd.read_excel(arquivo, sheet_name="vagas")

        df = processar(df_raw)

        cursos = sorted(df["Curso"].unique())

        with st.sidebar:
            st.header("Filtros")
            curso_sel = st.selectbox(
                "Curso",
                ["-- Todos os Cursos --"] + cursos
            )

        if curso_sel == "-- Todos os Cursos --":

            render_resumo_geral(df)

        else:

            render_detalhe_curso(df, df_vagas, curso_sel)

    except Exception as e:

        st.error(
            f"Erro ao processar arquivo: {e}. Verifique se as abas 'ranking' e 'vagas' existem."
        )


if __name__ == "__main__":
    main()
