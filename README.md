# 01 — Automação Web com Python e Selenium

Projeto completo inspirado nas aulas de **Automação Web**: formulário responsivo de teste, importação CSV compatível com Excel, validação, automação de cadastro e relatório dos resultados. Os cadastros ficam num banco SQLite local; nenhum dado é enviado a terceiros.

## Como executar (Windows)

1. Instale Python 3.10+ e Google Chrome.
2. Abra o terminal nesta pasta e execute:

```powershell
python -m pip install -r requirements.txt
python formulario_local.py
```

3. Acesse `http://127.0.0.1:8765/` para ver o formulário.
4. **Em um segundo terminal**, ainda nesta pasta:

```powershell
python automacao.py --dry-run
python automacao.py
```

O navegador abre, preenche três clientes fictícios de `dados/clientes_exemplo.csv` e gera `dados/resultado.csv`. Ao repetir o cadastro com os mesmos e-mails, a aplicação recusará duplicatas (comportamento esperado).

### Importação CSV e validação

O arquivo pode usar **vírgula (`,`) ou ponto e vírgula (`;`)** como separador (compatível com exportações do Excel). A primeira linha precisa conter as colunas: `Nome`, `Sobrenome`, `email`, `Celular`, `Estado`, `Rua`, `numero` e `additionals`.

O programa valida os registros antes de abrir o navegador e informa o número da linha caso encontre **e-mails duplicados**, colunas repetidas, registros incompletos ou valores extras. Quando há erros, nenhum cadastro é enviado.

Para automação sem mostrar o Chrome: `python automacao.py --headless`. Selenium usa o Selenium Manager para resolver o driver compatível quando possível.

## Testes

```powershell
python -m unittest discover -s tests -v
```

## Arquivos

- `formulario_local.py`: site e banco de dados de demonstração;
- `automacao.py`: leitura, validação e automação com Selenium;
- `dados/clientes_exemplo.csv`: dados **fictícios**;
- `dados/resultado.csv`: relatório gerado após o envio;
- `dados/clientes.db`: banco gerado localmente.

## Limites

Este projeto preenche **apenas o site local**. Não usa o Google Forms das aulas nem autoriza cadastro em sites externos. Não foi necessário salvar credenciais ou tokens.
