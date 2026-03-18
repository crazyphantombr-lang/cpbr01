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

    # normalizações
    df["Ranking Geral"] = pd.to_numeric(df["Class ACP1"], errors="coerce")

    # ranking por cota (dinâmico)
    def get_ranking_cota(row):
        cota = row["Cota do candidato"]
        mapa = {
            "AC": "Class ACP1",
            "LB_PPI": "Class LB_PPIP9",
            "LB_Q": "Class LB_QP8",
            "LB_PCD": "Class LB_PCDP7",
            "LB_EP": "Class LB_EPP6",
            "LI_PPI": "Class LI_PPIP5",
            "LI_Q": "Class LI_QP4",
            "LI_PCD": "Class LI_PCDP3",
            "LI_EP": "Class LI_EPP2",
        }
        col = mapa.get(cota)
        if col in df.columns:
            return pd.to_numeric(row[col], errors="coerce")
        return None

    df["Ranking_cota"] = df.apply(get_ranking_cota, axis=1)

    return df


@st.cache_data
def calcular_ultima_cota(df):
    res = {}

    for (proc, curso, cota), g in df.groupby(["Processo seletivo", "Curso", "Cota do candidato"]):
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


@st.cache_data
def calcular_vagas(df):
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    cotas = ["AC","LB_PPI","LB_Q","LB_PCD","LB_EP","LI_PPI","LI_PCD","LI_EP","LI_Q"]

    vagas = {}

    for _, row in df.iterrows():
        proc = row["Processo seletivo"]
        curso = row["Curso"]

        for cota in cotas:
            if cota in df.columns:
                valor = pd.to_numeric(row[cota], errors="coerce")
                vagas[(proc, curso, cota)] = int(valor) if pd.notna(valor) else 0

    return vagas


# =========================
# UI CANDIDATO
# =========================

def tela_candidato(df, vagas, ultima_cota):
    nome = st.text_input("Digite seu nome")

    if not nome:
        return

    df_filtrado = df[df["Nome"].str.contains(nome, case=False, na=False)]

    if df_filtrado.empty:
        st.warning("Nenhum candidato encontrado")
        return

    for nome_candidato, grupo_nome in df_filtrado.groupby("Nome"):
        st.markdown(f"# {nome_candidato}")

        for _, row in grupo_nome.iterrows():

            proc = row["Processo seletivo"]
            curso = row["Curso"]
            cota = row["Cota do candidato"]
            status = row["Status"]

            ranking_geral = row["Ranking Geral"]
            ranking_cota = row["Ranking_cota"]

            ultima = ultima_cota.get((proc, curso, cota), 0)
            vagas_base = vagas.get((proc, curso, cota), 0)

            ocupadas = len(df[
                (df["Processo seletivo"] == proc) &
                (df["Curso"] == curso) &
                (df["Cota do candidato"] == cota) &
                (df["Status"] == "🟢 Matriculado")
            ])

            excedente = max(0, ocupadas - vagas_base)

            # status + processo unificado
            st.markdown(f"### 📌 {proc} — {status}")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**Curso:** {curso}")
                st.markdown(f"**Cota do candidato:** {cota}")

                st.markdown(
                    f"**Vagas na sua cota:** {vagas_base}"
                    + (f" + {excedente} vagas excedentes que vieram de outras cotas" if excedente > 0 else "")
                )

                st.markdown(f"**Vagas ocupadas:** {ocupadas}")

                if status == "🟢 Matriculado":
                    vaga = row.get("Cota da vaga garantida", "-")
                    st.markdown(f"**Conseguiu a vaga através de:** {vaga}")

            with col2:
                if pd.notna(ranking_geral):
                    st.markdown(f"**Sua posição no Ranking Geral:** {int(ranking_geral)}º")

                if cota == "AC":
                    ranking_cota_exibir = ranking_geral
                else:
                    ranking_cota_exibir = ranking_cota

                if pd.notna(ranking_cota_exibir):
                    st.markdown(f"**Sua posição no Ranking da sua Cota:** {int(ranking_cota_exibir)}º")

                # último chamado
                if ultima == 0:
                    texto_ultima = "Não houve chamada ainda"
                else:
                    texto_ultima = f"{int(ultima)}º"

                st.markdown(f"**Último chamado na cota:** {texto_ultima}")

                # distância
                if ultima and ranking_cota_exibir:
                    diff = int(ranking_cota_exibir) - int(ultima)

                    if diff > 0:
                        st.markdown(f"**Você está {diff} posições atrás do último chamado**")
                        st.markdown("Você ainda pode ser chamado se outros candidatos desistirem")
                    else:
                        st.markdown("Você está dentro da faixa de chamadas")

            st.divider()


# =========================
# UI GESTOR
# =========================

def tela_gestor(df):
    resumo = df.groupby(["Processo seletivo", "Curso", "Status"]).size().reset_index(name="Qtd")

    st.dataframe(resumo, use_container_width=True)


# =========================
# MAIN
# =========================

def main():
    st.title("Processos Seletivos")

    arquivo = st.file_uploader("Upload do Excel", type=["xlsx"])

    if not arquivo:
        return

    df_raw = pd.read_excel(arquivo, sheet_name="ranking")
    df_vagas = pd.read_excel(arquivo, sheet_name="vagas")

    df = processar(df_raw)
    vagas = calcular_vagas(df_vagas)
    ultima_cota = calcular_ultima_cota(df)

    modo = st.radio("Modo", ["Candidato", "Gestor"], horizontal=True)

    if modo == "Candidato":
        tela_candidato(df, vagas, ultima_cota)
    else:
        tela_gestor(df)


if __name__ == "__main__":
    main()
