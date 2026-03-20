import streamlit as st
import pandas as pd
import re

VERSAO = "5.11.2"

st.set_page_config(page_title="DASHBOARD PROCESSOS SELETIVOS", layout="wide")

MAPA_STATUS = {
    "Etapa 2 concluída":"🟢 Matriculado",
    "Etapa 1 concluída":"🟡 Em processo",
    "Desistiu da vaga":"🔴 Desistiu da vaga",
    "Matrícula cancelada":"🔴 Matrícula cancelada",
    "Indeferido":"🔴 Indeferido",
    "Não compareceu":"🔴 Não compareceu",
    "Enviou documentação":"🟡 Em processo",
    "Enviou substituição de documentos":"🟡 Em processo",
    "Enviou recurso":"🟡 Em processo",
    "Enviar recurso":"🟡 Em processo",
    "Enviar substituição de documentos":"🟡 Em processo",
    "Aguardando vaga":"🟡 Aguardando vaga",
    "Aguardando convocação em outra cota":"🟡 Aguardando vaga"
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

def format_date(dt):
    if pd.isna(dt): return ""
    return dt.strftime("%d/%m às %Hh%M")

def get_active_phase(df_group):
    now = pd.Timestamp.now()
    
    for _, row in df_group.iterrows():
        sit = str(row.get('etapa_do_processo', '')).strip()
        cand_start, cand_end = parse_dates(row.get('prazo_candidato'))
        int_start, int_end = parse_dates(row.get('prazo_analise_interna'))
        res_start, _ = parse_dates(row.get('publicação_resultado'))

        if cand_start and now < cand_start:
            return f"⏳ Aguardando: {sit} (inicia em {format_date(cand_start)})"
        
        if cand_start and cand_end and cand_start <= now <= cand_end:
            return f"🟢 {sit} (Prazo do Candidato - até {format_date(cand_end)})"
        
        if cand_end and int_start and cand_end < now < int_start:
            return f"🟡 Aguardando Análise: {sit}"
        
        if int_start and int_end and int_start <= now <= int_end:
            return f"🟡 {sit} (Análise Interna - até {format_date(int_end)})"
        
        if int_end and res_start and int_end < now < res_start:
            return f"🟡 Aguardando Resultado (sai dia {format_date(res_start)})"
        
        final_date = res_start if res_start else (int_end if int_end else cand_end)
        
        if final_date and now <= final_date:
            return f"🟡 Em andamento: {sit}"
        
        if final_date and now > final_date:
            continue 
    
    return "🔴 Processo Finalizado"

def extrair_chamada(txt):
    if pd.isna(txt): return 0
    nums = re.findall(r"(\d+)ª", str(txt))
    if not nums: return 0
    return max([int(n) for n in nums])

def detectar_chamada_atual(df):
    chamadas = df.groupby("Processo seletivo")["Chamada"].max()
    return chamadas.to_dict()

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

def status_exibicao(row, chamada_atual, chamada_fechada):
    s = str(row["Situação do requerimento de matrícula"]).strip()
    proc = row["Processo seletivo"]
    chamada = row["Chamada"]

    if s in MAPA_STATUS: return MAPA_STATUS[s]
    if chamada == 0: return "⚪ Lista de espera"

    atual = chamada_atual.get(proc, 0)

    if chamada == atual:
        if chamada_fechada.get(proc, False): return "🔴 Não compareceu"
        return "🟡 Convocado"

    if chamada < atual: return "🔴 Não compareceu"
    return "⚪ Sem status"

def processar(df):
    df = df.copy()

    for c in ["Curso", "Processo seletivo", "Cota do candidato", "Cota da vaga garantida"]:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str).str.strip()
            # Padronização de segurança para cruzamento de dados
            if c in ["Curso", "Processo seletivo"]:
                df[c] = df[c].str.upper()

    df["Nota final"] = pd.to_numeric(df["Nota final"], errors="coerce").fillna(0)
    df["Ranking"] = pd.to_numeric(df["Class ACP1"], errors="coerce")
    df["Chamada"] = df["Chamadas"].apply(extrair_chamada)

    df["Ranking Cota"] = df.groupby(["Curso", "Processo seletivo", "Cota do candidato"])["Ranking"].rank(method="min").fillna(0).astype(int)

    chamada_atual = detectar_chamada_atual(df)
    chamada_fechada = chamada_encerrada(df)

    df["Status"] = df.apply(lambda r: status_exibicao(r, chamada_atual, chamada_fechada), axis=1)
    df = df.rename(columns={"Cota da vaga garantida": "Vaga ocupada"})
    
    return df, chamada_atual, chamada_fechada

