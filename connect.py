import requests

base_url = "https://nretelemacoborba.educacao.pr.gov.br"
page_url = base_url + "/webservices/documentador/convocacoes-atribuicoes-aula"
post_url = base_url + "/webservices/documentador/convocacoes-atribuicoes-aula/arquivo/"

session = requests.Session()
session.get(page_url)

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": page_url,
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": base_url
}

payload = {
    "rota": "convocacoes-atribuicoes-aula",
    "pasta": "Telêmaco Borba/Professor/Convocação e Distribuição/2026"
}

response = session.post(post_url, data=payload, headers=headers)

print("Status:", response.status_code)
print(response.text)