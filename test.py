from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

options = Options()
options.headless = False  # depois podemos colocar True

driver = webdriver.Firefox(
    service=Service(GeckoDriverManager().install()),
    options=options
)

url = "https://nretelemacoborba.educacao.pr.gov.br/webservices/documentador/convocacoes-atribuicoes-aula"

driver.get(url)

# Espera algum elemento da página carregar (importante!)
WebDriverWait(driver, 15).until(
    EC.presence_of_element_located((By.TAG_NAME, "body"))
)

print("Página carregada!")

html = driver.page_source

with open("pagina_renderizada.html", "w", encoding="utf-8") as f:
    f.write(html)

print("HTML salvo!")

input("Pressione Enter para fechar...")
driver.quit()