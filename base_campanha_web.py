import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Base Campanha", page_icon=":bar_chart:", layout="centered")

LOGO_PATH = "Logo-Ejabrasil-sem-fundo.png.webp"

try:
    st.image(LOGO_PATH, width=260)
except Exception:
    st.warning("Logo não encontrada. Verifique o nome do arquivo de imagem na pasta do app.")

st.title("Base Campanha")
st.markdown("Organize e limpe suas bases de campanha de forma automática :rocket:")
st.markdown("---")

@st.cache_data
def carregar_arquivo(arquivo):
    if arquivo is None:
        return None

    nome = arquivo.name.lower()

    # Se for CSV, tentamos várias codificações
    if nome.endswith(".csv"):
        for encoding in ["utf-8", "latin-1", "iso-8859-1", "cp1252", "utf-16"]:
            try:
                arquivo.seek(0)
                return pd.read_csv(arquivo, encoding=encoding, sep=None, engine="python")
            except Exception:
                pass

        # Última tentativa: tentar separador ";"
        for encoding in ["utf-8", "latin-1", "iso-8859-1", "cp1252", "utf-16"]:
            try:
                arquivo.seek(0)
                return pd.read_csv(arquivo, encoding=encoding, sep=";")
            except Exception:
                pass

        raise ValueError("Erro ao ler o CSV — tente salvar novamente como UTF-8.")

    # Arquivos Excel (mais seguros)
    elif nome.endswith((".xls", ".xlsx", ".xlsm", ".xlsb")):
        try:
            return pd.read_excel(arquivo, engine="openpyxl")
        except Exception:
            arquivo.seek(0)
            return pd.read_excel(arquivo)

    else:
        raise ValueError("Tipo de arquivo não suportado. Use CSV ou Excel.")

def padronizar_colunas(df):
    df = df.copy()
    df.columns = (df.columns.astype(str)
        .str.strip().str.lower().str.replace(" ", "_")
        .str.replace("ç","c").str.replace("ã","a").str.replace("á","a")
        .str.replace("é","e").str.replace("í","i").str.replace("ó","o").str.replace("ú","u")
    )
    return df

def tentar_identificar_cpf(df):
    possiveis = ["cpf","cpf_cliente","cpf_aluno","cpf_cnpj"]
    cols = [c.lower() for c in df.columns]
    for c in possiveis:
        if c in cols:
            return c
    return None

def preparar_bases(kpi_df, fid_df, painel_df):
    kpi_final = aba_nome = fidelizados = painel = None
    if kpi_df is not None:
        kpi_df = padronizar_colunas(kpi_df)
        kpi_final = kpi_df.copy()
        col_nome = next((c for c in kpi_df.columns if "nome" in c), None)
        if col_nome:
            aba_nome = kpi_df[[col_nome]].drop_duplicates().reset_index(drop=True)
    if fid_df is not None:
        fidelizados = padronizar_colunas(fid_df)
    if painel_df is not None:
        painel = padronizar_colunas(painel_df)
    if kpi_final is not None and fidelizados is not None:
        cpf_k = tentar_identificar_cpf(kpi_final)
        cpf_f = tentar_identificar_cpf(fidelizados)
        if cpf_k and cpf_f:
            kpi_final["eh_fidelizado"] = kpi_final[cpf_k].isin(fidelizados[cpf_f])
    if kpi_final is not None and painel is not None:
        cpf_k = tentar_identificar_cpf(kpi_final)
        cpf_p = tentar_identificar_cpf(painel)
        if cpf_k and cpf_p:
            painel_reduz = painel.drop_duplicates(subset=[cpf_p])
            kpi_final = kpi_final.merge(
                painel_reduz, left_on=cpf_k, right_on=cpf_p, how="left"
            )
    return kpi_final, aba_nome, fidelizados, painel

st.subheader("1. Faça upload das bases")
col1, col2 = st.columns(2)
with col1:
    kpi_file = st.file_uploader("Importar KPI", type=["xls","xlsx","xlsm","xlsb","csv"])
with col2:
    fid_file = st.file_uploader("Importar Fidelizados", type=["xls","xlsx","xlsm","xlsb","csv"])
painel_file = st.file_uploader("Importar Painel", type=["xls","xlsx","xlsm","xlsb","csv"])

st.markdown("---")
st.subheader("2. Pré-visualização das bases")

def preview(df, titulo):
    if df is not None:
        st.markdown(f"**{titulo}**")
        st.write(f"Linhas: {df.shape[0]} | Colunas: {df.shape[1]}")
        st.dataframe(df.head(10))
    else:
        st.info(f"Nenhum arquivo de {titulo} enviado.")

