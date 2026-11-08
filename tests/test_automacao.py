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

    def test_csv_com_ponto_e_virgula(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "clientes.csv"
            csv_path.write_text(
                "Nome;Sobrenome;email;Celular;Estado;Rua;numero;additionals\n"
                "Joana;Lima;JOANA@EXAMPLE.COM;123;sp;Rua Um;15;\n",
                encoding="utf-8",
            )
            clientes, erros = ler_clientes(csv_path)
            self.assertEqual(erros, [])
            self.assertEqual(clientes[0]["email"], "joana@example.com")
            self.assertEqual(clientes[0]["Estado"], "SP")
            self.assertEqual(clientes[0]["additionals"], "")

    def test_csv_rejeita_email_repetido(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "duplicados.csv"
            csv_path.write_text(
                "Nome,Sobrenome,email,Celular,Estado,Rua,numero,additionals\n"
                "Joana,Lima,joana@example.com,123,SP,Rua Um,15,\n"
                "Maria,Lima,JOANA@example.com,321,RJ,Rua Dois,16,\n",
                encoding="utf-8",
            )
            clientes, erros = ler_clientes(csv_path)
            self.assertEqual(len(clientes), 1)
            self.assertEqual(len(erros), 1)
            self.assertIn("duplicado", erros[0])
            self.assertIn("Linha 3", erros[0])

    def test_csv_rejeita_colunas_extras_e_linhas_incompletas(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "inconsistente.csv"
            csv_path.write_text(
                "Nome,Sobrenome,email,Celular,Estado,Rua,numero,additionals\n"
                "Joana,Lima,joana@example.com,123,SP,Rua Um,15,,EXTRA\n"
                "Maria,Lima,maria@example.com,321,RJ,Rua Dois\n",
                encoding="utf-8",
            )
            clientes, erros = ler_clientes(csv_path)
            self.assertEqual(clientes, [])
            self.assertEqual(len(erros), 2)
            self.assertIn("Linha 2", erros[0])
            self.assertIn("Linha 3", erros[1])

    def test_csv_rejeita_cabecalho_duplicado(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "cabecalho.csv"
            csv_path.write_text(
                "Nome,Nome,Sobrenome,email,Celular,Estado,Rua,numero,additionals\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicados"):
                ler_clientes(csv_path)

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
