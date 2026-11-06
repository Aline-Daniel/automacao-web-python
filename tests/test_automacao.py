import sqlite3
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer
from threading import Thread
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automacao import ler_clientes
from formulario_local import criar_tabela, make_handler, salvar, validar


class TestAutomacao(unittest.TestCase):
    def test_csv_origem(self):
        rows, errors = ler_clientes(Path(__file__).resolve().parents[1] / 'dados/clientes_exemplo.csv')
        self.assertEqual(len(rows), 3)
        self.assertEqual(errors, [])

    def test_validador(self):
        d = dict(Nome='Teste',Sobrenome='Exemplo',email='teste@example.com',Celular='123',Estado='sp',Rua='A',numero='1',additionals='')
        self.assertEqual(validar(d)['Estado'], 'SP')
        d['email'] = 'invalido'
        with self.assertRaises(ValueError): validar(d)

    def test_persistencia_e_email_unico(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'clientes.db'; criar_tabela(db)
            d = dict(Nome='Teste',Sobrenome='Exemplo',email='teste@example.com',Celular='123',Estado='SP',Rua='A',numero='1',additionals='')
            salvar(db, d)
            with self.assertRaises(sqlite3.IntegrityError): salvar(db, d)

    def test_post_formulario_http_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'clientes.db'; criar_tabela(db)
            srv = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(db))
            t = Thread(target=srv.serve_forever, daemon=True); t.start()
            try:
                d = dict(Nome='Teste',Sobrenome='Exemplo',email='web@example.com',Celular='123',Estado='SP',Rua='A',numero='1',additionals='')
                req=Request(f'http://127.0.0.1:{srv.server_port}/salvar', data=urlencode(d).encode('utf-8'), method='POST')
                with urlopen(req, timeout=5) as response:
                    self.assertIn(b'Cadastro salvo', response.read())
                with sqlite3.connect(db) as con:
                    self.assertEqual(con.execute('select count(*) from clientes').fetchone()[0], 1)
            finally:
                srv.shutdown(); srv.server_close(); t.join(timeout=4)


if __name__ == '__main__': unittest.main()
