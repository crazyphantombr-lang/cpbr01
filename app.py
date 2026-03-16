import streamlit as st
import pandas as pd
import re

VERSAO = "v5.0"

st.set_page_config(page_title="DASHBOARD PROCESSOS SELETIVOS", layout="wide")

st.markdown("""
<style>
.main {background-color:#f8f9fa;}

.section-title{
font-weight:700;
color:#1f77b4;
margin-top:20px;
}

.center-table td, .center-table th{
text-align:center !important;
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
"Enviar substituição de documentos":"🟡 Em processo",
"Aguardando vaga":"⚪ Aguardando vaga"
}

STATUS_ENCERRADO=[
"🔴 Desistiu da vaga",
"🔴 Matrícula cancelada",
"🔴 Indeferido",
"🔴 Não compareceu"
]

STATUS_OCUPA_VAGA=[
"🟢 Matriculado",
"🔵 Etapa 1 concluída"
]

COTAS=[
"AC","LB_EP","LB_PCD","LB_PPI","LB_Q","LI_EP","LI_PCD","LI_PPI","LI_Q"
]


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

        enc=(g[
            (g["Chamada detectada"]==atual) &
            (g["Situação do requerimento de matrícula"]=="Etapa 2 concluída")
        ])

        res[proc]=len(enc)>0

    return res


def status_exibicao(row,chamada_atual,chamada_fechada):

    s=str(row["Situação do requerimento de matrícula"]).strip()

    proc=row["Processo seletivo"]

    chamada=row["Chamada detectada"]

    if s in MAPA_STATUS:
        return MAPA_STATUS[s]

    if chamada==0:
        return "⚪ Lista de espera"

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

    df["Chamada detectada"]=df["Chamadas"].apply(extrair_chamada)

    chamada_atual=detectar_chamada_atual(df)

    chamada_fechada=chamada_encerrada(df)

    df["Status"]=df.apply(
        lambda r:status_exibicao(r,chamada_atual,chamada_fechada),axis=1
    )

    df["Ocupa vaga"]=df["Status"].isin(STATUS_OCUPA_VAGA)

    df["Ranking geral"]=df.groupby(
        ["Curso","Processo seletivo"]
    )["Nota final"].rank(
        method="first",ascending=False
    ).astype(int)

    return df,chamada_atual,chamada_fechada


def style_df(df):

    def cor(row):

        if row["Status"]=="🟢 Matriculado":
            return ["background-color:#e6ffed"]*len(row)

        if row["Status"]=="🟡 Em processo":
            return ["background-color:#fffbe6"]*len(row)

        if row["Status"]=="🟡 Convocado":
            return ["background-color:#e6f7ff"]*len(row)

        if row["Status"] in STATUS_ENCERRADO:
            return ["background-color:#fff1f0"]*len(row)

        return [""]*len(row)

    sty=df.style.apply(cor,axis=1)

    sty=sty.set_properties(**{"text-align":"center"})

    sty=sty.set_properties(subset=["Nome"],**{"text-align":"left"})

    return sty


def resumo_chamadas(df,chamada_atual,chamada_fechada):

    st.markdown("### Situação das chamadas")

    dados=[]

    for proc in sorted(df["Processo seletivo"].unique()):

        atual=chamada_atual.get(proc,0)

        sit="🟢 Encerrada" if chamada_fechada.get(proc) else "🟡 Em andamento"

        dados.append({
            "Processo seletivo":proc,
            "Chamada atual":f"{atual}ª",
            "Situação":sit
        })

    tabela=pd.DataFrame(dados)

    st.dataframe(tabela,use_container_width=True,hide_index=True)


def render_resumo(df):

    st.markdown("<h2 class='section-title'>Resumo Geral</h2>",unsafe_allow_html=True)

    resumo=df.groupby("Curso").agg(
        Matriculados=("Status",lambda x:(x=="🟢 Matriculado").sum()),
        Em_processo=("Status",lambda x:(x=="🟡 Em processo").sum())
    ).reset_index()

    st.dataframe(resumo,use_container_width=True,hide_index=True)


def render_lista(df,proc_sel):

    st.markdown("<h3 class='section-title'>Lista de candidatos</h3>",unsafe_allow_html=True)

    busca=st.text_input("Buscar candidato")

    if busca:
        df=df[df["Nome"].str.contains(busca,case=False,na=False)]

    cols=[
        "Ranking geral",
        "Inscrição",
        "Nome",
        "Nota final",
        "Cota do candidato",
        "Cota da vaga garantida",
        "Status"
    ]

    df=df.copy()

    df.rename(columns={
        "Cota da vaga garantida":"Vaga ocupada pelo candidato"
    },inplace=True)

    if proc_sel=="Todos":

        st.info("Lista de todos os candidatos em ordem alfabética.")

        df=df.sort_values("Nome")

        cols.remove("Ranking geral")

    else:

        st.info("Lista ordenada por classificação geral.")

        df=df.sort_values("Ranking geral")

    st.dataframe(
        style_df(df[cols]),
        use_container_width=True,
        hide_index=True
    )


def main():

    st.title("Gestão de Processos Seletivos")

    st.caption(f"Versão do painel: {VERSAO}")

    arquivo=st.file_uploader("Upload da planilha Excel",type=["xlsx"])

    if not arquivo:
        st.stop()

    df_raw=pd.read_excel(arquivo,sheet_name="ranking")

    df_vagas=pd.read_excel(arquivo,sheet_name="vagas")

    df,chamada_atual,chamada_fechada=processar(df_raw)

    cursos=sorted(df["Curso"].unique())

    with st.sidebar:

        st.header("Filtros")

        curso_sel=st.selectbox(
            "Curso",
            ["-- Todos os Cursos --"]+cursos
        )

    if curso_sel=="-- Todos os Cursos --":

        render_resumo(df)

        resumo_chamadas(df,chamada_atual,chamada_fechada)

        return

    df=df[df["Curso"]==curso_sel]

    processos=sorted(df["Processo seletivo"].unique())

    with st.sidebar:

        proc_sel=st.selectbox(
            "Processo seletivo",
            ["Todos"]+processos
        )

        ocultar=st.checkbox("Ocultar candidatos com processo encerrado")

    if proc_sel!="Todos":

        df=df[df["Processo seletivo"]==proc_sel]

    if ocultar:

        df=df[~df["Status"].isin(STATUS_ENCERRADO)]

    resumo_chamadas(df,chamada_atual,chamada_fechada)

    render_lista(df,proc_sel)


if __name__=="__main__":
    main()
