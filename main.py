import requests
from bs4 import BeautifulSoup
from downloader import baixar_pdf
import re

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

# Busca a lista de arquivos
url_arquivo = base_url + "/webservices/documentador/convocacoes-atribuicoes-aula/arquivo/"
r1 = session.post(url_arquivo, data=dados, headers=headers, cookies=cookies)

soup = BeautifulSoup(r1.json(), "html.parser")
links = soup.find_all("a", href=True)
print(f"Links encontrados: {len(links)}")

for link in links:
    href = link["href"]
    
    # Pega só o nome do arquivo .pdf (antes do texto extra)
    nome_raw = link.get_text(strip=True)
    nome_arquivo = re.sub(r'[\\/*?:"<>|]', "_", nome_raw) + ".pdf"
    
    print(f"Baixando: {nome_arquivo}")
    baixar_pdf(session, href, nome_arquivo)