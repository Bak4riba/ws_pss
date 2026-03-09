import pdfplumber
import re


def limpar_texto(texto):
    """Remove quebras de linha e hifenização."""
    if not texto:
        return ""
    return re.sub(r'-?\n\s*', '', texto).strip()


TURNOS_CURTOS = {"M", "T", "N"}
TURNOS_LONGOS = {"MANHÃ", "TARDE", "NOITE"}


def eh_tabela_de_aulas(table):
    """Verifica se uma tabela é de distribuição de aulas."""
    if not table or len(table) < 3:
        return False
    # Verifica nas primeiras 5 linhas — algumas tabelas têm linha extra vazia
    for row in table[1:5]:
        vals = [str(c).strip().upper() for c in row if c and str(c).strip()]
        if len([v for v in vals if v in TURNOS_CURTOS]) >= 3:
            return True
        if len([v for v in vals if v in TURNOS_LONGOS]) >= 2:
            return True
    return False


def linha_dos_turnos(table):
    """Retorna o índice da linha que contém os turnos (M/T/N ou MANHÃ/TARDE/NOITE)."""
    for i, row in enumerate(table[1:5], start=1):
        vals = [str(c).strip().upper() for c in row if c and str(c).strip()]
        if len([v for v in vals if v in TURNOS_CURTOS]) >= 3:
            return i
        if len([v for v in vals if v in TURNOS_LONGOS]) >= 2:
            return i
    return 2  # fallback


def normalizar_turno(val):
    """Normaliza turnos longos para curtos."""
    mapa = {"MANHÃ": "M", "TARDE": "T", "NOITE": "N"}
    return mapa.get(str(val).strip().upper(), val)


def normalizar_tabela(table):
    """
    Corrige tabelas onde o pdfplumber fundiu 'Ensino Fundamental\nM T N' numa célula.
    Separa o M/T/N para a linha correta.
    """
    table = [list(row) for row in table]  # copia mutável

    for i, row in enumerate(table):
        for j, cell in enumerate(row):
            if not cell:
                continue
            # Detecta célula com nível + turnos embutidos ex: "Ensino Fundamental\nM T N"
            padrao = r'(Ensino\s+\w+)\s*\n\s*(M\s+T\s+N)'
            match = re.search(padrao, str(cell), re.IGNORECASE)
            if match:
                # Limpa a célula deixando só o nível
                table[i][j] = match.group(1)
                # Garante que a próxima linha tem M na coluna correta
                if i + 1 < len(table):
                    proxima = table[i + 1]
                    # Se a célula na mesma coluna está vazia, insere M
                    if j < len(proxima) and not proxima[j]:
                        proxima[j] = "M"
    return table


def limpar_aulas(valor):
    """
    Separa o número de aulas da nota de referência.
    Ex: '*6' -> ('6', '*Docência II será na observação')
        '6 subst.' -> ('6', 'subst.')
        '4' -> ('4', '')
    """
    if not valor:
        return "", ""
    valor = valor.strip()
    match = re.match(r'^\*(\d+)(.*)$', valor)
    if match:
        return match.group(1) + match.group(2).strip(), "*"
    match = re.match(r'^(\d+)\s+(.+)$', valor)
    if match:
        return match.group(1), match.group(2)
    return valor, ""


def extrair_nota_linha(row):
    """Retorna nota *Docência II da última coluna, se houver."""
    for val in reversed(row):
        if val and re.search(r'Docência|Docencia', str(val), re.IGNORECASE):
            return limpar_texto(val)
    return ""


