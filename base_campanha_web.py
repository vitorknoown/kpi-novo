def gerar_base_discador(kpi_final):
    """Gera arquivo exatamente no formato do discador,
    com 1 linha por telefone e nome quando disponível.
    """

    if kpi_final is None or kpi_final.empty:
        return None

    df = kpi_final.copy()

    # ---------- identificar colunas na KPI ----------
    # telefone
    COL_TELEFONE = None
    for c in df.columns:
        if any(p in c.lower() for p in ["tel", "cel", "fone", "whats"]):
            COL_TELEFONE = c
            break

    if COL_TELEFONE is None:
        st.error("Não foi possível identificar a coluna de telefone na KPI.")
        return None

    # nome
    COL_NOME = next((c for c in df.columns if "nome" in c.lower()), None)

    # CPF
    COL_CPF = tentar_identificar_cpf(df)

    # código cliente / matrícula / id
    COL_COD = next(
        (c for c in df.columns if c.lower() in ["id", "matricula", "codcliente"]),
        None,
    )

    # ---------- limpar e deduplicar pelos telefones ----------
    df["_telefone_limpo"] = (
        df[COL_TELEFONE]
        .astype(str)
        .str.replace(r"\D", "", regex=True)  # só números
    )

    # remove linhas sem telefone ou muito curtos
    df = df[df["_telefone_limpo"].notna()]
    df = df[df["_telefone_limpo"] != ""]
    df = df[df["_telefone_limpo"].str.len() >= 8]

    # prioriza linhas que têm nome preenchido (para escolher melhor registro)
    if COL_NOME:
        df["_tem_nome"] = df[COL_NOME].notna() & (df[COL_NOME].astype(str).str.strip() != "")
        df = df.sort_values(by=["_tem_nome"], ascending=False)
    else:
        df["_tem_nome"] = False

    # remove duplicatas: fica 1 linha por telefone
    df = df.drop_duplicates(subset=["_telefone_limpo"]).reset_index(drop=True)

    # ---------- montar base final no padrão do discador ----------
    base = pd.DataFrame()
    base["TIPO_DE_REGISTRO"] = "TELEFONE"
    base["VALOR_DO_REGISTRO"] = df["_telefone_limpo"]

    base["MENSAGEM"] = ""

    if COL_NOME:
        base["NOME_CLIENTE"] = df[COL_NOME].astype(str)
    else:
        base["NOME_CLIENTE"] = ""

    if COL_CPF:
        base["CPFCNPJ"] = df[COL_CPF].astype(str)
    else:
        base["CPFCNPJ"] = ""

    if COL_COD:
        base["CODCLIENTE"] = df[COL_COD].astype(str)
    else:
        base["CODCLIENTE"] = ""

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

    base = base[colunas].reset_index(drop=True)
    return base
