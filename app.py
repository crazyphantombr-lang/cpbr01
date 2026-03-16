import streamlit as st
import pandas as pd
import re

VERSAO = "v5.6"

st.set_page_config(page_title="DASHBOARD PROCESSOS SELETIVOS", layout="wide")

st.markdown("""
<style>
.main {background-color:#f8f9fa;}
.section-title{
font-weight:700;
color:#1f77b4;
margin-top:20px;
}
</style>
""", unsafe_allow_html=True)


MAPA_STATUS = {
"Etapa 2 concluída":"🟢 Matriculado",
"Etapa 1 concluída":"🔵 Etapa 1 concluída",
"Desistiu da vaga":"🔴 Desistiu da vaga",
"Matrícula cancelada":"🔴 Matrícula cancelada",
"Indeferido":"🔴 Indeferido",
"Não compareceu":"🔴 Não compareceu",
"Enviou documentação":"🟡 Em processo",
"Enviou recurso":"🟡 Em processo",
"Enviar recurso":"🟡 Em processo",
"Convocado":"🟡 Em processo",
"Aguardando vaga":"🟡 Aguardando vaga"
}

STATUS_ENCERRADO=[
"🔴 Desistiu da vaga",
"🔴 Matrícula cancelada",
"🔴 Indeferido",
"🔴 Não compareceu"
]

COTAS=["AC","LB_EP","LB_PCD","LB_PPI","LB_Q","LI_EP","LI_PCD","LI_PPI","LI_Q"]


def extrair_chamada(txt):

    if pd.isna(txt):
        return 0

    nums=re.findall(r"(\d+)ª",str(txt))

    if not nums:
        return 0

    return max([int(n) for n in nums])


def detectar_chamada_atual(df):

    chamadas=df.groupby("Processo seletivo")["Chamada detectada"].max()

    return chamadas.to_dict()


def chamada_encerrada(df):

    res={}

    for proc,g in df.groupby("Processo seletivo"):

        atual=g["Chamada detectada"].max()

        enc=g[
            (g["Chamada detectada"]==atual) &
            (g["Situação do requerimento de matrícula"]=="Etapa 2 concluída")
        ]

        res[proc]=len(enc)>0

    return res


def status_exibicao(row,chamada_atual,chamada_fechada):

    s=str(row["Situação do requerimento de matrícula"]).strip()

    proc=row["Processo seletivo"]

    chamada=row["Chamada detectada"]

    if s in MAPA_STATUS:
        return MAPA_STATUS[s]

    if chamada==0:
        return "🟡 Aguardando vaga"

    atual=chamada_atual.get(proc,0)

    if chamada==atual:

        if chamada_fechada.get(proc,False):
            return "🔴 Não compareceu"

        return "🟡 Convocado"

    return "🔴 Não compareceu"


def processar(df):

    df=df.copy()

    for c in ["Curso","Processo seletivo","Cota do candidato","Cota da vaga garantida"]:
        if c in df.columns:
            df[c]=df[c].fillna("").astype(str).str.strip()

    df["Nota final"]=pd.to_numeric(df["Nota final"],errors="coerce").fillna(0)

    df["Ranking"]=pd.to_numeric(df["Class ACP1"],errors="coerce")

    df["Chamada detectada"]=df["Chamadas"].apply(extrair_chamada)

    chamada_atual=detectar_chamada_atual(df)

    chamada_fechada=chamada_encerrada(df)

    df["Status"]=df.apply(
        lambda r:status_exibicao(r,chamada_atual,chamada_fechada),axis=1
    )

    return df,chamada_atual,chamada_fechada


def style_df(df):

    def cor(row):

        if row["Status"]=="🟢 Matriculado":
            return ["background-color:#e6ffed"]*len(row)

        if row["Status"] in ["🟡 Em processo","🟡 Aguardando vaga"]:
            return ["background-color:#fffbe6"]*len(row)

        if row["Status"]=="🟡 Convocado":
            return ["background-color:#e6f7ff"]*len(row)

        if row["Status"] in STATUS_ENCERRADO:
            return ["background-color:#fff1f0"]*len(row)

        return [""]*len(row)

    sty=df.style.apply(cor,axis=1)

    sty=sty.set_properties(**{"text-align":"center"})

    if "Nome" in df.columns:
        sty=sty.set_properties(subset=["Nome"],**{"text-align":"left"})

    return sty


