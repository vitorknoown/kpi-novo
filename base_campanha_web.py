import io
import pandas as pd
import streamlit as st

# ---------------------------
# CONFIG DA PÁGINA
# ---------------------------
st.set_page_config(
    page_title="Base Campanha Abandono",
    page_icon=":telephone_receiver:",
    layout="centered",
)

LOGO_PATH = "Logo-Ejabrasil-sem-fundo.png.webp"

try:
    st.image(LOGO_PATH, width=260)
except Exception:
    st.warning("Logo não encontrada. Verifique o nome do arquivo de imagem.")

st.title("Base Campanha - Abandono")
st.markdown("Gere o arquivo para o discador automaticamente :rocket:")
st.markdown("---")


# ---------------------------
# FUNÇÕES AUXILIARES
# ---------------------------

@st.cache_data
def carregar_arquivo(arquivo):
    """Carrega arquivos CSV/Excel tentando várias codificações."""
    if arquivo is None:
        return None

    nome = arquivo.name.lower()

    # CSV
    if nome.endswith(".csv"):
        encodings = ["utf-8", "latin-1", "iso-8859-1", "cp1252", "utf-16"]
        for enc in encodings:
            try:
                arquivo.seek(0)
                return pd.read_csv(arquivo, sep=None, engine="python", encoding=enc)
            except Exception:
                pass
        for enc in encodings:
            try:
                arquivo.seek(0)
                return pd.read_csv(arquivo, sep=";", encoding=enc)
            except Exception:
                pass

        raise ValueError("Erro ao ler o CSV. Tente salvá-lo novamente em UTF-8.")

    # Excel
    elif nome.endswith((".xls", ".xlsx", ".xlsm", ".xlsb")):
        try:
            arquivo.seek(0)
            return pd.read_excel(arquivo)
        except Exception as e:
            raise ValueError(f"Erro ao ler Excel: {e}")

    else:
        raise ValueError("Tipo de arquivo não suportado.")


def padronizar_colunas(df):
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("ç", "c")
        .str.replace("á", "a")
        .str.replace("ã", "a")
        .str.replace("â", "a")
        .str.replace("é", "e")
        .str.replace("ê", "e")
        .str.replace("í", "i")
        .str.replace("ó", "o")
        .str.replace("ô", "o")
        .str.replace("ú", "u")
    )
    return df


def tentar_identificar_cpf(df):
    possiveis = ["cpf", "cpf_cliente", "cpf_aluno", "cpfcnpj", "cpf_cnpj"]
    for col in df.columns:
        if col.lower() in possiveis:
            return col
    return None


def preparar_bases(kpi_df, fid_df):
    """Padroniza e cruza KPI x Fidelizados."""
    kpi_final = aba_nome = fidelizados = None

    if kpi_df is not None:
        kpi_df = padronizar_colunas(kpi_df)
        kpi_final = kpi_df.copy()

        col_nome = next((c for c in kpi_df.columns if "nome" in c), None)
        if col_nome:
            aba_nome = kpi_df[[col_nome]].drop_duplicates()

    if fid_df is not None:
        fidelizados = padronizar_colunas(fid_df)

    # Cruzamento simples por CPF
    if kpi_final is not None and fidelizados is not None:
        cpf_k = tentar_identificar_cpf(kpi_final)
        cpf_f = tentar_identificar_cpf(fidelizados)
        if cpf_k and cpf_f:
            kpi_final["eh_fidelizado"] = kpi_final[cpf_k].isin(fidelizados[cpf_f])

    return kpi_final, aba_nome, fidelizados