kpi_df = fid_df = painel_df = None
with st.spinner("Carregando arquivos..."):
    if kpi_file: kpi_df = carregar_arquivo(kpi_file)
    if fid_file: fid_df = carregar_arquivo(fid_file)
    if painel_file: painel_df = carregar_arquivo(painel_file)

preview(kpi_df, "KPI")
preview(fid_df, "Fidelizados")
preview(painel_df, "Painel")

st.markdown("---")
st.subheader("3. Processamento e download")

def df_vazio(df):
    return (df is None) or (isinstance(df, pd.DataFrame) and df.empty)
    
def detectar_coluna(df, candidatos):
    """Tenta achar uma coluna baseada em pedaços de nome (ex: 'telefone', 'celular')."""
    if df is None:
        return None
    for col in df.columns:
        col_lower = str(col).lower()
        for cand in candidatos:
            if cand in col_lower:
                return col
    return None


def gerar_base_discador(kpi_final: pd.DataFrame) -> pd.DataFrame | None:
    """
    Gera a base no formato:
    TIPO_DE_REGISTRO;VALOR_DO_REGISTRO;MENSAGEM;NOME_CLIENTE;CPFCNPJ;...
    usando, principalmente, a base KPI.
    """
    if kpi_final is None or kpi_final.empty:
        return None

    df = kpi_final.copy()

    # Detecta possíveis colunas
    col_tel = detectar_coluna(df, ["telefone", "celular", "whats", "whatsapp", "fone"])
    col_nome = detectar_coluna(df, ["nome"])
    col_cpf = detectar_coluna(df, ["cpf", "cpfcnpj"])
    col_cod = detectar_coluna(df, ["codcliente", "id_cliente", "matricula", "id"])

    if col_tel is None:
        st.error("Não foi possível identificar a coluna de telefone na base KPI.")
        return None

    base = pd.DataFrame()

    # 1) TIPO_DE_REGISTRO (fixo TELEFONE)
    base["TIPO_DE_REGISTRO"] = "TELEFONE"

    # 2) VALOR_DO_REGISTRO (telefone só com números)
    base["VALOR_DO_REGISTRO"] = (
        df[col_tel]
        .astype(str)
        .str.replace(r"\D", "", regex=True)  # remove tudo que não é número
    )

    # 3) MENSAGEM (vazia ou você pode colocar um texto fixo)
    base["MENSAGEM"] = ""

    # 4) NOME_CLIENTE
    if col_nome:
        base["NOME_CLIENTE"] = df[col_nome].astype(str)
    else:
        base["NOME_CLIENTE"] = ""

    # 5) CPFCNPJ
    if col_cpf:
        base["CPFCNPJ"] = df[col_cpf].astype(str)
    else:
        base["CPFCNPJ"] = ""

    # 6) CODCLIENTE
    if col_cod:
        base["CODCLIENTE"] = df[col_cod].astype(str)
    else:
        base["CODCLIENTE"] = ""

    # 7) Demais campos vazios
    for col in ["TAG", "CORINGA1", "CORINGA2", "CORINGA3", "CORINGA4", "CORINGA5", "PRIORIDADE"]:
        base[col] = ""

    # Garante a ordem das colunas
    colunas_finais = [
        "TIPO_DE_REGISTRO",
        "VALOR_DO_REGISTRO",
        "MENSAGEM",
        "NOME_CLIENTE",
        "CPFCNPJ",
        "CODCLIENTE",
        "TAG",
        "CORINGA1",
        "CORINGA2",
        "CORINGA3",
        "CORINGA4",
        "CORINGA5",
        "PRIORIDADE",
    ]
    base = base[colunas_finais]

    return base

if st.button("Processar bases"):
    # Se todas as bases forem None ou vazias, mostra erro
    if all(df_vazio(df) for df in [kpi_df, fid_df, painel_df]):
        st.error("Envie pelo menos uma base com dados para processar.")
    else:
        with st.spinner("Processando..."):
            kpi_final, aba_nome, fidelizados, painel = preparar_bases(
                kpi_df, fid_df, painel_df
            )

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                if kpi_final is not None:
                    kpi_final.to_excel(writer, "kpi", index=False)
                if aba_nome is not None:
                    aba_nome.to_excel(writer, "nome", index=False)
                if fidelizados is not None:
                    fidelizados.to_excel(writer, "fidelizados", index=False)
                if painel is not None:
                    painel.to_excel(writer, "painel", index=False)

            buf.seek(0)

        st.success("Pronto!")
        st.download_button(
            "Baixar Excel Final",
            buf,
            "base_campanha_final.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
