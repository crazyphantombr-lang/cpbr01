import streamlit as st
import pandas as pd
import re

VERSAO = "6.2.0"

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

COTAS_MAP = {
    "AC": "Class ACP1",
    "LI_EP": "Class LI_EPP2",
    "LI_PCD": "Class LI_PCDP3",
    "LI_Q": "Class LI_QP4",
    "LI_PPI": "Class LI_PPIP5",
    "LB_EP": "Class LB_EPP6",
    "LB_PCD": "Class LB_PCDP7",
    "LB_Q": "Class LB_QP8",
    "LB_PPI": "Class LB_PPIP9"
}

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

def calcular_ranking_cota(row):
    cota = row["Cota do candidato"]
    col = COTAS_MAP.get(cota)
    if col and col in row:
        try:
            return int(row[col])
        except:
            return None
    return None

def ultima_posicao_cota(df):
    res = {}
    for (proc, curso, cota), g in df.groupby(["Processo seletivo","Curso","Cota do candidato"]):
        chamados = g[g["Status"].isin(["🟢 Matriculado","🟡 Convocado"])]
        if len(chamados) > 0:
            if cota == "AC":
                pos = chamados["Ranking Geral"].max()
            else:
                pos = chamados["Ranking_cota"].max()
        else:
            pos = 0
        res[(proc, curso, cota)] = pos
    return res

@st.cache_data
def processar(df):
    df = df.copy()

    df["Nota final"] = pd.to_numeric(df["Nota final"], errors="coerce").fillna(0)
    df["Ranking Geral"] = pd.to_numeric(df["Class ACP1"], errors="coerce")
    df["Chamada"] = df["Chamadas"].apply(extrair_chamada)

    df["Ranking_cota"] = df.apply(calcular_ranking_cota, axis=1)

    chamada_atual = detectar_chamada_atual(df)
    chamada_fechada = chamada_encerrada(df)

    df["Status"] = df.apply(lambda r: definir_status(r, chamada_atual, chamada_fechada), axis=1)

    ultima_cota = ultima_posicao_cota(df)

    return df, ultima_cota

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

def tela_candidato(df, ultima_cota):
    nome = st.text_input("Digite seu nome")

    if not nome:
        return

    df_user = df[df["Nome"].str.contains(nome, case=False, na=False)]

    if df_user.empty:
        st.warning("Nenhum candidato encontrado")
        return

    for nome, grupo in df_user.groupby("Nome"):
        st.markdown(f"# 🎯 {nome}")

        for proc, g in grupo.groupby("Processo seletivo"):
            st.markdown(f"## 📄 {proc}")

            for _, row in g.iterrows():
                key = (row["Processo seletivo"], row["Curso"], row["Cota do candidato"])
                ultima = ultima_cota.get(key, 0)

                col1, col2 = st.columns([2,1])

                with col1:
                    st.markdown(f"""
### 📌 Situação: **{row['Status']}**

{interpretar_status(row['Status'])}

**Curso:** {row['Curso']}
""")

                with col2:
                    forma = "-"
                    if row["Status"] not in STATUS_ENCERRADO:
                        forma = "Ampla concorrência" if row["Cota do candidato"] == "AC" else "Cota"

                    ultima_fmt = int(ultima) if pd.notna(ultima) and ultima != 0 else "-"

                    st.markdown(f"""
**Cota do candidato:** {row['Cota do candidato']}

**Conseguiu a vaga através de:** {forma}

**Sua posição no Ranking Geral:** {int(row['Ranking Geral']) if pd.notna(row['Ranking Geral']) else '-'}º

**Sua posição no Ranking da sua Cota:** {int(row['Ranking_cota']) if pd.notna(row['Ranking_cota']) else '-'}

**Último chamado na cota:** {ultima_fmt}
""")

                st.divider()

def resumo_geral(df):
    st.subheader("Visão geral por curso")

    resumo = df.groupby("Curso").agg(
        Matriculados=("Status", lambda x: (x == "🟢 Matriculado").sum()),
        Em_processo=("Status", lambda x: (x == "🟡 Em processo").sum()),
        Convocados=("Status", lambda x: (x == "🟡 Convocado").sum()),
        Lista_espera=("Status", lambda x: (x == "⚪ Lista de espera").sum()),
        Total=("Nome", "count")
    ).reset_index()

    st.dataframe(resumo, use_container_width=True, hide_index=True)

def tela_gestor(df):
    resumo_geral(df)

    st.subheader("Detalhamento")

    curso = st.selectbox("Curso", ["Todos"] + sorted(df["Curso"].unique()))
    processo = st.selectbox("Processo seletivo", ["Todos"] + sorted(df["Processo seletivo"].unique()))
    cota = st.selectbox("Cota", ["Todas"] + sorted(df["Cota do candidato"].unique()))
    ocultar = st.toggle("Mostrar apenas candidatos ativos")

    df_view = df.copy()

    if curso != "Todos":
        df_view = df_view[df_view["Curso"] == curso]

    if processo != "Todos":
        df_view = df_view[df_view["Processo seletivo"] == processo]

    if cota != "Todas":
        df_view = df_view[df_view["Cota do candidato"] == cota]

    if ocultar:
        df_view = df_view[~df_view["Status"].isin(STATUS_ENCERRADO)]

    cols = [
        "Nome","Curso","Processo seletivo",
        "Cota do candidato","Ranking Geral",
        "Ranking_cota","Status","Chamada"
    ]

    cols = [c for c in cols if c in df_view.columns]

    st.dataframe(df_view[cols], use_container_width=True, hide_index=True)

def main():
    st.title("Gestão de Processos Seletivos")
    st.caption(f"Versão {VERSAO}")

    modo = st.radio("Modo", ["👤 Candidato", "🧑‍💼 Gestor"], horizontal=True)

    arquivo = st.file_uploader("Carregar base (.xlsx)", type=["xlsx"])

    if not arquivo:
        return

    df_raw = pd.read_excel(arquivo, sheet_name="ranking")

    df, ultima_cota = processar(df_raw)

    if modo == "👤 Candidato":
        tela_candidato(df, ultima_cota)
    else:
        tela_gestor(df)

if __name__ == "__main__":
    main()
