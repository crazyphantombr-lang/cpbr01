import streamlit as st
import pandas as pd
import re

VERSAO = "5.11.1"

st.set_page_config(page_title="DASHBOARD PROCESSOS SELETIVOS", layout="wide")

MAPA_STATUS = {
    "Etapa 2 concluída":"🟢 Matriculado",
    "Etapa 1 concluída":"🟡 Em processo",
    "Desistiu da vaga":"🔴 Desistiu da vaga",
    "Matrícula cancelada":"🔴 Matrícula cancelada",
    "Indeferido":"🔴 Indeferido",
    "Não compareceu":"🔴 Não compareceu",
    "Enviou documentação":"🟡 Em processo",
    "Enviou recurso":"🟡 Em processo",
    "Enviar recurso":"🟡 Em processo",
    "Enviar substituição de documentos":"🟡 Em processo",
    "Aguardando vaga":"🟡 Aguardando vaga"
}

STATUS_ENCERRADO = [
    "🔴 Desistiu da vaga",
    "🔴 Matrícula cancelada",
    "🔴 Indeferido",
    "🔴 Não compareceu"
]

COTAS = ["AC","LB_EP","LB_PCD","LB_PPI","LB_Q","LI_EP","LI_PCD","LI_PPI","LI_Q"]

if "busca" not in st.session_state: st.session_state.busca = ""
if "curso" not in st.session_state: st.session_state.curso = "-- Todos os Cursos --"
if "processo" not in st.session_state: st.session_state.processo = "Todos"
if "cota" not in st.session_state: st.session_state.cota = "Todas"
if "ocultar" not in st.session_state: st.session_state.ocultar = False

def limpar_filtros():
    st.session_state.busca = ""
    st.session_state.curso = "-- Todos os Cursos --"
    st.session_state.processo = "Todos"
    st.session_state.cota = "Todas"
    st.session_state.ocultar = False

def parse_dates(text):
    if pd.isna(text): return None, None
    matches = re.findall(r"(\d{2}/\d{2}/\d{4}),\s*(\d{2})h:(\d{2})min", str(text))
    dates = []
    for m in matches:
        dt_str = f"{m[0]} {m[1]}:{m[2]}"
        try:
            dates.append(pd.to_datetime(dt_str, format="%d/%m/%Y %H:%M"))
        except:
            pass
    if len(dates) == 0: return None, None
    if len(dates) == 1: return dates[0], dates[0]
    return dates[0], dates[1]

def get_active_phase(df_group):
    now = pd.Timestamp.now()
    
    for _, row in df_group.iterrows():
        sit = str(row.get('situação', '')).strip()
        in_start, in_end = parse_dates(row.get('início'))
        fim_start, fim_end = parse_dates(row.get('fim'))
        res_start, _ = parse_dates(row.get('resultado'))

        if in_start and now < in_start:
            return f"⏳ Aguardando: {sit}"
        if in_start and in_end and in_start <= now <= in_end:
            return f"🟢 {sit} (Prazo Candidato)"
        if in_end and fim_start and in_end < now < fim_start:
            return f"🟡 Aguardando Análise: {sit}"
        if fim_start and fim_end and fim_start <= now <= fim_end:
            return f"🟠 {sit} (Em Análise Interna)"
        if fim_end and res_start and fim_end < now < res_start:
            return f"🟡 Aguardando Resultado: {sit}"
        
        final_date = res_start if res_start else (fim_end if fim_end else in_end)
        
        if final_date and now <= final_date:
            return f"🟡 Em andamento: {sit}"
        
    return "🔴 Processo Finalizado"

def extrair_chamada(txt):
    if pd.isna(txt): return 0
    nums = re.findall(r"(\d+)ª", str(txt))
    return max([int(n) for n in nums]) if nums else 0

def detectar_chamada_atual(df):
    return df.groupby("Processo seletivo")["Chamada"].max().to_dict()

def chamada_encerrada(df):
    res = {}
    for proc, g in df.groupby("Processo seletivo"):
        atual = g["Chamada"].max()
        enc = g[
            (g["Chamada"] == atual) &
            (g["Situação do requerimento de matrícula"] == "Etapa 2 concluída")
        ]
        res[proc] = len(enc) > 0
    return res

def definir_status(row, chamada_atual, chamada_fechada):
    s = str(row["Situação do requerimento de matrícula"]).strip()
    proc = row["Processo seletivo"]
    chamada = row["Chamada"]

    if s in MAPA_STATUS:
        return MAPA_STATUS[s]

    if chamada == 0:
        return "⚪ Lista de espera"

    atual = chamada_atual.get(proc, 0)

    if chamada == atual:
        if chamada_fechada.get(proc, False):
            return "🔴 Não compareceu"
        return "🟡 Convocado"

    if chamada < atual:
        return "🔴 Não compareceu"

    return "⚪ Lista de espera"