def resumo_geral(df):

    st.markdown("## 📊 Visão Geral")

    total=len(df)

    matriculados=len(df[df["Status"]=="🟢 Matriculado"])

    processo=len(df[df["Status"]=="🟡 Em processo"])

    aguardando=len(df[df["Status"]=="🟡 Aguardando vaga"])

    convocados=len(df[df["Status"]=="🟡 Convocado"])

    c1,c2,c3,c4,c5=st.columns(5)

    c1.metric("Candidatos",total)
    c2.metric("Matriculados",matriculados)
    c3.metric("Em processo",processo)
    c4.metric("Convocados",convocados)
    c5.metric("Aguardando vaga",aguardando)

    resumo=df.groupby("Curso").agg(
        candidatos=("Nome","count"),
        matriculados=("Status",lambda x:(x=="🟢 Matriculado").sum())
    ).reset_index()

    st.dataframe(resumo,use_container_width=True,hide_index=True)


def render_busca(df):

    st.markdown("## 🔎 Resultado da busca")

    df=df.rename(columns={
        "Processo seletivo":"Processo",
        "Nota final":"Nota",
        "Cota do candidato":"Cota",
        "Cota da vaga garantida":"Vaga ocupada"
    })

    cols=[
    "Processo",
    "Curso",
    "Nome",
    "Ranking",
    "Nota",
    "Cota",
    "Vaga ocupada",
    "Status"
    ]

    cols=[c for c in cols if c in df.columns]

    st.dataframe(style_df(df[cols]),use_container_width=True,hide_index=True)


def main():

    st.title("Gestão de Processos Seletivos")
    st.caption(f"Versão {VERSAO}")

    with st.sidebar:

        with st.expander("📂 Upload da planilha",expanded=True):

            arquivo=st.file_uploader("Carregar planilha Excel",type=["xlsx"])

        col1,col2=st.columns([3,1])

        busca_nome=col1.text_input("Buscar candidato")

        limpar=col2.button("Limpar")

        if limpar:
            busca_nome=""

    if not arquivo:
        st.stop()

    df_raw=pd.read_excel(arquivo,sheet_name="ranking")
    df_vagas=pd.read_excel(arquivo,sheet_name="vagas")

    df,chamada_atual,chamada_fechada=processar(df_raw)

    resumo_geral(df)

    if busca_nome:

        df_busca=df[df["Nome"].str.contains(busca_nome,case=False,na=False)]

        st.info(f"{len(df_busca)} candidatos encontrados")

        render_busca(df_busca)

        return

    cursos=sorted(df["Curso"].unique())

    with st.sidebar:

        curso_sel=st.selectbox(
            "Curso",
            ["-- Todos os Cursos --"]+cursos
        )

    if curso_sel=="-- Todos os Cursos --":
        return

    df=df[df["Curso"]==curso_sel]

    processos=sorted(df["Processo seletivo"].unique())

    with st.sidebar:

        proc_sel=st.selectbox(
            "Processo seletivo",
            ["Todos"]+processos
        )

        cota_sel=st.selectbox(
            "Cota",
            ["Todas"]+COTAS
        )

        ocultar=st.checkbox("Ocultar candidatos com processo encerrado")

    if proc_sel!="Todos":
        df=df[df["Processo seletivo"]==proc_sel]

    if ocultar:
        df=df[~df["Status"].isin(STATUS_ENCERRADO)]

    df=df.rename(columns={
        "Cota da vaga garantida":"Vaga ocupada"
    })

    if cota_sel!="Todas":

        st.info(f"Lista de candidatos da modalidade {cota_sel}, ordenados por ranking dentro da cota.")

        df_cota=df[df["Cota do candidato"]==cota_sel].copy()

        df_cota=df_cota.sort_values("Ranking")

        df_cota["Ranking Cota"]=range(1,len(df_cota)+1)

        cols=[
        "Ranking Cota",
        "Ranking",
        "Nome",
        "Nota final",
        "Status"
        ]

        cols=[c for c in cols if c in df_cota.columns]

        st.dataframe(
            style_df(df_cota[cols]),
            use_container_width=True,
            hide_index=True
        )

        return

    cols=[
    "Ranking",
    "Inscrição",
    "Nome",
    "Nota final",
    "Cota do candidato",
    "Vaga ocupada",
    "Status"
    ]

    cols=[c for c in cols if c in df.columns]

    if proc_sel=="Todos":

        if "Ranking" in cols:
            cols.remove("Ranking")

        df=df.sort_values("Nome")

    else:

        df=df.sort_values("Ranking")

    st.dataframe(
        style_df(df[cols]),
        use_container_width=True,
        hide_index=True
    )


if __name__=="__main__":
    main()