def extrair_aulas_da_tabela(table):
    """
    Extrai registros de aulas de uma tabela.

    Cada tabela tem:
    - Linha 0: [MUNICÍPIO, DISC1, None, None, DISC2_ou_None, ...]
    - Linha 1: [ESTABELECIMENTO, Ensino Fundamental, ..., Ensino Médio, ...]
    - Linha 2: [None, M, T, N, M, T, N]
    - Linha 3+: [escola, val, val, val, val, val, val, nota?]

    Casos:
    1. 1 disciplina, Fund + Médio: 2 blocos com mesmo nome, níveis diferentes
    2. 2 disciplinas distintas: 2 blocos com nomes diferentes (ex: Filosofia + Sociologia)
    3. 1 disciplina, só Médio: 2 blocos com mesmo nome, ambos nível Médio
    """
    registros = []
    table = normalizar_tabela(table)
    linha0 = table[0]
    linha1 = table[1]
    idx_turnos = linha_dos_turnos(table)
    linha2 = table[idx_turnos]

    municipio = limpar_texto(linha0[0]) if linha0[0] else ""

    # Normaliza turnos longos para curtos
    linha2 = [normalizar_turno(c) if c else c for c in linha2]

    # Monta lista de blocos na ordem em que aparecem
    posicoes_M = [i for i, v in enumerate(linha2) if v == "M"]
    blocos = []
    for pos_m in posicoes_M:
        disciplina = ""
        for col in range(pos_m, 0, -1):
            val = linha0[col]
            if val and limpar_texto(val) != municipio:
                disciplina = limpar_texto(val)
                break

        nivel_raw = linha1[pos_m] if pos_m < len(linha1) else ""
        nivel = limpar_texto(nivel_raw).upper() if nivel_raw else ""

        blocos.append({
            "disciplina": disciplina,
            "nivel":      nivel,
            "col_M":      pos_m,
            "col_T":      pos_m + 1,
            "col_N":      pos_m + 2,
        })

    # Detecta se é tabela de 1 disciplina com Fund+Médio ou 2 disciplinas distintas
    # Se todos os blocos têm o mesmo nome de disciplina → é 1 disciplina com Fund+Médio
    # Se os blocos têm nomes diferentes → são disciplinas separadas
    nomes_distintos = list(dict.fromkeys(b["disciplina"] for b in blocos))

    # Agrupa: para disciplinas distintas, cada uma vira um registro separado
    # Para mesma disciplina (Fund+Médio), os dois blocos são combinados num único registro
    grupos = {}  # nome_disciplina -> [bloco_fund, bloco_medio]
    for bloco in blocos:
        disc = bloco["disciplina"]
        if disc not in grupos:
            grupos[disc] = []
        grupos[disc].append(bloco)

    # Processa cada linha de escola (começa após a linha dos turnos)
    for row in table[idx_turnos + 1:]:
        if not row or not row[0]:
            continue

        escola = limpar_texto(row[0])
        if not escola or escola.upper() == "ESTABELECIMENTO":
            continue

        nota_linha = extrair_nota_linha(row)

        def get_val(col):
            val = row[col] if col < len(row) else None
            return limpar_texto(val) if val else ""

        for disc, blocos_disc in grupos.items():
            fund = {"M": "", "T": "", "N": ""}
            medio = {"M": "", "T": "", "N": ""}
            observacoes = set()

            if nota_linha:
                observacoes.add(nota_linha)

            for idx, bloco in enumerate(blocos_disc):
                nivel = bloco["nivel"]

                aulas_raw = {
                    "M": get_val(bloco["col_M"]),
                    "T": get_val(bloco["col_T"]),
                    "N": get_val(bloco["col_N"]),
                }

                aulas = {}
                for turno, val in aulas_raw.items():
                    numero, nota_val = limpar_aulas(val)
                    aulas[turno] = numero
                    if nota_val and nota_val != "*":
                        observacoes.add(nota_val)

                # Determina se esse bloco é Fundamental ou Médio
                if "MÉDIO" in nivel or "MEDIO" in nivel:
                    medio = aulas
                elif "FUNDAMENTAL" in nivel:
                    fund = aulas
                else:
                    # Sem indicação explícita: primeiro bloco = Fund, segundo = Médio
                    if idx == 0:
                        fund = aulas
                    else:
                        medio = aulas

            registros.append({
                "disciplina":         disc,
                "municipio":          municipio,
                "escola":             escola,
                "ensino_fundamental": fund,
                "ensino_medio":       medio,
                "observacao":         ", ".join(sorted(observacoes)),
            })

    return registros


def extrair_data(pdf_path):
    """Extrai a data do cabeçalho do PDF."""
    with pdfplumber.open(pdf_path) as pdf:
        texto = pdf.pages[0].extract_text()
        match = re.search(r"DATA\s+(\d{2}/\d{2}/\d{4})", texto)
        return match.group(1) if match else "Data não encontrada"


