import streamlit as st
import pandas as pd
import re

VERSAO = "v5.1"

st.set_page_config(page_title="DASHBOARD PROCESSOS SELETIVOS", layout="wide")

st.markdown("""
<style>

.main {
background-color:#f8f9fa;
}

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

    if "Nome" in df.columns:
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


def render_lista(df,proc_sel):

    st.markdown("<h3 class='section-title'>Lista de candidatos</h3>",unsafe_allow_html=True)

    cols=[
        "Ranking geral",
        "Inscrição",
        "Nome",
        "Nota final",
        "Cota do candidato",
        "Cota da vaga garantida",
        "Status"
    ]

    cols_existentes=[c for c in cols if c in df.columns]

    df=df.copy()

    if "Cota da vaga garantida" in df.columns:
        df.rename(columns={
            "Cota da vaga garantida":"Vaga ocupada pelo candidato"
        },inplace=True)

        cols_existentes=[c if c!="Cota da vaga garantida" else "Vaga ocupada pelo candidato" for c in cols_existentes]

    if proc_sel=="Todos":

        st.info("Lista de todos os candidatos em ordem alfabética.")

        if "Ranking geral" in cols_existentes:
            cols_existentes.remove("Ranking geral")

        if "Nome" in df.columns:
            df=df.sort_values("Nome")

    else:

        st.info("Lista ordenada por classificação geral.")

        if "Ranking geral" in df.columns:
            df=df.sort_values("Ranking geral")

    st.dataframe(
        style_df(df[cols_existentes]),
        use_container_width=True,
        hide_index=True
    )


def main():

    st.title("Gestão de Processos Seletivos")

    st.caption(f"Versão do painel: {VERSAO}")

    with st.sidebar:

        st.header("Configurações")

        arquivo=st.file_uploader("Upload da planilha Excel",type=["xlsx"])

        busca_nome=st.text_input("Buscar candidato")

    if not arquivo:
        st.stop()

    df_raw=pd.read_excel(arquivo,sheet_name="ranking")
    df_vagas=pd.read_excel(arquivo,sheet_name="vagas")

    df,chamada_atual,chamada_fechada=processar(df_raw)

    if busca_nome:

        st.markdown("## Resultado da busca")

        df_busca=df[df["Nome"].str.contains(busca_nome,case=False,na=False)]

        render_lista(df_busca,"Busca")

        return

    cursos=sorted(df["Curso"].unique())

    with st.sidebar:

        curso_sel=st.selectbox(
            "Curso",
            ["-- Todos os Cursos --"]+cursos
        )

    if curso_sel=="-- Todos os Cursos --":

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
