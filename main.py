import requests
from bs4 import BeautifulSoup
from downloader import baixar_pdf

session = requests.Session()

url = "https://nretelemacoborba.educacao.pr.gov.br/webservices/documentador/convocacoes-atribuicoes-aula/pasta/"

dados = {
    "rota": "convocacoes-atribuicoes-aula",
    "pasta": "Telêmaco Borba/Professor/Convocação e Distribuição/2026"
}

headers = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://nretelemacoborba.educacao.pr.gov.br/webservices/documentador/convocacoes-atribuicoes-aula"
}

resposta = session.post(url, data=dados, headers=headers)

print("Status:", resposta.status_code)
print(resposta.text[:500])  # DEBUG

soup = BeautifulSoup(resposta.text, "html.parser")
print(len(soup.find_all("a")))
for link in soup.find_all("a", href=True):
    href = link["href"]
    nome = link.get_text(strip=True)

    if "documentador.pr.gov.br" in href:
        print("Encontrado:", nome)
        baixar_pdf(href, nome.replace("/", "_"))