def gerar_base_discador(kpi_final):
    """Gera arquivo exatamente no formato do discador."""

    if kpi_final is None or kpi_final.empty:
        return None

    df = kpi_final.copy()

    # Identificar telefone
    COL_TELEFONE = None
    for c in df.columns:
        if any(p in c.lower() for p in ["tel", "cel", "fone", "whats"]):
            COL_TELEFONE = c
            break

    if COL_TELEFONE is None:
        st.error("Não foi possível identificar a coluna de telefone na KPI.")
        return None

    # Identificar nome
    COL_NOME = next((c for c in df.columns if "nome" in c.lower()), None)

    # Identificar CPF
    COL_CPF = tentar_identificar_cpf(df)

    # identificar algum código identificador
    COL_COD = next(
        (c for c in df.columns if c.lower() in ["id", "matricula", "codcliente"]),
        None,
    )

    base = pd.DataFrame()
    base["TIPO_DE_REGISTRO"] = "TELEFONE"

    base["VALOR_DO_REGISTRO"] = (
        df[COL_TELEFONE]
        .astype(str)
        .str.replace(r"\D", "", regex=True)
    )

    base["MENSAGEM"] = ""

    base["NOME_CLIENTE"] = df[COL_NOME].astype(str) if COL_NOME else ""

    base["CPFCNPJ"] = df[COL_CPF].astype(str) if COL_CPF else ""

    base["CODCLIENTE"] = df[COL_COD].astype(str) if COL_COD else ""

    for col in ["TAG", "CORINGA1", "CORINGA2", "CORINGA3", "CORINGA4", "CORINGA5", "PRIORIDADE"]:
        base[col] = ""

    colunas = [
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

    return base[colunas]


def df_vazio(df):
    return (df is None) or (isinstance(df, pd.DataFrame) and df.empty)


# ---------------------------
# UPLOAD DAS BASES
# ---------------------------

st.subheader("1. Upload das bases")

col1, col2 = st.columns(2)

with col1:
    kpi_file = st.file_uploader(
        "Base KPI (obrigatória)",
        type=["xls", "xlsx", "xlsm", "xlsb", "csv"],
    )

with col2:
    fid_file = st.file_uploader(
        "Base Fidelizados (opcional)",
        type=["xls", "xlsx", "xlsm", "xlsb", "csv"],
    )

st.markdown("---")
st.subheader("2. Visualização")


def preview(df, titulo):
    if df is None or df.empty:
        st.info(f"Nenhum arquivo enviado para {titulo}.")
    else:
        st.markdown(f"**{titulo}**")
        st.write(f"{df.shape[0]} linhas | {df.shape[1]} colunas")
        st.dataframe(df.head(10))


# Carregar arquivos
kpi_df = fid_df = None

with st.spinner("Carregando arquivos..."):
    if kpi_file:
        kpi_df = carregar_arquivo(kpi_file)
    if fid_file:
        fid_df = carregar_arquivo(fid_file)

preview(kpi_df, "KPI")
preview(fid_df, "Fidelizados")

# ---------------------------
# PROCESSAMENTO E DOWNLOAD
# ---------------------------

st.markdown("---")
st.subheader("3. Gerar base final para o discador (Excel)")

if st.button("Gerar Excel para discador"):
    if df_vazio(kpi_df):
        st.error("A base KPI é obrigatória.")
    else:
        with st.spinner("Processando..."):
            kpi_final, aba_nome, fidelizados = preparar_bases(kpi_df, fid_df)
            base_discador = gerar_base_discador(kpi_final)

        if df_vazio(base_discador):
            st.error("Não foi possível gerar a base do discador.")
        else:
            st.success("Base gerada com sucesso!")

            # 👉 AQUI: gera EXCEL (.xlsx) com o padrão do arquivo
            output = io.BytesIO()
            with pd.ExcelWriter(output) as writer:  # sem engine explícito
                base_discador.to_excel(writer, index=False, sheet_name="Abandono")

            output.seek(0)

            st.download_button(
                "Baixar base para discador (Excel)",
                data=output.getvalue(),
                file_name="base_abandono_discador.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

st.markdown("---")
st.caption("EJA Brasil • Geração automática de base para campanha de abandono.")
