"""Automatiza o formulário local com Selenium usando registros de CSV."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from urllib.parse import urlsplit
from formulario_local import CAMPOS, validar


def ler_clientes(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    validos, erros = [], []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or any(field not in reader.fieldnames for field in CAMPOS):
            raise ValueError("CSV precisa das colunas: " + ", ".join(CAMPOS))
        for n, row in enumerate(reader, start=2):
            try:
                validos.append(validar(row))
            except (ValueError, TypeError) as e:
                erros.append(f"Linha {n}: {e}")
    return validos, erros


def executar(clientes: list[dict[str, str]], url: str, headless: bool) -> list[tuple[str, str]]:
    host = urlsplit(url)
    if host.scheme != "http" or host.hostname not in ("localhost", "127.0.0.1") or host.path not in ("", "/"):
        raise ValueError("Por segurança, esta automação de exemplo só aceita o formulário local HTTP.")
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError as exc:
        raise RuntimeError("Instale Selenium: python -m pip install -r requirements.txt") from exc
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1200,900")
    driver = webdriver.Chrome(options=options)
    resultados = []
    try:
        for cliente in clientes:
            try:
                driver.get(url)
                wait = WebDriverWait(driver, 15)
                for campo in CAMPOS:
                    elemento = wait.until(EC.presence_of_element_located((By.NAME, campo)))
                    elemento.send_keys(cliente[campo])
                driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                wait.until(EC.url_contains("/ok"))
                resultados.append((cliente["email"], "enviado"))
            except Exception as error:
                resultados.append((cliente["email"], f"falhou: {type(error).__name__}"))
    finally:
        driver.quit()
    return resultados


def main():
    p = argparse.ArgumentParser(description="Preenche formulário de demonstração automaticamente")
    p.add_argument("--csv", type=Path, default=Path("dados/clientes_exemplo.csv"))
    p.add_argument("--url", default="http://127.0.0.1:8765/")
    p.add_argument("--dry-run", action="store_true", help="Valida arquivo sem abrir navegador")
    p.add_argument("--headless", action="store_true", help="Oculta navegador durante execução")
    p.add_argument("--relatorio", type=Path, default=Path("dados/resultado.csv"))
    a = p.parse_args()
    try:
        clientes, erros = ler_clientes(a.csv)
        print(f"Registros válidos: {len(clientes)} | Com erro: {len(erros)}")
        for e in erros:
            print(e)
        if a.dry_run:
            return
        if erros:
            raise ValueError("Corrija as linhas inválidas antes de enviar qualquer cadastro.")
        resultados = executar(clientes, a.url, a.headless)
        a.relatorio.parent.mkdir(parents=True, exist_ok=True)
        with a.relatorio.open("w", encoding="utf-8-sig", newline="") as file:
            w = csv.writer(file)
            w.writerow(("email", "situacao"))
            w.writerows(resultados)
        print(f"Relatório: {a.relatorio}")
    except (OSError, ValueError, RuntimeError) as e:
        p.exit(1, f"Erro: {e}\n")


if __name__ == "__main__":
    main()