def processar_vagas(df_vagas):
    df_vagas = df_vagas.copy()
    # Padronização de segurança para cruzamento de dados
    if "Curso" in df_vagas.columns:
        df_vagas["Curso"] = df_vagas["Curso"].astype(str).str.strip().str.upper()
    if "Processo seletivo" in df_vagas.columns:
        df_vagas["Processo seletivo"] = df_vagas["Processo seletivo"].astype(str).str.strip().str.upper()
    return df_vagas

def style_df(df):
    def cor(row):
        if row["Status"] == "🟢 Matriculado": return ["background-color:#e6ffed"] * len(row)
        if row["Status"] in ["🟡 Em processo", "🟡 Aguardando vaga"]: return ["background-color:#fffbe6"] * len(row)
        if row["Status"] == "🟡 Convocado": return ["background-color:#e6f7ff"] * len(row)
        if row["Status"] in ["⚪ Lista de espera", "⚪ Sem status"]: return ["background-color:#f5f5f5"] * len(row)
        if row["Status"] in STATUS_ENCERRADO: return ["background-color:#fff1f0"] * len(row)
        return [""] * len(row)

    sty = df.style.apply(cor, axis=1).set_properties(**{"text-align": "center"})
    if "Nome" in df.columns: sty = sty.set_properties(subset=["Nome"], **{"text-align": "left"})
    
    format_dict = {}
    if "Ranking" in df.columns: format_dict["Ranking"] = "{:.0f}"
    if "Ranking Cota" in df.columns: format_dict["Ranking Cota"] = "{:.0f}"
    if "Nota" in df.columns: format_dict["Nota"] = "{:.2f}"
    if "Nota final" in df.columns: format_dict["Nota final"] = "{:.2f}"
    
    sty = sty.format(format_dict, na_rep="")
    
    return sty

def resumo_geral(df, chamada_atual, chamada_fechada, df_crono):
    st.markdown("## 📊 Visão Geral Global")

    total = len(df)
    matriculados = len(df[df["Status"] == "🟢 Matriculado"])
    aguardando = len(df[df["Status"] == "🟡 Aguardando vaga"])
    processo = len(df[df["Status"] == "🟡 Em processo"])
    convocados = len(df[df["Status"] == "🟡 Convocado"])
    lista_espera = len(df[df["Status"] == "⚪ Lista de espera"])

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Matriculados", matriculados)
    c2.metric("Aguardando Vaga", aguardando)
    c3.metric("Em processo", processo)
    c4.metric("Convocados", convocados)
    c5.metric("Lista de espera", lista_espera)
    c6.metric("Candidatos", total)

    resumo = df.groupby("Curso").agg(
        Matriculados=("Status", lambda x: (x == "🟢 Matriculado").sum()),
        Aguardando_vaga=("Status", lambda x: (x == "🟡 Aguardando vaga").sum()),
        Em_processo=("Status", lambda x: (x == "🟡 Em processo").sum()),
        Convocados=("Status", lambda x: (x == "🟡 Convocado").sum()),
        Lista_de_espera=("Status", lambda x: (x == "⚪ Lista de espera").sum()),
        Candidatos=("Nome", "count")
    ).reset_index()

    resumo = resumo.rename(columns={"Aguardando_vaga": "Aguardando vaga", "Em_processo": "Em processo", "Lista_de_espera": "Lista de espera"})
    resumo = resumo[["Curso", "Matriculados", "Aguardando vaga", "Em processo", "Convocados", "Lista de espera", "Candidatos"]]
    st.dataframe(resumo, use_container_width=True, hide_index=True)

    st.markdown("### 📋 Situação dos Processos Seletivos")
    
    if df_crono is not None and not df_crono.empty:
        df_crono_local = df_crono.copy()
        df_crono_local.columns = [c.lower().strip() for c in df_crono_local.columns]
        dados_processos = []
        for (proc, chamada), group in df_crono_local.groupby(['processo', 'chamada']):
            fase = get_active_phase(group)
            dados_processos.append({
                "Processo seletivo": str(proc).upper(),
                "Chamada": f"{chamada}ª Chamada",
                "Status / Fase Atual": fase
            })
        df_proc = pd.DataFrame(dados_processos).sort_values(by=["Processo seletivo", "Chamada"])
        st.dataframe(df_proc, use_container_width=True, hide_index=True)
    else:
        dados_processos = []
        for proc, atual in chamada_atual.items():
            situacao = "🔴 Finalizada" if chamada_fechada.get(proc, False) else "🟢 Em andamento"
            dados_processos.append({
                "Processo seletivo": proc,
                "Chamada atual": f"{atual}ª Chamada" if atual > 0 else "Nenhuma",
                "Situação": situacao
            })
        st.dataframe(pd.DataFrame(dados_processos), use_container_width=True, hide_index=True)

