import requests # :Ignore
import os

def baixar_pdf(url, nome_arquivo):
    os.makedirs("pdfs", exist_ok=True)

    resposta = requests.get(url)

    if resposta.status_code == 200:
        caminho = os.path.join("pdfs", nome_arquivo)
        with open(caminho, "wb") as f:
            f.write(resposta.content)
        print(f"Baixado: {nome_arquivo}")
    else:
        print("Erro ao baixar:", resposta.status_code)