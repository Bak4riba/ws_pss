import requests
import json
import os
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from downloader import baixar_pdf
from extractor import processar_pdf

# ─── Configuração ───────────────────────────────────────────────────────────

session = requests.Session()

base_url = "https://nretelemacoborba.educacao.pr.gov.br"
page_url = base_url + "/webservices/documentador/convocacoes-atribuicoes-aula"

cookies = {
    "_ga": "GA1.1.1692140853.1768793094",
    "_clck": "ploue6%5E2%5Eg38%5E0%5E2210",
    "_ga_VF9WRB3SP9": "GS2.1.s1770064258$o15$g1$t1770064275$j43$l0$h0"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": page_url,
    "Origin": base_url
}

dados = {
    "rota": "convocacoes-atribuicoes-aula",
    "pasta": "Telêmaco Borba/Professor/Convocação e Distribuição/2026"
}

DIAS_FILTRO = 2

# ─── Helpers ────────────────────────────────────────────────────────────────

def extrair_data_do_nome(nome):
    """
    Tenta extrair a data do nome/título do link.
    Prioriza formatos mais completos (com ano) e pega a data mais recente encontrada.
    """
    datas = []

    # dd/mm/yyyy
    for m in re.finditer(r'(\d{2})/(\d{2})/(\d{4})', nome):
        try:
            datas.append(datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))))
        except: pass

    # dd_mm_yyyy
    for m in re.finditer(r'(\d{2})_(\d{2})_(\d{4})', nome):
        try:
            datas.append(datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))))
        except: pass

    # dd/mm sem ano — assume ano atual
    for m in re.finditer(r'(\d{2})/(\d{2})(?!\d)', nome):
        try:
            datas.append(datetime(datetime.today().year, int(m.group(2)), int(m.group(1))))
        except: pass

    return max(datas) if datas else None

# ─── Etapa 1: Scraping — busca lista de PDFs ────────────────────────────────

print("Buscando lista de PDFs...")
url_arquivo = base_url + "/webservices/documentador/convocacoes-atribuicoes-aula/arquivo/"
r1 = session.post(url_arquivo, data=dados, headers=headers, cookies=cookies)

soup = BeautifulSoup(r1.json(), "html.parser")
links = soup.find_all("a", href=True)
print(f"PDFs encontrados no site: {len(links)}")

# ─── Etapa 2: Download — só baixa PDFs dos últimos X dias ───────────────────

pasta_pdfs = "pdfs"
os.makedirs(pasta_pdfs, exist_ok=True)

data_limite = datetime.today() - timedelta(days=DIAS_FILTRO)
print(f"\nFiltrando PDFs dos últimos {DIAS_FILTRO} dias (a partir de {data_limite.strftime('%d/%m/%Y')})...")

for link in links:
    href = link["href"]
    nome_raw = link.get_text(strip=True)
    nome_arquivo = re.sub(r'[\\/*?:"<>|]', "_", nome_raw) + ".pdf"
    caminho = os.path.join(pasta_pdfs, nome_arquivo)

    # Filtra pela data antes de baixar
    data_link = extrair_data_do_nome(nome_raw)
    if data_link is None:
        print(f"  Data não identificada, pulando: {nome_arquivo}")
        continue

    if data_link < data_limite:
        print(f"  Ignorando (muito antigo - {data_link.strftime('%d/%m/%Y')}): {nome_arquivo}")
        continue

    if os.path.exists(caminho):
        print(f"  Já existe ({data_link.strftime('%d/%m/%Y')}): {nome_arquivo}")
    else:
        print(f"  Baixando ({data_link.strftime('%d/%m/%Y')}): {nome_arquivo}")
        baixar_pdf(session, href, nome_arquivo)

# ─── Etapa 3: Extração — processa PDFs baixados e gera JSON ─────────────────

print("\nExtraindo dados dos PDFs...")
todos_registros = []

for nome_arquivo in sorted(os.listdir(pasta_pdfs)):
    if not nome_arquivo.endswith(".pdf"):
        continue

    caminho = os.path.join(pasta_pdfs, nome_arquivo)
    try:
        resultado = processar_pdf(caminho)
        print(f"  {nome_arquivo} → {resultado['total_registros']} registros (data: {resultado['data']})")
        todos_registros.append(resultado)
    except Exception as e:
        print(f"  ERRO em {nome_arquivo}: {e}")

# ─── Etapa 4: Deduplicação — mantém só o registro mais recente por escola+disciplina ──

print("\nDeduplicando registros...")

def parse_data(s):
    try:
        return datetime.strptime(s, "%d/%m/%Y")
    except:
        return datetime.min

# Achata todos os registros com a data do PDF pai
todos_flat = []
for pdf in todos_registros:
    for reg in pdf["distribuicao"]:
        todos_flat.append({ **reg, "data_pdf": pdf["data"], "horario": pdf.get("horario", "") })

# Para cada chave escola+disciplina, mantém só o mais recente
mais_recentes = {}
for reg in todos_flat:
    chave = (reg["escola"].strip().upper(), reg["disciplina"].strip().upper())
    data_reg = parse_data(reg["data_pdf"])
    if chave not in mais_recentes or data_reg > parse_data(mais_recentes[chave]["data_pdf"]):
        mais_recentes[chave] = reg

registros_finais = list(mais_recentes.values())
print(f"  Antes: {len(todos_flat)} registros → Após deduplicação: {len(registros_finais)} registros")

# ─── Etapa 5: Salva o JSON final ─────────────────────────────────────────────

output = {
    "total_pdfs":        len(todos_registros),
    "total_registros":   len(registros_finais),
    "pdfs":              todos_registros,
    "distribuicao":      registros_finais,
}

with open("dados.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\nJSON salvo em dados.json")
print(f"Total de PDFs processados   : {output['total_pdfs']}")
print(f"Total de registros únicos   : {output['total_registros']}")