def render_busca(df):
    st.markdown("## 🔎 Resultado da busca")
    df = df.rename(columns={"Processo seletivo": "Processo", "Nota final": "Nota", "Cota do candidato": "Cota"})
    cols = ["Processo", "Curso", "Nome", "Ranking Cota", "Ranking", "Nota", "Chamada", "Cota", "Vaga ocupada", "Status"]
    cols = [c for c in cols if c in df.columns]
    st.dataframe(style_df(df[cols]), use_container_width=True, hide_index=True)

def main():
    st.title("Gestão de Processos Seletivos")
    st.caption(f"Versão {VERSAO}")

    with st.sidebar:
        with st.expander("📥 Fonte de Dados", expanded=True):
            arquivo = st.file_uploader("Carregar base de dados (.xlsx)", type=["xlsx"])

    if not arquivo:
        st.stop()

    df_raw = pd.read_excel(arquivo, sheet_name="ranking")
    df_vagas_raw = pd.read_excel(arquivo, sheet_name="vagas")
    
    try:
        df_crono = pd.read_excel(arquivo, sheet_name="cronograma")
    except:
        df_crono = None

    df, chamada_atual, chamada_fechada = processar(df_raw)
    df_vagas = processar_vagas(df_vagas_raw)

    with st.sidebar:
        st.text_input("Buscar candidato", key="busca")
        
        cursos = sorted(df["Curso"].unique())
        if st.session_state.curso not in ["-- Todos os Cursos --"] + cursos:
            st.session_state.curso = "-- Todos os Cursos --"
            
        st.selectbox("Curso", ["-- Todos os Cursos --"] + cursos, key="curso")

        if st.session_state.curso != "-- Todos os Cursos --":
            df_curso_opcoes = df[df["Curso"] == st.session_state.curso]
            processos = sorted(df_curso_opcoes["Processo seletivo"].unique())
        else:
            processos = []

        if st.session_state.processo not in ["Todos"] + processos:
            st.session_state.processo = "Todos"

        if st.session_state.curso != "-- Todos os Cursos --":
            st.selectbox("Processo seletivo", ["Todos"] + processos, key="processo")
            st.selectbox("Cota", ["Todas"] + COTAS, key="cota")
            st.checkbox("Ocultar candidatos com processo encerrado", key="ocultar")

        st.divider()
        st.button("🧹 Limpar Filtros", on_click=limpar_filtros, use_container_width=True)

    if st.session_state.busca:
        df_busca = df[df["Nome"].str.contains(st.session_state.busca, case=False, na=False)]
        st.info(f"{len(df_busca)} candidatos encontrados")
        render_busca(df_busca)
        return

    if st.session_state.curso == "-- Todos os Cursos --":
        resumo_geral(df, chamada_atual, chamada_fechada, df_crono)
        return

    df_curso = df[df["Curso"] == st.session_state.curso]
    
    if st.session_state.processo != "Todos":
        df_view = df_curso[df_curso["Processo seletivo"] == st.session_state.processo]
        processos_view = [st.session_state.processo]
    else:
        df_view = df_curso
        processos_view = df_curso["Processo seletivo"].unique()

    st.markdown(f"## 📊 Visão Geral: {st.session_state.curso}")
    
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Matriculados", len(df_view[df_view["Status"] == "🟢 Matriculado"]))
    c2.metric("Aguardando Vaga", len(df_view[df_view["Status"] == "🟡 Aguardando vaga"]))
    c3.metric("Em processo", len(df_view[df_view["Status"] == "🟡 Em processo"]))
    c4.metric("Convocados", len(df_view[df_view["Status"] == "🟡 Convocado"]))
    c5.metric("Lista de espera", len(df_view[df_view["Status"] == "⚪ Lista de espera"]))
    c6.metric("Candidatos", len(df_view))
    
    st.divider()
    
    st.markdown("### 🎯 Quadro Consolidado de Vagas")
    df_vagas_curso = df_vagas[df_vagas["Curso"] == st.session_state.curso]
    
    dados_vagas = []
    
    for proc in processos_view:
        df_vagas_proc = df_vagas_curso[df_vagas_curso["Processo seletivo"] == proc]
        df_mat_proc = df_curso[(df_curso["Processo seletivo"] == proc) & (df_curso["Status"] == "🟢 Matriculado")]
        
        if st.session_state.cota == "Todas":
            v_ofertadas = df_vagas_proc[COTAS].sum().sum() if not df_vagas_proc.empty else 0
            v_preenchidas = len(df_mat_proc)
        else:
            v_ofertadas = df_vagas_proc[st.session_state.cota].sum() if (not df_vagas_proc.empty and st.session_state.cota in df_vagas_proc.columns) else 0
            v_preenchidas = len(df_mat_proc[df_mat_proc["Vaga ocupada"] == st.session_state.cota])
            
        dados_vagas.append({
            "Processo seletivo": proc,
            "Vagas Ofertadas": int(v_ofertadas),
            "Vagas Preenchidas": int(v_preenchidas),
            "Saldo de Vagas": int(v_ofertadas - v_preenchidas)
        })
        
    if dados_vagas:
        st.dataframe(pd.DataFrame(dados_vagas), use_container_width=True, hide_index=True)

    st.markdown("### 🧩 Vagas por Cota")
    dados_cota = []
    cotas_analisadas = COTAS if st.session_state.cota == "Todas" else [st.session_state.cota]

    for cota_especifica in cotas_analisadas:
        ofertadas_cota = 0
        preenchidas_cota = 0
        for proc in processos_view:
            df_vagas_proc = df_vagas_curso[df_vagas_curso["Processo seletivo"] == proc]
            df_mat_proc = df_curso[(df_curso["Processo seletivo"] == proc) & (df_curso["Status"] == "🟢 Matriculado")]
            
            ofertadas_cota += df_vagas_proc[cota_especifica].sum() if (not df_vagas_proc.empty and cota_especifica in df_vagas_proc.columns) else 0
            preenchidas_cota += len(df_mat_proc[df_mat_proc["Vaga ocupada"] == cota_especifica])
            
        dados_cota.append({
            "Cota": cota_especifica,
            "Vagas Ofertadas": int(ofertadas_cota),
            "Vagas Preenchidas": int(preenchidas_cota),
            "Saldo de Vagas": int(ofertadas_cota - preenchidas_cota)
        })

    if dados_cota:
        st.dataframe(pd.DataFrame(dados_cota), use_container_width=True, hide_index=True)
        
    st.markdown("### 📋 Cronograma Local")
    if df_crono is not None and not df_crono.empty:
        df_crono_local = df_crono.copy()
        df_crono_local.columns = [c.lower().strip() for c in df_crono_local.columns]
        dados_crono_local = []
        
        for proc in processos_view:
            global_atual = chamada_atual.get(proc, 0)
            if global_atual == 0: continue
            
            max_chamada_curso = df_curso[df_curso["Processo seletivo"] == proc]["Chamada"].max()
            
            if pd.isna(max_chamada_curso) or max_chamada_curso < global_atual:
                fase = "⚪ Sem convocados na chamada atual"
            else:
                group = df_crono_local[(df_crono_local['processo'].str.lower() == str(proc).lower()) & (df_crono_local['chamada'] == global_atual)]
                if not group.empty:
                    fase = get_active_phase(group)
                else:
                    fase = "⚪ Cronograma indisponível"
                    
            dados_crono_local.append({
                "Processo seletivo": str(proc).upper(),
                "Chamada ativa (Global)": f"{global_atual}ª Chamada",
                "Status do Curso": fase
            })
            
        if dados_crono_local:
            st.dataframe(pd.DataFrame(dados_crono_local).sort_values("Processo seletivo"), use_container_width=True, hide_index=True)
    st.divider()

    if st.session_state.ocultar:
        df_view = df_view[~df_view["Status"].isin(STATUS_ENCERRADO)]

    if st.session_state.cota != "Todas":
        df_view = df_view[df_view["Cota do candidato"] == st.session_state.cota].copy()
    
    cols = ["Ranking Cota", "Ranking", "Inscrição", "Nome", "Nota final", "Chamada", "Cota do candidato", "Vaga ocupada", "Status"]
    cols = [c for c in cols if c in df_view.columns]

    if st.session_state.processo == "Todos":
        if "Ranking" in cols: cols.remove("Ranking")
        if "Ranking Cota" in cols: cols.remove("Ranking Cota")
        df_view = df_view.sort_values("Nome")
    else:
        df_view = df_view.sort_values("Ranking")

    st.markdown("#### Lista de Candidatos")
    st.dataframe(style_df(df_view[cols]), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
