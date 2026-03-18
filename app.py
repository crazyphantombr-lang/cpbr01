import streamlit as st
import pandas as pd
import re

VERSAO = "6.0.0"

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
        in_start, _ = parse_dates(row.get('início'))
        prazo_start, prazo_end = parse_dates(row.get('prazo_candidato'))
        res_start, _ = parse_dates(row.get('resultado'))

        if in_start and now < in_start:
            return f"⏳ Aguardando: {sit}"

        if in_start and prazo_end and in_start <= now <= prazo_end:
            return f"🟢 {sit} (Prazo do candidato)"

        if prazo_end and res_start and prazo_end < now < res_start:
            return f"🟠 {sit} (Em análise interna)"

        if res_start and now < res_start:
            return f"🟡 Aguardando resultado: {sit}"

        final_date = res_start or prazo_end

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

@st.cache_data
def processar(df):
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

def interpretar_status(status):
    if "Matriculado" in status:
        return "Você já garantiu sua vaga."
    if "Convocado" in status:
        return "Você foi convocado. Verifique os prazos."
    if "Lista de espera" in status:
        return "Você ainda pode ser chamado."
    if "Não compareceu" in status:
        return "Você perdeu a chamada."
    return "Acompanhe o processo."

def tela_candidato(df):
    st.subheader("Consulta do candidato")
    nome = st.text_input("Digite seu nome")

    if nome:
        df_user = df[df["Nome"].str.contains(nome, case=False, na=False)]

        if df_user.empty:
            st.warning("Nenhum candidato encontrado")
        else:
            for _, row in df_user.iterrows():
                st.markdown(f"""
                ## 🎯 {row['Nome']}

                **{row['Status']}**

                {interpretar_status(row['Status'])}

                ---
                🎓 Curso: {row['Curso']}  
                🏆 Ranking: {int(row['Ranking']) if pd.notna(row['Ranking']) else '-'}  
                📊 Nota: {row['Nota final']}  
                📣 Chamada: {row['Chamada']}ª  
                """)

def kpis(df):
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Matriculados", (df["Status"] == "🟢 Matriculado").sum())
    col2.metric("Em processo", (df["Status"] == "🟡 Em processo").sum())
    col3.metric("Convocados", (df["Status"] == "🟡 Convocado").sum())
    col4.metric("Lista de espera", (df["Status"] == "⚪ Lista de espera").sum())

def tela_gestor(df, df_crono):
    st.subheader("Visão do gestor")

    kpis(df)

    resumo = df.groupby("Curso")["Status"].value_counts().unstack().fillna(0)
    st.bar_chart(resumo)

    with st.sidebar:
        curso = st.selectbox("Curso", ["Todos os cursos"] + sorted(df["Curso"].unique()))
        processo = st.selectbox("Processo seletivo", ["Todos"] + sorted(df["Processo seletivo"].unique()))
        cota = st.selectbox("Cota", ["Todas"] + COTAS)
        ocultar = st.toggle("Mostrar apenas candidatos ativos")

    df_view = df.copy()

    if curso != "Todos os cursos":
        df_view = df_view[df_view["Curso"] == curso]

    if processo != "Todos":
        df_view = df_view[df_view["Processo seletivo"] == processo]

    if cota != "Todas":
        df_view = df_view[df_view["Cota do candidato"] == cota]

    if ocultar:
        df_view = df_view[~df_view["Status"].isin(STATUS_ENCERRADO)]

    st.dataframe(df_view, use_container_width=True, hide_index=True)

    if df_crono is not None and not df_crono.empty:
        st.subheader("Situação dos processos")

        df_crono.columns = [c.lower().strip() for c in df_crono.columns]

        dados = []
        for (proc, chamada), group in df_crono.groupby(['processo','chamada']):
            fase = get_active_phase(group)
            dados.append({
                "Processo": proc,
                "Chamada": f"{chamada}ª",
                "Status": fase
            })

        st.dataframe(pd.DataFrame(dados), use_container_width=True, hide_index=True)

def main():
    st.title("Gestão de Processos Seletivos")
    st.caption(f"Versão {VERSAO}")

    modo = st.radio("Modo", ["👤 Candidato", "🧑‍💼 Gestor"], horizontal=True)

    arquivo = st.file_uploader("Carregar base (.xlsx)", type=["xlsx"])

    if not arquivo:
        return

    df_raw = pd.read_excel(arquivo, sheet_name="ranking")

    try:
        df_crono = pd.read_excel(arquivo, sheet_name="cronograma")
    except:
        df_crono = None

    df, chamada_atual, chamada_fechada = processar(df_raw)

    if modo == "👤 Candidato":
        tela_candidato(df)
    else:
        tela_gestor(df, df_crono)

if __name__ == "__main__":
    main()
