import os

def baixar_pdf(session, url, nome_arquivo):
    os.makedirs("pdfs", exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0"}
    resposta = session.get(url, headers=headers, allow_redirects=True)
    if resposta.status_code == 200 and "pdf" in resposta.headers.get("Content-Type", ""):
        caminho = os.path.join("pdfs", nome_arquivo)
        with open(caminho, "wb") as f:
            f.write(resposta.content)
        print(f"Baixado: {nome_arquivo}")
    else:
        print(f"Erro ao baixar {nome_arquivo}: {resposta.status_code}")