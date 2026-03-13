import streamlit as st
import pandas as pd

# Configuração da página para aproveitar o espaço horizontal
st.set_page_config(page_title="DASHBOARD PROCESSOS SELETIVOS", layout="wide")

# Estilização CSS Customizada para melhorar a UI
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stExpander"] {
        border: none !important;
        box-shadow: none !important;
    }
    </style>
    """, unsafe_loader=True)

# --- CONFIGURAÇÕES E MAPEAMENTOS ---
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

STATUS_ENCERRADO = ["🔴 Desistiu da vaga", "🔴 Matrícula cancelada", "🔴 Indeferido", "🔴 Não compareceu"]
STATUS_OCUPA_VAGA = ["🟢 Matriculado", "🔵 Etapa 1 concluída"]
COTAS = ["AC","LB_EP","LB_PCD","LB_PPI","LB_Q","LI_EP","LI_PCD","LI_PPI","LI_Q"]

# --- FUNÇÕES DE PROCESSAMENTO ---
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
    for col in ["Curso", "Processo seletivo", "Cota do candidato", "Cota da vaga garantida"]:
        if col in df.columns:
            df[col] = df[col].fillna("AC" if col == "Cota do candidato" else "").astype(str).str.strip()
    
    if "Cota da vaga garantida" not in df.columns:
        df["Cota da vaga garantida"] = ""

    df["Nota final"] = pd.to_numeric(df["Nota final"], errors="coerce").fillna(0)
    df["Nº de convocações"] = pd.to_numeric(df["Nº de convocações"], errors="coerce").fillna(0)
    df["Status"] = df.apply(status_exibicao, axis=1)
    df["Ocupa vaga"] = df["Status"].isin(STATUS_OCUPA_VAGA)

    # Rankings
    df["Ranking geral"] = df.groupby(["Curso","Processo seletivo"])["Nota final"].rank(method="first", ascending=False)
    df["Ranking cota"] = df.groupby(["Curso","Processo seletivo","Cota do candidato"])["Nota final"].rank(method="first", ascending=False)
    return df

# --- FUNÇÕES DE UI / ESTILO ---
def style_candidatos(df):
    def highlight_status(row):
        if row["Status"] == "🟢 Matriculado":
            return ['background-color: #e6ffed'] * len(row)
        if row["Status"] == "🟡 Em processo":
            return ['background-color: #fffbe6'] * len(row)
        if row["Status"] in STATUS_ENCERRADO:
            return ['background-color: #fff1f0'] * len(row)
        return [''] * len(row)
    
    return df.style.apply(highlight_status, axis=1).set_properties(**{"text-align": "center"}).set_properties(subset=["Nome"], **{"text-align": "left"})

# --- DASHBOARD PRINCIPAL ---
def main():
    st.markdown("# 📊 Dashboard de Processos Seletivos")
    
    arquivo = st.file_uploader("Arraste o arquivo .xlsx aqui", type=["xlsx"])
    if not arquivo:
        st.info("Aguardando upload da planilha para gerar os insights.")
        return

    # Leitura de dados
    df_raw = pd.read_excel(arquivo, sheet_name="ranking")
    df_vagas = pd.read_excel(arquivo, sheet_name="vagas")
    df = processar(df_raw)

    # Sidebar
    cursos = sorted(df["Curso"].unique())
    with st.sidebar:
        st.header("Filtros")
        curso_sel = st.selectbox("Selecione o Curso", ["-- Selecionar --"] + cursos)

    if curso_sel == "-- Selecionar --":
        render_resumo_geral(df)
    else:
        render_detalhe_curso(df, df_vagas, curso_sel)

def render_resumo_geral(df):
    st.subheader("Visão Geral de Todos os Cursos")
    resumo = df.groupby("Curso").agg(
        Matriculados=("Status", lambda x: (x=="🟢 Matriculado").sum()),
        Em_processo=("Status", lambda x: (x=="🟡 Em processo").sum())
    ).reset_index()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Matriculados", resumo["Matriculados"].sum())
    c2.metric("Total em Processo", resumo["Em_processo"].sum())
    c3.metric("Cursos Ativos", len(resumo))

    st.dataframe(resumo.style.background_gradient(cmap="Blues"), use_container_width=True, hide_index=True)

def render_detalhe_curso(df, df_vagas, curso_sel):
    df_curso = df[df["Curso"]==curso_sel]
    processos = sorted(df_curso["Processo seletivo"].unique())

    with st.sidebar:
        proc_sel = st.selectbox("Processo Seletivo", ["Todos"] + processos)
        ocultar_enc = st.checkbox("Ocultar Encerrados", value=False)

    # Filtro de exibição
    df_vis = df_curso[~df_curso["Status"].isin(STATUS_ENCERRADO)] if ocultar_enc else df_curso
    if proc_sel != "Todos":
        df_vis = df_vis[df_vis["Processo seletivo"]==proc_sel]
        df_vagas_filtradas = df_vagas[(df_vagas["Curso"]==curso_sel) & (df_vagas["Processo seletivo"]==proc_sel)]
    else:
        df_vagas_filtradas = df_vagas[df_vagas["Curso"]==curso_sel]

    # Cálculo de Vagas e Saldo
    vagas_totais = df_vagas_filtradas[COTAS].sum()
    ocupadas = {c: len(df_curso[(df_curso["Cota da vaga garantida"]==c) & (df_curso["Ocupa vaga"])]) for c in COTAS}
    
    # --- UI: KPI CARDS ---
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    total_v = vagas_totais.sum()
    total_o = sum(ocupadas.values())
    m1.metric("Vagas Ofertadas", total_v)
    m2.metric("Vagas Ocupadas", total_o)
    m3.metric("Vagas Restantes", total_v - total_o, delta_color="normal")
    m4.metric("% Ocupação", f"{(total_o/total_v*100):.1f}%" if total_v > 0 else "0%")

    # --- UI: PROGRESSO POR COTA ---
    st.subheader("Preenchimento por Modalidade")
    cols_cota = st.columns(3)
    for idx, c in enumerate(COTAS):
        with cols_cota[idx % 3]:
            v = vagas_totais[c]
            o = ocupadas[c]
            progresso = min(o/v, 1.0) if v > 0 else 0.0
            st.write(f"**{c}** ({o}/{v})")
            st.progress(progresso)

    # --- UI: TABELA DE CANDIDATOS ---
    st.subheader("Lista de Candidatos")
    cols_view = ["Ranking geral", "Inscrição", "Nome", "Nota final", "Cota do candidato", "Cota da vaga garantida", "Status"]
    df_final = df_vis.sort_values("Ranking geral")[cols_view]
    
    st.dataframe(style_candidatos(df_final), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
