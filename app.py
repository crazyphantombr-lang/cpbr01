import streamlit as st
import pandas as pd
import re

VERSAO = "6.3.0"

st.set_page_config(page_title="Processos Seletivos", layout="wide")

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
        chamados = g[g["Status"] == "🟢 Matriculado"]
        if len(chamados) > 0:
            if cota == "AC":
                pos = chamados["Ranking Geral"].max()
            else:
                pos = chamados["Ranking_cota"].max()
        else:
            pos = 0
        res[(proc, curso, cota)] = pos
    return res

def calcular_vagas(df_vagas):
    vagas = {}
    for _, row in df_vagas.iterrows():
        key = (row["Processo seletivo"], row["Curso"], row["Cota"])
        vagas[key] = row["Vagas"]
    return vagas

@st.cache_data
def processar(df, df_vagas):
    df = df.copy()

    df["Nota final"] = pd.to_numeric(df["Nota final"], errors="coerce").fillna(0)
    df["Ranking Geral"] = pd.to_numeric(df["Class ACP1"], errors="coerce")
    df["Chamada"] = df["Chamadas"].apply(extrair_chamada)

    df["Ranking_cota"] = df.apply(calcular_ranking_cota, axis=1)

    chamada_atual = detectar_chamada_atual(df)
    chamada_fechada = chamada_encerrada(df)

    df["Status"] = df.apply(lambda r: definir_status(r, chamada_atual, chamada_fechada), axis=1)

    vagas = calcular_vagas(df_vagas)
    ultima_cota = ultima_posicao_cota(df)

    return df, vagas, ultima_cota

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

def tela_candidato(df, vagas, ultima_cota):
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

                total_vagas = vagas.get(key, 0)
                ocupadas = len(df[
                    (df["Processo seletivo"] == row["Processo seletivo"]) &
                    (df["Curso"] == row["Curso"]) &
                    (df["Cota do candidato"] == row["Cota do candidato"]) &
                    (df["Status"] == "🟢 Matriculado")
                ])

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
                    if row["Status"] == "🟢 Matriculado":
                        forma = row.get("Vaga ocupada", "-")

                    ultima_fmt = f"{int(ultima)}º" if pd.notna(ultima) and ultima != 0 else "-"
                    ranking_geral = f"{int(row['Ranking Geral'])}º" if pd.notna(row['Ranking Geral']) else "-"
                    ranking_cota = (
                        f"{int(row['Ranking Geral'])}º" if row["Cota do candidato"] == "AC"
                        else f"{int(row['Ranking_cota'])}º" if pd.notna(row["Ranking_cota"]) else "-"
                    )

                    st.markdown(f"""
**Cota do candidato:** {row['Cota do candidato']}

**Conseguiu a vaga através de:** {forma}

**Sua posição no Ranking Geral:** {ranking_geral}

**Sua posição no Ranking da sua Cota:** {ranking_cota}

**Último chamado na cota:** {ultima_fmt}

**Vagas na sua cota:** {total_vagas}

**Vagas ocupadas:** {ocupadas}
""")

                st.divider()

def resumo_geral(df):
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
    modo = st.radio("", ["👤 Candidato", "🧑‍💼 Gestor"], horizontal=True)

    arquivo = st.file_uploader("Carregar base (.xlsx)", type=["xlsx"])

    if not arquivo:
        return

    df_raw = pd.read_excel(arquivo, sheet_name="ranking")
    df_vagas = pd.read_excel(arquivo, sheet_name="vagas")

    df, vagas, ultima_cota = processar(df_raw, df_vagas)

    if modo == "👤 Candidato":
        tela_candidato(df, vagas, ultima_cota)
    else:
        tela_gestor(df)

if __name__ == "__main__":
    main()