def extrair_horario(pdf_path):
    """Extrai o horário da distribuição do PDF."""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    for cell in row:
                        match = re.search(r'(\d{1,2}h\d{0,2}(?:min)?)', str(cell or ''), re.IGNORECASE)
                        if match:
                            return match.group(1)
    return "Horário não encontrado"


def eh_cabecalho_sem_dados(table):
    """
    Verifica se a tabela é só um cabeçalho sem linhas de escola.
    Ex: tabela com município + disciplina + M/T/N mas sem nenhuma linha de dados.
    """
    if not eh_tabela_de_aulas(table):
        return False
    idx = linha_dos_turnos(table)
    linhas_dados = [r for r in table[idx+1:] if r and r[0] and limpar_texto(r[0])]
    return len(linhas_dados) == 0


def eh_dados_orfaos(table):
    """
    Verifica se a tabela é só dados sem cabeçalho (continuação de tabela quebrada).
    Critério: primeira célula não é município nem ESTABELECIMENTO,
    e não tem linha de M/T/N.
    """
    if not table or len(table) == 0:
        return False
    if eh_tabela_de_aulas(table):
        return False
    primeira = limpar_texto(table[0][0] or "").upper()
    # Se começa com nome de escola (não é cabeçalho)
    municipios = ("BORBA", "ORTIGUEIRA", "RESERVA", "VENTANIA", "TIBAGI")
    nao_e_cabecalho = (
        primeira not in ("", "ESTABELECIMENTO") and
        not any(m in primeira for m in municipios)
    )
    return nao_e_cabecalho


def juntar_tabela(cabecalho, dados):
    """Junta um cabeçalho com linhas de dados órfãos."""
    idx = linha_dos_turnos(cabecalho)
    return cabecalho[:idx+1] + dados


def processar_pdf(pdf_path):
    """Processa um PDF completo e retorna os dados estruturados."""
    data = extrair_data(pdf_path)
    horario = extrair_horario(pdf_path)
    registros = []

    # Coleta todas as tabelas do PDF em sequência
    todas_tabelas = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            todas_tabelas.extend(page.extract_tables())

    # Processa tabelas tentando juntar cabeçalhos com dados órfãos
    ultimo_cabecalho = None
    for table in todas_tabelas:
        if eh_cabecalho_sem_dados(table):
            # Guarda o cabeçalho para juntar com a próxima tabela de dados
            ultimo_cabecalho = table
            continue

        if eh_dados_orfaos(table) and ultimo_cabecalho is not None:
            # Junta o cabeçalho guardado com esses dados
            table = juntar_tabela(ultimo_cabecalho, table)
            ultimo_cabecalho = None

        if eh_tabela_de_aulas(table):
            ultimo_cabecalho = None
            registros.extend(extrair_aulas_da_tabela(table))
        elif ultimo_cabecalho is None:
            # Tabela sem cabeçalho pendente — tenta processar mesmo assim
            # (caso de Recomposição LP sem linha M/T/N)
            pass

    return {
        "data":            data,
        "horario":         horario,
        "arquivo":         pdf_path,
        "total_registros": len(registros),
        "distribuicao":    registros,
    }


# Teste
if __name__ == "__main__":
    pdf_path = "/mnt/user-data/uploads/cronograma_distribuicao_de_aulas_telboba_26_02_26_pdfTB_26_02.pdf"
    resultado = processar_pdf(pdf_path)

    print(f"Data     : {resultado['data']}")
    print(f"Registros: {resultado['total_registros']}")
    print("\n" + "="*60)

    for item in resultado["distribuicao"]:
        print(f"\nDisciplina : {item['disciplina']}")
        print(f"Escola     : {item['escola']}")
        print(f"Fund. M/T/N: {item['ensino_fundamental']['M']} / {item['ensino_fundamental']['T']} / {item['ensino_fundamental']['N']}")
        print(f"Médio M/T/N: {item['ensino_medio']['M']} / {item['ensino_medio']['T']} / {item['ensino_medio']['N']}")
        if item['observacao']:
            print(f"Observação : {item['observacao']}")