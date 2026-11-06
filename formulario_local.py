"""Formulário demonstrativo local: sem envio para sites de terceiros."""
from __future__ import annotations

import argparse
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qs

CAMPOS = ("Nome", "Sobrenome", "email", "Celular", "Estado", "Rua", "numero", "additionals")
HTML = '''<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cadastro de Clientes • Automação Web</title><style>
:root{color-scheme:dark;font-family:system-ui,Arial;background:#0c1220;color:#f4f7fb}body{margin:0;padding:36px 16px}main{max-width:720px;margin:auto;background:#141e31;border:1px solid #304057;border-radius:20px;padding:28px;box-shadow:0 18px 50px #0005}h1{margin-top:0}.sub{color:#adbdd2}form{display:grid;grid-template-columns:1fr 1fr;gap:16px}label{display:flex;flex-direction:column;gap:7px;font-size:14px}input{padding:12px 13px;border:1px solid #53637b;border-radius:10px;background:#0b1527;color:white;font-size:16px}input:focus{outline:2px solid #79a9ff}button{grid-column:1/-1;border:0;border-radius:10px;padding:13px;font-size:16px;font-weight:700;background:#83b7ff;color:#061226;cursor:pointer}.wide{grid-column:1/-1}small{color:#afc1d7}@media(max-width:580px){form{grid-template-columns:1fr}main{padding:18px}}</style></head><body><main><h1>Cadastro de clientes</h1><p class="sub">Formulário de demonstração para testar automação com Selenium. Os dados ficam apenas neste computador.</p><form method="post" action="/salvar">
<label>Nome<input name="Nome" required maxlength="100"></label><label>Sobrenome<input name="Sobrenome" required maxlength="100"></label><label>E-mail<input name="email" type="email" required maxlength="255"></label><label>Celular<input name="Celular" required maxlength="30"></label><label>Estado (UF)<input name="Estado" required maxlength="2"></label><label>Rua<input name="Rua" required maxlength="150"></label><label>Número<input name="numero" required maxlength="30"></label><label>Complemento<input name="additionals" maxlength="150"></label><button type="submit">Cadastrar cliente</button></form><p><small>Projeto educacional. Utilize dados fictícios nos testes.</small></p></main></body></html>'''


def criar_tabela(caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(caminho) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, sobrenome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE, celular TEXT NOT NULL, estado TEXT NOT NULL,
            rua TEXT NOT NULL, numero TEXT NOT NULL, complemento TEXT NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")


def validar(d: dict[str, str]) -> dict[str, str]:
    values = {k: str(d.get(k, "")).strip() for k in CAMPOS}
    if any(not values[k] for k in CAMPOS if k != "additionals"):
        raise ValueError("Preencha todos os campos obrigatórios.")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", values["email"]):
        raise ValueError("E-mail inválido.")
    if not re.fullmatch(r"[A-Za-z]{2}", values["Estado"]):
        raise ValueError("Estado deve conter duas letras.")
    if any(len(values[k]) > n for k, n in {"Nome":100,"Sobrenome":100,"email":255,"Celular":30,"Estado":2,"Rua":150,"numero":30,"additionals":150}.items()):
        raise ValueError("Texto excede o tamanho permitido.")
    values["Estado"] = values["Estado"].upper()
    values["email"] = values["email"].lower()
    return values


def salvar(caminho: Path, valores: dict[str, str]) -> int:
    d = validar(valores)
    with sqlite3.connect(caminho) as con:
        cur = con.execute("""INSERT INTO clientes(nome,sobrenome,email,celular,estado,rua,numero,complemento)
            VALUES(?,?,?,?,?,?,?,?)""", tuple(d[k] for k in CAMPOS))
        return int(cur.lastrowid)


def make_handler(db: Path):
    class Handler(BaseHTTPRequestHandler):
        def responder(self, status: int, html: str):
            payload = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == "/":
                self.responder(200, HTML)
            elif self.path.startswith("/ok"):
                self.responder(200, "<html lang='pt-br'><meta charset='utf-8'><h1>Cadastro salvo com sucesso!</h1><a href='/'>Novo cadastro</a></html>")
            else:
                self.responder(404, "<h1>Página não encontrada</h1>")

        def do_POST(self):
            if self.path != "/salvar":
                self.responder(404, "<h1>Página não encontrada</h1>")
                return
            try:
                tamanho = int(self.headers.get("Content-Length", "0"))
                if not 0 < tamanho <= 8192:
                    raise ValueError("Tamanho do formulário inválido.")
                body = self.rfile.read(tamanho).decode("utf-8")
                valores = {k: v[0] for k,v in parse_qs(body, keep_blank_values=True).items()}
                salvar(db, valores)
            except (ValueError, UnicodeError, sqlite3.IntegrityError) as exc:
                msg = "E-mail já cadastrado." if isinstance(exc, sqlite3.IntegrityError) else str(exc)
                self.responder(400, "<html lang='pt-br'><meta charset='utf-8'><h1>Erro no cadastro</h1><p>"+escape(msg)+"</p><a href='/'>Voltar</a></html>")
                return
            self.send_response(303)
            self.send_header("Location", "/ok")
            self.send_header("Content-Length", "0")
            self.end_headers()
    return Handler


def main():
    parser = argparse.ArgumentParser(description="Inicia formulário demonstrativo em localhost")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", type=Path, default=Path("dados/clientes.db"))
    args = parser.parse_args()
    criar_tabela(args.db)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.db))
    print(f"Abra http://127.0.0.1:{server.server_port} no navegador. Ctrl+C encerra.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