def processar(df):
    required = ["Nome","Curso","Processo seletivo","Class ACP1","Chamadas"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"Colunas ausentes: {missing}")
        st.stop()

    df = df.copy()

    for c in ["Curso", "Processo seletivo", "Cota do candidato", "Cota da vaga garantida"]:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str).str.strip()

    df["Nota final"] = pd.to_numeric(df["Nota final"], errors="coerce").fillna(0)
    df["Ranking"] = pd.to_numeric(df["Class ACP1"], errors="coerce")
    df["Chamada"] = df["Chamadas"].apply(extrair_chamada)

    chamada_atual = detectar_chamada_atual(df)
    chamada_fechada = chamada_encerrada(df)

    df["Status"] = df.apply(lambda r: definir_status(r, chamada_atual, chamada_fechada), axis=1)
    df = df.rename(columns={"Cota da vaga garantida": "Vaga ocupada"})

    return df, chamada_atual, chamada_fechada

def style_df(df):
    def cor(row):
        if row["Status"] == "🟢 Matriculado": return ["background-color:#e6ffed"] * len(row)
        if row["Status"] in ["🟡 Em processo","🟡 Aguardando vaga"]: return ["background-color:#fffbe6"] * len(row)
        if row["Status"] == "🟡 Convocado": return ["background-color:#e6f7ff"] * len(row)
        if row["Status"] in ["⚪ Lista de espera","⚪ Sem status"]: return ["background-color:#f5f5f5"] * len(row)
        if row["Status"] in STATUS_ENCERRADO: return ["background-color:#fff1f0"] * len(row)
        return [""] * len(row)

    sty = df.style.apply(cor, axis=1).set_properties(**{"text-align":"center"})
    if "Nome" in df.columns:
        sty = sty.set_properties(subset=["Nome"], **{"text-align":"left"})
    return sty

def resumo_geral(df, chamada_atual, chamada_fechada, df_crono):
    st.markdown("## 📊 Visão Geral Global")

    resumo = df.groupby("Curso").agg(
        Matriculados=("Status", lambda x: (x == "🟢 Matriculado").sum()),
        Em_processo=("Status", lambda x: (x == "🟡 Em processo").sum()),
        Convocados=("Status", lambda x: (x == "🟡 Convocado").sum()),
        Aguardando_vaga=("Status", lambda x: (x == "🟡 Aguardando vaga").sum()),
        Lista_de_espera=("Status", lambda x: (x == "⚪ Lista de espera").sum()),
        Candidatos=("Nome", "count")
    ).reset_index()

    resumo = resumo.rename(columns={
        "Em_processo":"Em processo",
        "Aguardando_vaga":"Aguardando vaga",
        "Lista_de_espera":"Lista de espera"
    })

    st.dataframe(resumo, use_container_width=True, hide_index=True)

    st.markdown("### 📋 Situação dos Processos Seletivos")

    if df_crono is not None and not df_crono.empty:
        df_crono_local = df_crono.copy()
        df_crono_local.columns = [c.lower().strip() for c in df_crono_local.columns]

        dados = []

        for (proc, chamada), group in df_crono_local.groupby(['processo','chamada']):
            fase = get_active_phase(group)
            dados.append({
                "Processo seletivo": str(proc).title(),
                "Chamada": f"{chamada}ª",
                "Status": fase
            })

        st.dataframe(pd.DataFrame(dados), use_container_width=True, hide_index=True)

def main():
    st.title("Gestão de Processos Seletivos")
    st.caption(f"Versão {VERSAO}")

    with st.sidebar:
        arquivo = st.file_uploader("Carregar base (.xlsx)", type=["xlsx"])

    if not arquivo:
        st.stop()

    df_raw = pd.read_excel(arquivo, sheet_name="ranking")
    df_vagas = pd.read_excel(arquivo, sheet_name="vagas")

    try:
        df_crono = pd.read_excel(arquivo, sheet_name="cronograma")
    except:
        df_crono = None

    df, chamada_atual, chamada_fechada = processar(df_raw)

    with st.sidebar:
        st.text_input("Buscar candidato", key="busca")

        cursos = ["-- Todos os Cursos --"] + sorted(df["Curso"].unique())
        st.selectbox("Curso", cursos, key="curso")

        if st.session_state.curso != "-- Todos os Cursos --":
            df_curso = df[df["Curso"] == st.session_state.curso]
            processos = ["Todos"] + sorted(df_curso["Processo seletivo"].unique())
            st.selectbox("Processo seletivo", processos, key="processo")
            st.selectbox("Cota", ["Todas"] + COTAS, key="cota")

    if st.session_state.busca:
        df_busca = df[df["Nome"].str.contains(st.session_state.busca, case=False, na=False)]
        st.dataframe(style_df(df_busca), use_container_width=True, hide_index=True)
        return

    if st.session_state.curso == "-- Todos os Cursos --":
        resumo_geral(df, chamada_atual, chamada_fechada, df_crono)
        return

    df_view = df[df["Curso"] == st.session_state.curso]

    if st.session_state.processo != "Todos":
        df_view = df_view[df_view["Processo seletivo"] == st.session_state.processo]

    if len(df_view) > 0:
        with st.sidebar:
            st.checkbox("Ocultar candidatos com processo encerrado", key="ocultar")

    if st.session_state.ocultar:
        df_view = df_view[~df_view["Status"].isin(STATUS_ENCERRADO)]

    cols = ["Ranking","Nome","Nota final","Chamada","Cota do candidato","Vaga ocupada","Status"]
    cols = [c for c in cols if c in df_view.columns]

    st.dataframe(style_df(df_view[cols]), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
