import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

# =========================
# PROCESSAMENTO
# =========================
@st.cache_data
def processar(df):
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    # Ranking geral (base = AC)
    df["Ranking Geral"] = pd.to_numeric(df["Class ACP1"], errors="coerce")

    # Normalizações
    df["Situação"] = df["Situação"].astype(str).str.strip()
    df["Cota"] = df["Cota"].astype(str).str.strip()

    return df


@st.cache_data
def calcular_ultima_cota(df):
    resultado = {}

    grupos = df.groupby(["Processo seletivo", "Curso"])

    for (proc, curso), g in grupos:
        matriculados = g[g["Situação"] == "🟢 Matriculado"]

        for _, row in matriculados.iterrows():
            cota = row["Cota"]

            if cota == "AC":
                pos = row["Ranking Geral"]
            else:
                col_cota = f"Class {cota}"
                if col_cota in g.columns:
                    pos = row[col_cota]
                else:
                    continue

            key = (proc, curso, cota)

            if key not in resultado or pos > resultado[key]:
                resultado[key] = pos

    return resultado


# =========================
# HELPERS
# =========================
def get_rank_cota(row):
    cota = row["Cota"]

    if cota == "AC":
        return row["Ranking Geral"]

    col = f"Class {cota}"
    return row[col] if col in row else None


def format_pos(x):
    if pd.isna(x):
        return "-"
    return f"{int(x)}º"


# =========================
# TELA CANDIDATO
# =========================
def tela_candidato(df, ultima_cota):
    nome = st.text_input("Digite seu nome")

    if not nome:
        return

    df_filtrado = df[df["Nome"].str.contains(nome, case=False, na=False)]

    if df_filtrado.empty:
        st.warning("Nenhum candidato encontrado")
        return

    grupos = df_filtrado.groupby("Processo seletivo")

    for proc, g in grupos:
        st.markdown(f"## {proc}")

        for _, row in g.iterrows():
            curso = row["Curso"]
            cota = row["Cota"]
            situacao = row["Situação"]

            ranking_geral = row["Ranking Geral"]
            ranking_cota = get_rank_cota(row)

            key = (proc, curso, cota)
            ultima = ultima_cota.get(key)

            # distância
            distancia = None
            if ultima and ranking_cota:
                distancia = int(ranking_cota - ultima)

            # forma de ingresso
            forma = ""
            if situacao == "🟢 Matriculado":
                forma = row.get("Cota da vaga garantida", "-")

            st.markdown(f"""
### {curso}

**Situação:** {situacao}  
**Cota do candidato:** {cota}  

**Sua posição no Ranking Geral:** {format_pos(ranking_geral)}  
**Sua posição no Ranking da sua Cota:** {format_pos(ranking_cota)}  

**Último chamado na cota:** {format_pos(ultima)}  
{"**Você está " + str(distancia) + " posições atrás do último chamado**" if distancia and distancia > 0 else ""}

{"**Conseguiu a vaga através de:** " + forma if forma else ""}
            """)


# =========================
# TELA GESTOR
# =========================
def tela_gestor(df):
    st.markdown("## Visão Geral")

    resumo = (
        df.groupby(["Processo seletivo", "Curso", "Cota"])["Situação"]
        .value_counts()
        .unstack(fill_value=0)
        .reset_index()
    )

    st.dataframe(resumo, use_container_width=True)


# =========================
# MAIN
# =========================
def main():
    st.title("Processos Seletivos")

    modo = st.radio("Modo", ["Candidato", "Gestor"])

    arquivo = st.file_uploader("Envie a planilha")

    if not arquivo:
        return

    df_raw = pd.read_excel(arquivo, sheet_name="cronograma")

    df = processar(df_raw)
    ultima_cota = calcular_ultima_cota(df)

    if modo == "Candidato":
        tela_candidato(df, ultima_cota)
    else:
        tela_gestor(df)


if __name__ == "__main__":
    main()
